"""CW-047 local static server smoke, no third-party engine required."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from workstation.creative_web_static_server import CreativeStaticHandler


class StaticWebServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "index.html").write_text("<title>Test</title>", encoding="utf-8")
        (self.root / "fixture.wasm").write_bytes(b"\x00asm")
        self.nonce = "T" * 48

        def handler(*args, **kwargs):
            return CreativeStaticHandler(
                *args, root=self.root, engine="photocraft",
                port=self.server.server_port, nonce=self.nonce, **kwargs
            )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.worker.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path, headers=None):
        return urlopen(Request(
            f"http://127.0.0.1:{self.server.server_port}{path}",
            headers=headers or {}
        ), timeout=3)

    def test_web_root_and_wasm_mime(self):
        with self.request("/") as resp:
            self.assertIn(b"Test", resp.read())
        with self.request("/fixture.wasm") as resp:
            self.assertEqual(resp.headers.get_content_type(), "application/wasm")
            self.assertEqual(resp.read(), b"\x00asm")

    def test_health_requires_per_instance_nonce(self):
        with self.assertRaises(HTTPError) as fail:
            self.request("/__hermes_health")
        self.assertEqual(fail.exception.code, 403)
        with self.request("/__hermes_health",
                          {"X-Hermes-Creative-Nonce": self.nonce}) as resp:
            self.assertEqual(json.loads(resp.read())["engine"], "photocraft")

    def test_refuse_cross_origin(self):
        with self.assertRaises(HTTPError) as fail:
            self.request("/", {"Origin": "https://evil.example"})
        self.assertEqual(fail.exception.code, 403)

    def test_disable_directory_listing(self):
        (self.root / "empty").mkdir()
        with self.assertRaises(HTTPError) as fail:
            self.request("/empty/")
        self.assertEqual(fail.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
