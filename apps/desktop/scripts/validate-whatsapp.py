import json
import os
from pathlib import Path
import urllib.request

def get_control():
    base = os.environ.get("LOCALAPPDATA", "")
    ctrl_path = Path(base) / "HermesWorkstation" / "Runtime" / "browser-control.json"
    with open(ctrl_path, "r", encoding="utf-8") as f:
        return json.load(f)

def check_health(ctrl):
    req = urllib.request.Request(
        ctrl["url"] + "/health",
        headers={"Authorization": f"Bearer {ctrl['token']}"}
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read().decode("utf-8"))

def execute_action(ctrl, action, args=None, task_id="20261024_143448_c0afe6", session_id="20261024_143448_c0afe6"):
    payload = {
        "action": action,
        "arguments": args or {},
        "task_id": task_id,
        "session_id": session_id
    }
    req = urllib.request.Request(
        ctrl["url"] + "/v1/action",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {ctrl['token']}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    ctrl = get_control()
    print("Checking health...")
    health = check_health(ctrl)
    print(f"Health state: ready={health.get('state', {}).get('ready')}, activeTabId={health.get('state', {}).get('activeTabId')}")

    tabs = health.get("state", {}).get("tabs", [])
    print(f"Open tabs ({len(tabs)}):")
    for t in tabs:
        print(f"  - [{t.get('id')}] {t.get('title')} ({t.get('url')}) ownerTaskId={t.get('ownerTaskId')}")

    print("\nRequesting browser_snapshot for active task...")
    res = execute_action(ctrl, "browser_snapshot", {"full": False})
    print(f"Snapshot success: {res.get('success')}")
    result = res.get("result", {})
    element_count = result.get("element_count", 0)
    print(f"Element count: {element_count}")
    print(f"Snapshot text snippet:\n{result.get('snapshot', '')[:400]}")

if __name__ == "__main__":
    main()
