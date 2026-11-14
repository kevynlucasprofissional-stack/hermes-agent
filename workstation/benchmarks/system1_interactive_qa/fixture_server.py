"""Ephemeral loopback-only UI QA fixture. No external calls, disk writes or cookies."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HTML = b"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>System 1 Interaction QA</title></head>
<body>
<h1>Hermes System 1 - QA interativa</h1>
<label for="name">Nome</label>
<input id="name" type="text" aria-label="Nome" autocomplete="off">
<button id="reports" type="button">Relatorios</button>
<p id="click-proof">QA-REPORTS-NOT-CLICKED</p>
<p id="fill-proof">QA-NAME-EMPTY</p>
<script>
'use strict';
const btn = document.getElementById('reports');
btn.addEventListener('click', () => {
  btn.disabled = true;
  document.getElementById('click-proof').textContent='QA-REPORTS-CLICKED-ONCE';
});
document.getElementById('name').addEventListener('input', event => {
  document.getElementById('fill-proof').textContent='QA-NAME-ENTERED:' + event.target.value;
});
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body, kind = b'{"ok":true,"fixture":"system1-interaction-qa"}', "application/json"
        elif self.path == "/interaction":
            body, kind = HTML, "text/html"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 18792), Handler)
    print("QA_READY http://127.0.0.1:18792/interaction", flush=True)
    server.serve_forever()
