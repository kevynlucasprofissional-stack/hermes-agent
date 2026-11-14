"""Isolated localhost HTTP/SQLite site for native-browser Kanban E2E qualification.

Not a Hermes tool or external integration. The browser may navigate and submit
the HTML form; a separate SQLite connection or GET /api/item verifies persistence.
No external network access and no application data is touched.
"""
from __future__ import annotations

from contextlib import closing
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=3)
    con.execute("""CREATE TABLE IF NOT EXISTS qa_item (
        id INTEGER PRIMARY KEY CHECK(id=1), title TEXT NOT NULL,
        revision INTEGER NOT NULL DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS qa_applied_operations (
        operation_id TEXT PRIMARY KEY, title TEXT NOT NULL)""")
    con.execute("INSERT OR IGNORE INTO qa_item(id,title,revision) VALUES(1,'Inicial',0)")
    con.commit()
    return con


def make_server(database_path: Path, *, submit_navigates: bool = False) -> ThreadingHTTPServer:
    """Bind only to loopback; optional normal form POST -> HTTP 303 for lost-ACK QA."""
    db = Path(database_path).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(db)):
        pass

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path not in {"/", "/api/item", "/api/item/operation"}:
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            with closing(_connect(db)) as con:
                item = con.execute(
                    "SELECT title,revision FROM qa_item WHERE id=1"
                ).fetchone()
                applied = (con.execute(
                    "SELECT operation_id FROM qa_applied_operations ORDER BY rowid DESC LIMIT 1"
                ).fetchone() if path == "/api/item/operation" else None)
            title, revision = item
            if path in {"/api/item", "/api/item/operation"}:
                body = {"id": "qa-1", "title": title, "revision": revision}
                if path == "/api/item/operation":
                    body["last_operation_id"] = applied[0] if applied else None
                self._send(200, json.dumps(body).encode("utf-8"), "application/json")
                return
            op = uuid4().hex
            page = f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>Browser Kanban QA</title><h1>Browser Kanban QA</h1>
<p id="persisted-title" data-testid="persisted-title">{escape(title)}</p>
<p id="persisted-revision">Revision: {revision}</p>
<form method="post" action="/save">
  <label for="title">Titulo</label>
  <input id="title" name="title" type="text" value="{escape(title, quote=True)}">
  <input name="expected_revision" type="hidden" value="{revision}">
  <input name="operation_id" type="hidden" value="{op}">
  <button id="save" type="submit">Salvar</button>
</form>
<script>
// Real POST/GET, with no document replacement before native click delivery
// can be acknowledged. No fake receipt or local-only successful save.
document.querySelector('form').addEventListener('submit', async function(event) {{
  event.preventDefault();
  const form = event.currentTarget;
  const button = document.querySelector('#save');
  button.disabled = true;
  try {{
    const response = await fetch('/save', {{
      method: 'POST', body: new URLSearchParams(new FormData(form)),
      cache: 'no-store', credentials: 'same-origin'
    }});
    if (!response.ok) {{ throw new Error('save_http_failed'); }}
    const remote = await fetch('/api/item', {{ cache: 'no-store' }});
    if (!remote.ok) {{ throw new Error('read_http_failed'); }}
    const saved = await remote.json();
    document.querySelector('#persisted-title').textContent = saved.title;
    document.querySelector('#persisted-revision').textContent = 'Revision: ' + saved.revision;
  }} catch (_) {{
    document.querySelector('#persisted-revision').textContent = 'Save failed or uncertain';
  }} finally {{
    button.disabled = false;
  }}
}});
</script></html>""".encode("utf-8")
            if submit_navigates:
                # Ordinary HTML submit replaces the document after HTTP 303.
                # No JS interception: native click delivery may lose its ACK.
                page = page.split(b"<script>", 1)[0] + b"</html>"
            self._send(200, page, "text/html; charset=utf-8")

        def do_POST(self):
            if urlsplit(self.path).path != "/save":
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    raise ValueError("size")
                form = parse_qs(self.rfile.read(size).decode("utf-8"),
                                strict_parsing=True)
                def one(key):
                    values = form[key]
                    if len(values) != 1:
                        raise ValueError(key)
                    return values[0]
                title = one("title").strip()
                op = one("operation_id")
                rev = int(one("expected_revision"))
                if not (1 <= len(title) <= 160 and rev >= 0
                        and re.fullmatch(r"[a-f0-9]{32}", op)):
                    raise ValueError("fields")
            except (ValueError, KeyError, UnicodeError):
                self._send(400, b"invalid form", "text/plain; charset=utf-8")
                return
            with closing(_connect(db)) as con:
                con.execute("BEGIN IMMEDIATE")
                previous = con.execute(
                    "SELECT title FROM qa_applied_operations WHERE operation_id=?",
                    (op,),
                ).fetchone()
                if previous is not None:
                    if previous[0] != title:
                        self._send(409, b"operation conflict", "text/plain; charset=utf-8")
                        return
                else:
                    current = con.execute("SELECT revision FROM qa_item WHERE id=1").fetchone()[0]
                    if current != rev:
                        self._send(409, b"revision conflict", "text/plain; charset=utf-8")
                        return
                    con.execute("UPDATE qa_item SET title=?,revision=revision+1 WHERE id=1",
                                (title,))
                    con.execute(
                        "INSERT INTO qa_applied_operations(operation_id,title) VALUES(?,?)",
                        (op, title),
                    )
                    con.commit()
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
