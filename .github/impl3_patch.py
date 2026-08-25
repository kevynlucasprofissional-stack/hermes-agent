import base64
import json
import os
import urllib.parse
import urllib.request

REPO = "kevynlucasprofissional-stack/hermes-agent"
BRANCH = "validation/impl3-browser-session-capability"
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com"


def api(method: str, path: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "hermes-workstation-impl3",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read()
    return json.loads(body.decode("utf-8")) if body else {}


branch_ref = api("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
base_sha = branch_ref["object"]["sha"]
base_commit = api("GET", f"/repos/{REPO}/git/commits/{base_sha}")
base_tree = base_commit["tree"]["sha"]

paths = ["tools/registry.py", "tools/browser_workstation.py", "model_tools.py"]
contents: dict[str, str] = {}
for path in paths:
    item = api(
        "GET",
        f"/repos/{REPO}/contents/{urllib.parse.quote(path, safe='/')}?ref={base_sha}",
    )
    contents[path] = base64.b64decode(item["content"]).decode("utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = contents[path]
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}")
    contents[path] = text.replace(old, new, 1)


replace_once(
    "tools/registry.py",
    '    def get_definitions(self, tool_names: Set[str], quiet: bool = False) -> List[dict]:\n',
    '    def get_definitions(\n'
    '        self,\n'
    '        tool_names: Set[str],\n'
    '        quiet: bool = False,\n'
    '        force_available: Optional[Set[str]] = None,\n'
    '    ) -> List[dict]:\n',
)
replace_once(
    "tools/registry.py",
    '        result = []\n        # Per-call cache on top of the 30 s TTL — handles repeat probes of the\n',
    '        result = []\n'
    '        # Session/surface owners may explicitly preserve a schema after\n'
    '        # deciding capability outside check_fn. This is intentionally a\n'
    '        # per-call input: it is never stored in the process-wide check_fn\n'
    '        # cache, and runtime dispatch still performs its own health/recovery\n'
    '        # checks. See Workstation Browser session capability.\n'
    '        forced = set(force_available or ())\n'
    '        # Per-call cache on top of the 30 s TTL — handles repeat probes of the\n',
)
replace_once(
    "tools/registry.py",
    '            if entry.check_fn:\n                if entry.check_fn not in check_results:\n',
    '            if entry.check_fn and name not in forced:\n                if entry.check_fn not in check_results:\n',
)

replace_once(
    "tools/browser_workstation.py",
    'def workstation_browser_enabled() -> bool:\n'
    '    if not _bool_env("HERMES_WORKSTATION_BROWSER", True):\n'
    '        return False\n'
    '    return bool(_browser_config().get("enabled", True))\n\n\n'
    'def workstation_routing_enabled() -> bool:\n',
    'def workstation_browser_enabled() -> bool:\n'
    '    if not _bool_env("HERMES_WORKSTATION_BROWSER", True):\n'
    '        return False\n'
    '    return bool(_browser_config().get("enabled", True))\n\n\n'
    '_WORKSTATION_SCHEMA_TOOLS = frozenset({\n'
    '    "browser_navigate",\n'
    '    "browser_snapshot",\n'
    '    "browser_click",\n'
    '    "browser_type",\n'
    '    "browser_scroll",\n'
    '    "browser_back",\n'
    '    "browser_press",\n'
    '    "browser_get_images",\n'
    '    "browser_vision",\n'
    '    "browser_console",\n'
    '})\n\n\n'
    'def workstation_schema_tools_for_current_session() -> set[str]:\n'
    '    """Schemas structurally owned by a Desktop/Workstation session.\n\n'
    '    Surface capability belongs to the session source, not to a 200 ms\n'
    '    controller health probe. Returning these names does *not* claim the\n'
    '    controller is reachable; workstation_routed_browser_handler() keeps\n'
    '    the authoritative health/recovery/fail-closed decision at dispatch.\n'
    '    """\n'
    '    if not workstation_browser_enabled():\n'
    '        return set()\n'
    '    try:\n'
    '        from gateway.session_context import get_session_env\n'
    '    except Exception:\n'
    '        return set()\n'
    '    source = str(get_session_env("HERMES_SESSION_SOURCE", "") or "").strip().lower()\n'
    '    platform = str(get_session_env("HERMES_SESSION_PLATFORM", "") or "").strip().lower()\n'
    '    surface = source or platform\n'
    '    if surface != "desktop":\n'
    '        return set()\n'
    '    return set(_WORKSTATION_SCHEMA_TOOLS)\n\n\n'
    'def workstation_routing_enabled() -> bool:\n',
)

replace_once(
    "model_tools.py",
    'def get_tool_definitions(\n',
    'def _session_force_available_tools() -> frozenset[str]:\n'
    '    """Return schemas guaranteed by the current client surface.\n\n'
    '    This decision is intentionally outside registry check_fn: one gateway\n'
    '    process serves many session sources, while check_fn probes are cached.\n'
    '    """\n'
    '    try:\n'
    '        from tools.browser_workstation import workstation_schema_tools_for_current_session\n'
    '        return frozenset(workstation_schema_tools_for_current_session())\n'
    '    except Exception:\n'
    '        return frozenset()\n\n\n'
    'def get_tool_definitions(\n',
)
replace_once(
    "model_tools.py",
    '    cache_key = None\n    if quiet_mode:\n',
    '    force_available_tools = _session_force_available_tools()\n'
    '    cache_key = None\n'
    '    if quiet_mode:\n',
)
replace_once(
    "model_tools.py",
    '                profile_scope,\n            )\n',
    '                profile_scope,\n'
    '                force_available_tools,\n'
    '            )\n',
)
replace_once(
    "model_tools.py",
    '    result = _compute_tool_definitions(enabled_toolsets, disabled_toolsets, quiet_mode,\n                                       skip_tool_search_assembly=skip_tool_search_assembly)\n',
    '    result = _compute_tool_definitions(\n'
    '        enabled_toolsets,\n'
    '        disabled_toolsets,\n'
    '        quiet_mode,\n'
    '        skip_tool_search_assembly=skip_tool_search_assembly,\n'
    '        force_available_tools=force_available_tools,\n'
    '    )\n',
)
replace_once(
    "model_tools.py",
    'def _compute_tool_definitions(\n'
    '    enabled_toolsets: Optional[List[str]] = None,\n'
    '    disabled_toolsets: Optional[List[str]] = None,\n'
    '    quiet_mode: bool = False,\n'
    '    skip_tool_search_assembly: bool = False,\n'
    ') -> List[Dict[str, Any]]:\n',
    'def _compute_tool_definitions(\n'
    '    enabled_toolsets: Optional[List[str]] = None,\n'
    '    disabled_toolsets: Optional[List[str]] = None,\n'
    '    quiet_mode: bool = False,\n'
    '    skip_tool_search_assembly: bool = False,\n'
    '    force_available_tools: Optional[set[str]] = None,\n'
    ') -> List[Dict[str, Any]]:\n',
)
replace_once(
    "model_tools.py",
    '    # Ask the registry for schemas (only returns tools whose check_fn passes)\n'
    '    filtered_tools = registry.get_definitions(tools_to_include, quiet=quiet_mode)\n',
    '    # Ask the registry for schemas. Session-surface capabilities can\n'
    '    # bypass reachability check_fn filtering for selected schemas only;\n'
    '    # disabled/unselected tools are never re-added.\n'
    '    forced = set(force_available_tools or ()) & tools_to_include\n'
    '    filtered_tools = registry.get_definitions(\n'
    '        tools_to_include, quiet=quiet_mode, force_available=forced\n'
    '    )\n',
)

contents["tests/tui_gateway/test_workstation_browser_schema_capability.py"] = r'''"""Workstation Browser schema capability is owned by the Desktop session."""

import pytest

import model_tools
from gateway.session_context import clear_session_vars, set_session_vars
from tools import browser_workstation
from tools.registry import registry

TARGET = "browser_navigate"


def _tool_names(platform: str, source: str) -> set[str]:
    tokens = set_session_vars(platform=platform, source=source, session_id=f"schema-{platform}")
    try:
        return {
            item["function"]["name"]
            for item in model_tools.get_tool_definitions(
                enabled_toolsets=["browser"],
                quiet_mode=True,
                skip_tool_search_assembly=True,
            )
        }
    finally:
        clear_session_vars(tokens)


@pytest.fixture(autouse=True)
def clean_schema_cache(monkeypatch):
    monkeypatch.delenv("HERMES_DESKTOP", raising=False)
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER", "1")
    monkeypatch.setattr(browser_workstation, "_browser_config", lambda: {"enabled": True, "routing_enabled": True})
    model_tools._clear_tool_defs_cache()
    yield
    model_tools._clear_tool_defs_cache()


def _force_probe_false(monkeypatch):
    entry = registry.get_entry(TARGET)
    assert entry is not None
    monkeypatch.setattr(entry, "check_fn", lambda: False)
    monkeypatch.setattr(model_tools, "validate_toolset", lambda name: name == "browser")
    monkeypatch.setattr(model_tools, "resolve_toolset", lambda name: [TARGET] if name == "browser" else [])


def test_desktop_surface_preserves_browser_schema_when_probe_is_false(monkeypatch):
    _force_probe_false(monkeypatch)
    assert TARGET in _tool_names("desktop", "desktop")


def test_desktop_schema_cache_does_not_leak_into_tui(monkeypatch):
    _force_probe_false(monkeypatch)
    assert TARGET in _tool_names("desktop", "desktop")
    assert TARGET not in _tool_names("tui", "tui")


def test_process_desktop_env_does_not_grant_tui_browser_capability(monkeypatch):
    monkeypatch.setenv("HERMES_DESKTOP", "1")
    tokens = set_session_vars(platform="tui", source="tui", session_id="schema-tui-env")
    try:
        assert browser_workstation.workstation_schema_tools_for_current_session() == set()
    finally:
        clear_session_vars(tokens)


def test_desktop_source_grants_capability_without_process_env():
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="schema-desktop-no-env")
    try:
        tools = browser_workstation.workstation_schema_tools_for_current_session()
        assert TARGET in tools
        assert "browser_snapshot" in tools
        assert "browser_exec" not in tools
    finally:
        clear_session_vars(tokens)
'''

entries = []
for path, content in contents.items():
    blob = api("POST", f"/repos/{REPO}/git/blobs", {"content": content, "encoding": "utf-8"})
    entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

# Remove the two temporary patching files from the resulting candidate tree.
entries.append({"path": ".github/impl3_patch.py", "mode": "100644", "type": "blob", "sha": None})
entries.append({"path": ".github/workflows/impl3-session-capability-patch.yml", "mode": "100644", "type": "blob", "sha": None})

new_tree = api("POST", f"/repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": entries})
new_commit = api(
    "POST",
    f"/repos/{REPO}/git/commits",
    {
        "message": "feat(workstation): make browser schema a desktop session capability",
        "tree": new_tree["sha"],
        "parents": [base_sha],
    },
)
api(
    "PATCH",
    f"/repos/{REPO}/git/refs/heads/{BRANCH}",
    {"sha": new_commit["sha"], "force": False},
)
print(new_commit["sha"])
