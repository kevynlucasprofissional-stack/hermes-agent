"""Model-facing browser payload projection: economy without losing addressability.

The Workstation lane returned the interactive-element inventory twice per call —
once as ``snapshot`` text (``formatInventory``) and again as the ``elements`` array.
These tests lock the projection that drops the duplicate and, above all, prove it is
lossless and fails open.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tools import browser_workstation as bw

# Elementos como o runtime os produz (element.shape: ref,tag,role,label,value,disabled,testid,name)
_ELEMENTS = [
    {"ref": "@e1", "tag": "input", "role": "input", "label": "Message", "value": "", "disabled": False,
     "name": "prompt"},
    {"ref": "@e2", "tag": "button", "role": "button", "label": "Enviar", "value": "", "disabled": False,
     "testid": "send-button"},
    {"ref": "@e3", "tag": "a", "role": "link", "label": "Documentação", "value": "", "disabled": False},
    {"ref": "@e4", "tag": "button", "role": "button", "label": "Copiar", "value": "", "disabled": True},
    {"ref": "@e5", "tag": "textarea", "role": "textarea", "label": "", "value": "texto digitado",
     "disabled": False},
]

_LINE = re.compile(
    r'^- \[(?P<ref>@e\d+)\] (?P<role>\S+)'
    r'(?: "(?P<label>(?:[^"\\]|\\.)*)")?'
    r'(?: value="(?P<value>(?:[^"\\]|\\.)*)")?'
    r'(?P<disabled> disabled)?$'
)


def _render_line(element: dict) -> str:
    """Exactly what ``formatInventory`` prints for one element."""
    label = f' "{element["label"].replace(chr(34), chr(92) + chr(34))}"' if element.get("label") else ""
    value = f' value="{element["value"]}"' if element.get("value") else ""
    disabled = " disabled" if element.get("disabled") else ""
    return f'- [{element["ref"]}] {element.get("role") or element["tag"]}{label}{value}{disabled}'


def _snapshot(elements: list[dict], text: str = "conteudo da pagina") -> str:
    lines = "\n".join(_render_line(element) for element in elements)
    return (
        "URL: https://example.com\nTitle: Exemplo\n\n"
        f"Interactive elements:\n{lines}\n\nPage text:\n{text}"
    )


def _payload(elements: list[dict] | None = None, text: str = "conteudo da pagina") -> dict:
    elements = _ELEMENTS if elements is None else elements
    return {
        "success": True,
        "runtime": "electron-chromium",
        "task_id": "task-a",
        "url": "https://example.com",
        "title": "Exemplo",
        "snapshot": _snapshot(elements, text),
        "snapshot_delta": None,
        "revision": 7,
        "elements": elements,
        "truncated": False,
        "total_text_chars": len(text),
        "element_count": len(elements),
        "wall_detected": False,
        "readiness": "ready",
    }


def _reconstruct(projected: dict) -> list[dict]:
    """Rebuild every element from the projected model-facing payload alone."""
    section = projected["snapshot"].partition("Interactive elements:\n")[2].partition("\nPage text:")[0]
    index = projected.get("element_index", {})
    rebuilt = []
    for line in section.splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        ref = match.group("ref")
        extras = index.get(ref, {})
        label = (match.group("label") or "").replace('\\"', '"')
        value = match.group("value") or ""
        element = {
            "ref": ref,
            "tag": extras.get("tag", match.group("role")),
            "role": match.group("role"),
            "label": label,
            "value": value,
            "disabled": bool(match.group("disabled")),
        }
        for key in ("testid", "name"):
            if key in extras:
                element[key] = extras[key]
        rebuilt.append({key: value for key, value in element.items() if value != ""})
    return rebuilt


# ---------------------------------------------------------------- projeção


def test_duplicate_element_list_is_dropped_and_marked():
    projected = bw.project_model_browser_payload(_payload())
    assert "elements" not in projected
    assert projected["elements_projected"] is True
    assert projected["element_count"] == len(_ELEMENTS)


def test_projection_is_lossless_for_every_element_field():
    projected = bw.project_model_browser_payload(_payload())
    rebuilt = _reconstruct(projected)
    assert len(rebuilt) == len(_ELEMENTS)
    for original, recovered in zip(_ELEMENTS, rebuilt):
        for key, value in original.items():
            if value in ("", False):
                continue
            assert recovered.get(key) == value, f"{original['ref']} perdeu {key}"


def test_projection_keeps_only_fields_the_text_cannot_express():
    projected = bw.project_model_browser_payload(_payload())
    index = projected.get("element_index", {})
    # @e1: tag == role, só "name" é extra.  @e2: role button != tag button? igual + testid.
    assert index.get("@e1") == {"name": "prompt"}
    assert index.get("@e2") == {"testid": "send-button"}
    # @e4 e @e5 não têm nada que o texto já não diga.
    assert "@e4" not in index and "@e5" not in index


def test_projection_shrinks_a_realistic_payload():
    elements = [
        {"ref": f"@e{i}", "tag": "button", "role": "button", "label": f"Item {i}",
         "value": "", "disabled": False}
        for i in range(1, 61)
    ]
    payload = _payload(elements)
    projected = bw.project_model_browser_payload(payload)
    before = len(json.dumps(payload, ensure_ascii=False))
    after = len(json.dumps(projected, ensure_ascii=False))
    assert after < before * 0.65, f"economia insuficiente: {before} -> {after}"


# ---------------------------------------------------------------- fail open


def test_fails_open_when_snapshot_text_does_not_list_every_ref():
    payload = _payload()
    payload["snapshot"] = payload["snapshot"].replace(_render_line(_ELEMENTS[-1]), "")
    assert bw.project_model_browser_payload(payload) == payload


def test_fails_open_on_unknown_inventory_grammar():
    payload = _payload()
    payload["snapshot"] = "URL: https://example.com\n\n[refs em outro formato]"
    assert bw.project_model_browser_payload(payload) == payload


def test_fails_open_when_an_element_has_no_ref():
    payload = _payload()
    payload["elements"] = [dict(element) for element in _ELEMENTS]
    payload["elements"][0].pop("ref")
    assert bw.project_model_browser_payload(payload) == payload


def test_passes_through_results_without_elements():
    assert bw.project_model_browser_payload({"success": True, "text": "ok"}) == {
        "success": True, "text": "ok"}
    assert bw.project_model_browser_payload("string crua") == "string crua"
    assert bw.project_model_browser_payload({"elements": [], "snapshot": ""}) == {
        "elements": [], "snapshot": ""}


# ---------------------------------------------------------------- seam real


class _SnapshotHandler(BaseHTTPRequestHandler):
    token = "test-token"

    def log_message(self, *_args):
        return

    def _json(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self._json(401, {"success": False})
            return
        if self.path == "/health":
            self._json(200, {"success": True, "state": {"ready": True}})
            return
        self._json(404, {"success": False})

    def do_POST(self):
        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self._json(401, {"success": False})
            return
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self._json(200, {"success": True, "result": _payload()})


@pytest.fixture()
def snapshot_controller(tmp_path, monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SnapshotHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    control = tmp_path / "browser-control.json"
    control.write_text(json.dumps({
        "version": 1,
        "url": f"http://127.0.0.1:{server.server_address[1]}",
        "token": _SnapshotHandler.token,
    }))
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER_CONTROL_FILE", str(control))
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER", "1")
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER_ROUTING", "1")
    bw._LAST_HEALTH_AT = 0.0
    bw._LAST_HEALTH_VALUE = False
    bw.clear_workstation_task_binding("task-a")
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    bw._LAST_HEALTH_AT = 0.0
    bw._LAST_HEALTH_VALUE = False
    bw.clear_workstation_task_binding("task-a")


def test_model_facing_handler_ships_the_projected_payload(snapshot_controller):
    raw = bw.workstation_routed_browser_handler(
        "browser_snapshot",
        {},
        fallback=lambda: pytest.fail("legacy fallback must not run"),
        task_id="task-a",
    )
    decoded = json.loads(raw)
    assert decoded["runtime"] == "electron-chromium"
    assert "elements" not in decoded, "o modelo recebeu a lista duplicada"
    assert decoded["elements_projected"] is True
    assert decoded["element_count"] == len(_ELEMENTS)
    # a reconstrução pelo payload do modelo devolve os mesmos alvos
    assert [element["ref"] for element in _reconstruct(decoded)] == [e["ref"] for e in _ELEMENTS]
    unprojected = len(json.dumps(_payload(), ensure_ascii=False))
    assert len(raw) < unprojected


# Regression cases discovered during independent review (2026-10-11).


def test_fail_open_when_label_changes_but_refs_stay_the_same():
    payload = _payload()
    payload["snapshot"] = payload["snapshot"].replace('button "Enviar"', 'button "Excluir"')
    assert bw.project_model_browser_payload(payload) == payload


def test_fail_open_when_inventory_order_diverges():
    payload = _payload()
    first = _render_line(_ELEMENTS[0])
    second = _render_line(_ELEMENTS[1])
    payload["snapshot"] = payload["snapshot"].replace(first + "\n" + second, second + "\n" + first)
    assert bw.project_model_browser_payload(payload) == payload


def test_fail_open_on_duplicate_refs():
    elements = [dict(_ELEMENTS[0]), dict(_ELEMENTS[0])]
    payload = _payload(elements)
    assert bw.project_model_browser_payload(payload) == payload


def test_fail_open_on_unknown_nonempty_inventory_line():
    payload = _payload()
    payload["snapshot"] = payload["snapshot"].replace(
        "Interactive elements:\n", "Interactive elements:\nUNRECOGNIZED INVENTORY\n"
    )
    assert bw.project_model_browser_payload(payload) == payload


def test_tag_differs_from_role_is_preserved_in_index():
    projected = bw.project_model_browser_payload(_payload())
    assert projected["element_index"]["@e3"] == {"tag": "a"}


def test_internal_controller_dispatch_retains_structured_elements(snapshot_controller):
    # The broker also calls call_workstation_browser directly: it is NOT
    # exclusively a model-facing entry point.
    raw = bw.call_workstation_browser("browser_snapshot", {}, task_id="task-a")
    result = json.loads(raw)
    assert result["elements"] == _ELEMENTS
    assert "elements_projected" not in result


# ---------------------------------------------------------------- viewport soft-filter (Fase 1)


def _payload_with_bounds(elements: list[dict], viewport_height: int = 900) -> dict:
    """Build a payload where each element carries bounds.y for viewport filter tests."""
    base = _payload(elements)
    base["viewportHeight"] = viewport_height
    return base


def test_viewport_filter_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HERMES_BROWSER_VIEWPORT_FILTER", raising=False)
    elements = [
        {"ref": "@e1", "tag": "button", "role": "button", "label": "Far",
         "value": "", "disabled": False, "bounds": {"x": 0, "y": 5000, "width": 100, "height": 40}},
    ] * 6
    projected = bw.project_model_browser_payload(_payload_with_bounds(elements))
    assert "viewport_filter" not in projected
    idx = projected.get("element_index", {})
    for entry in idx.values():
        assert "offscreen" not in entry


def test_offscreen_elements_preserved_with_semantic_attributes(monkeypatch):
    monkeypatch.setenv("HERMES_BROWSER_VIEWPORT_FILTER", "1")
    elements = [
        {"ref": "@e1", "tag": "button", "role": "button", "label": "Visible",
         "value": "", "disabled": False, "bounds": {"x": 0, "y": 100, "width": 80, "height": 32}},
        {"ref": "@e2", "tag": "button", "role": "button", "label": "Offscreen Semantic",
         "value": "", "disabled": False, "testid": "far-btn",
         "bounds": {"x": 0, "y": 5000, "width": 80, "height": 32}},
        {"ref": "@e3", "tag": "input", "role": "textbox", "label": "Also Offscreen",
         "value": "", "disabled": False, "name": "far-input",
         "bounds": {"x": 0, "y": 6000, "width": 200, "height": 32}},
        {"ref": "@e4", "tag": "button", "role": "button", "label": "Visible2",
         "value": "", "disabled": False, "bounds": {"x": 0, "y": 200, "width": 80, "height": 32}},
        {"ref": "@e5", "tag": "button", "role": "button", "label": "Offscreen2",
         "value": "", "disabled": False, "testid": "far-btn-2",
         "bounds": {"x": 0, "y": 7000, "width": 80, "height": 32}},
        {"ref": "@e6", "tag": "a", "role": "link", "label": "Link Offscreen",
         "value": "", "disabled": False, "name": "far-link",
         "bounds": {"x": 0, "y": 8000, "width": 120, "height": 32}},
    ]
    projected = bw.project_model_browser_payload(_payload_with_bounds(elements))
    assert projected.get("viewport_filter", {}).get("enabled") is True
    idx = projected.get("element_index", {})
    # Semantic offscreen elements must be preserved with tag
    assert idx.get("@e2", {}).get("offscreen") is True
    assert idx.get("@e2", {}).get("testid") == "far-btn"
    assert idx.get("@e3", {}).get("offscreen") is True
    assert idx.get("@e3", {}).get("name") == "far-input"
    assert idx.get("@e5", {}).get("offscreen") is True
    assert idx.get("@e6", {}).get("offscreen") is True
    # Visible element must NOT be tagged offscreen
    e1_entry = idx.get("@e1", {})
    assert e1_entry.get("offscreen") is not True


def test_fail_open_on_low_element_count(monkeypatch):
    monkeypatch.setenv("HERMES_BROWSER_VIEWPORT_FILTER", "1")
    elements = [
        {"ref": "@e1", "tag": "button", "role": "button", "label": "Only",
         "value": "", "disabled": False, "bounds": {"x": 0, "y": 9000, "width": 80, "height": 32}},
    ]
    projected = bw.project_model_browser_payload(_payload_with_bounds(elements))
    assert "viewport_filter" not in projected
