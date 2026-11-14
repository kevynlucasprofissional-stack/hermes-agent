"""The QA fixture proves real HTTP/SQLite effects, not native-browser E2E."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
import sqlite3
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server


def _read(url: str) -> bytes:
    with urlopen(url, timeout=3) as response:
        return response.read()


def test_qa_fixture_save_duplicate_and_restart_persisted_state(tmp_path):
    path = tmp_path / "qa.sqlite"
    server = make_server(path)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(server.serve_forever)
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            page = _read(base + "/").decode("utf-8")
            op = re.search(r'name="operation_id" type="hidden" value="([a-f0-9]{32})"', page)
            assert op and 'id="persisted-title"' in page
            post = urlencode({
                "title": "Mudanca realmente salva", "expected_revision": "0",
                "operation_id": op[1],
            }).encode()
            assert b"Mudanca realmente salva" in _read(
                Request(base + "/save", data=post, method="POST"))
            with sqlite3.connect(path) as independent:
                assert independent.execute(
                    "SELECT title,revision FROM qa_item WHERE id=1"
                ).fetchone() == ("Mudanca realmente salva", 1)
            assert b'"revision": 1' in _read(base + "/api/item")
            # Duplicate operation ID does not issue a second mutation.
            _read(Request(base + "/save", data=post, method="POST"))
            with sqlite3.connect(path) as independent:
                assert independent.execute(
                    "SELECT COUNT(*) FROM qa_applied_operations"
                ).fetchone()[0] == 1
                assert independent.execute(
                    "SELECT revision FROM qa_item WHERE id=1"
                ).fetchone()[0] == 1
            # Another operation with the stale revision fails closed.
            stale = urlencode({"title": "Perderia dados", "expected_revision": "0",
                               "operation_id": "a" * 32}).encode()
            try:
                _read(Request(base + "/save", data=stale, method="POST"))
                assert False, "stale revision unexpectedly accepted"
            except HTTPError as e:
                assert e.code == 409
        finally:
            server.shutdown()
            running.result(timeout=3)
            server.server_close()
    # Reopening SQLite still returns the persisted value.
    with sqlite3.connect(path) as independent:
        assert independent.execute(
            "SELECT title,revision FROM qa_item WHERE id=1"
        ).fetchone() == ("Mudanca realmente salva", 1)
