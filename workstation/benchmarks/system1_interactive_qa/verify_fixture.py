"""QA fixture HTTP probe with a server that shuts down before exit."""
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen

from workstation.benchmarks.system1_interactive_qa.fixture_server import Handler

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{server.server_port}"
try:
    with urlopen(base + "/health", timeout=3) as response:
        health = response.read().decode()
    with urlopen(base + "/interaction", timeout=3) as response:
        html = response.read().decode()
    for marker in (
        'id="name"', 'id="reports"', "QA-REPORTS-CLICKED-ONCE",
        "QA-NAME-ENTERED:", "btn.disabled = true",
        "addEventListener('input'",
    ):
        assert marker in html, marker
    assert "system1-interaction-qa" in health
    print("QA_FIXTURE_HTTP_PASS",
          {"bytes": len(html), "ephemeral_port": server.server_port,
           "single_click_guard": True, "name_input": True})
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
