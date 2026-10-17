"""CW-047 opt-in static web-dist server for managed native Browser previews.

Does not install or compile third-party sources, expose privileged APIs,
or open a browser. Launch through the existing scoped ProcessRegistry and
command guards; never spawn this from a free-form untrusted prompt.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from workstation.creative_web_app_spec import APPS, prebuilt_site_root


class CreativeStaticHandler(SimpleHTTPRequestHandler):
    """Serve only an explicit dist, with loopback/host and readiness fencing."""
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".webmanifest": "application/manifest+json",
    }

    def __init__(self, *args, root: Path, engine: str, port: int,
                 nonce: str, **kwargs):
        self._root = root
        self._engine = engine
        self._port = port
        self._nonce = nonce
        super().__init__(*args, directory=str(root), **kwargs)

    def _safe_request(self) -> bool:
        host = (self.headers.get("Host") or "").lower()
        if host not in {f"127.0.0.1:{self._port}", f"localhost:{self._port}"}:
            self.send_error(403, "Unexpected Host")
            return False
        origin = self.headers.get("Origin")
        if origin and origin.lower().rstrip("/") not in {
            f"http://127.0.0.1:{self._port}",
            f"http://localhost:{self._port}",
        }:
            self.send_error(403, "Unexpected Origin")
            return False
        return True

    def _health(self):
        supplied = self.headers.get("X-Hermes-Creative-Nonce") or ""
        if not hmac.compare_digest(supplied, self._nonce):
            self.send_error(403, "Health proof required")
            return
        payload = json.dumps({"ready": True, "engine": self._engine}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def do_GET(self):
        if not self._safe_request():
            return
        if urlsplit(self.path).path == "/__hermes_health":
            self._health()
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._safe_request():
            return
        if urlsplit(self.path).path == "/__hermes_health":
            self._health()
            return
        super().do_HEAD()

    def send_head(self):
        # Prevent directory listing and following symlinks outside a dist.
        candidate = Path(self.translate_path(self.path)).resolve()
        if not candidate.is_relative_to(self._root):
            self.send_error(403, "Outside web dist")
            return None
        if candidate.is_dir():
            index = (candidate / "index.html").resolve()
            if not index.is_file():
                self.send_error(404, "No directory listing")
                return None
            if not index.is_relative_to(self._root):
                self.send_error(403, "Index outside web dist")
                return None
        return super().send_head()

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=sorted(APPS), required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    root = prebuilt_site_root(args.root)
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    nonce = os.environ.get("HERMES_CREATIVE_LAUNCH_NONCE", "")
    if len(nonce) < 32:
        parser.error("Missing managed launch nonce in child environment")
    handler = partial(CreativeStaticHandler, root=root, engine=args.engine,
                      port=args.port, nonce=nonce)
    # No 0.0.0.0: a local static renderer is not a network service.
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        server.serve_forever(poll_interval=0.25)


if __name__ == "__main__":
    main()
