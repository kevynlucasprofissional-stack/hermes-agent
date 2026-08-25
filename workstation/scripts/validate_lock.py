from __future__ import annotations
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
lock_path = root / "workstation" / "components.lock.json"
data = json.loads(lock_path.read_text(encoding="utf-8"))
assert data["schema_version"] == 1
assert data["components"]["hermes-agent"]["ref"] == data["channel"]["stable"]["hermes_ref"]
assert data["components"]["hermes-agent"]["vendored"] is False
for name, component in data["components"].items():
    assert component.get("repository"), f"{name}: repository missing"
    assert component.get("ref"), f"{name}: ref missing"
print(f"OK: {lock_path}")
