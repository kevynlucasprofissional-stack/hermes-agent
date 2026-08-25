from __future__ import annotations
import json
from pathlib import Path

ALLOWED_IMPORTED = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
root = Path(__file__).resolve().parents[2]
data = json.loads((root / "workstation" / "components.lock.json").read_text(encoding="utf-8"))

for name, component in data["components"].items():
    if component.get("vendored") and component.get("license") not in ALLOWED_IMPORTED:
        raise SystemExit(f"Refusing incompatible vendored component: {name} ({component.get('license')})")

notices = (root / "workstation" / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
assert "BrowserOS" in notices and "AGPL" in notices
print("OK: Workstation license policy")
