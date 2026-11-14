"""Profile the real native WhatsApp lookup without composing or sending."""
from __future__ import annotations
import json
from time import perf_counter
import tools.browser_workstation as bridge
from workstation.scripts.wa_hyb_live_lookup_smoke import main as smoke

original = bridge._dispatch
timings: list[tuple[str,float,str]] = []

def monitored(action, arguments, **kwargs):
    start = perf_counter()
    try:
        result = original(action, arguments, **kwargs)
        status = result.get("status") if isinstance(result, dict) else ""
        timings.append((action, round(perf_counter()-start, 3), str(status or "ok")))
        return result
    except Exception as exc:
        timings.append((action, round(perf_counter()-start, 3), type(exc).__name__))
        raise

bridge._dispatch = monitored
started = perf_counter()
try:
    status = smoke()
finally:
    bridge._dispatch = original
    print(json.dumps({
        "elapsed_seconds": round(perf_counter()-started, 2),
        "steps": len(timings),
        "by_action": [
            {"action":name, "seconds":seconds, "status":state}
            for name,seconds,state in timings
        ],
    }, ensure_ascii=False))
raise SystemExit(status)
