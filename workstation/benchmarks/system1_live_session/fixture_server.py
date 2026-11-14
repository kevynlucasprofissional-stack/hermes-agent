"""Read-only local fixture for testing Hermes browser element location."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlsplit

PAGES = {
    "/unique": ('Alvo único',
        '<button type="button" id="reports">Relatórios</button>'
        '<button type="button" id="settings">Configurações</button>'
        '<div role="tab" tabindex="0" aria-label="Painel">Painel</div>'
        '<a href="/unique" aria-label="Ajuda">Ajuda</a>'),
    "/partial": ('Correspondência parcial',
        '<button type="button" id="open-reports">Abrir relatórios</button>'
        '<button type="button" id="settings">Configurações</button>'
        '<a href="/partial">Ajuda</a>'),
    "/duplicate": ('Alvo duplicado',
        '<button type="button" id="report-a">Relatórios</button>'
        '<button type="button" id="report-b">Relatórios</button>'
        '<button type="button" id="settings">Configurações</button>'),
    "/missing": ('Alvo ausente',
        '<button type="button" id="clients">Clientes</button>'
        '<button type="button" id="settings">Configurações</button>'
        '<a href="/missing">Ajuda</a>'),
}

def page(title: str, controls: str) -> bytes:
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Hermes System 1 — {title}</title>
<style>
body {{font-family: system-ui, sans-serif; max-width:700px; margin:55px auto; padding:15px;}}
button, [role="tab"], a {{display:inline-block; padding:11px; margin:8px; border:1px solid #777;
border-radius:6px; background:#f8f8f8; color:#222; cursor:default;}}
small {{display:block;margin:16px 0; color:#555;}}
</style></head>
<body><h1>Hermes System 1 — {title}</h1>
<p>Página de teste local. Elementos sem ações nem eventos externos.</p>
<main>{controls}</main>
<small>Fixture somente leitura — 127.0.0.1 — nenhuma ação é persistida.</small>
</body></html>"""
    return html.encode("utf-8")

class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/health":
            return self.send_payload(200, b'{"ok":true,"fixture":"hermes-system1-read-only","version":1}\n', "application/json")
        if route in PAGES:
            title, controls = PAGES[route]
            return self.send_payload(200, page(title, controls), "text/html")
        return self.send_payload(404, b"Not found\n", "text/plain")

    def do_HEAD(self):
        route = urlsplit(self.path).path
        self.send_response(200 if route in PAGES or route == "/health" else 404)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def send_payload(self, status: int, payload: bytes, kind: str):
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Robots-Tag", "noindex")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        return  # no per-request identifiers on disk

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18791)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be 1024..65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), FixtureHandler)
    print(json.dumps({"ready": True, "url": f"http://127.0.0.1:{args.port}/unique"}), flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
