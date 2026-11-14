"""WA-OPC-011: one-shot, strictly read-only diagnostic of the owned WhatsApp tab.

Invoke only AFTER the agent has opened its authorized self-chat in the native
BrowserTask. Nothing here navigates, clicks, sends, uploads or changes a DB.
"""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from workstation.integrations.hermes.whatsapp_native_schema_probe import probe_native_schema


def _print(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WA-OPC-011 native self-chat read-only probe")
    parser.add_argument("--task-id", required=True, help="Actual owned BrowserTask ID")
    parser.add_argument("--session-id", required=True, help="Actual owning Hermes session ID")
    args = parser.parse_args(argv)

    if any(
        not val.strip() or val.strip().lower() in {"default", "active", "latest", "unbound"}
        for val in (args.task_id, args.session_id)
    ):
        _print({"status": "HOLD", "reason": "TASK_IDENTITY_REQUIRED",
                "can_send": False, "independently_verified": False})
        return 2

    from gateway.session_context import clear_session_vars, set_session_vars
    from workstation.integrations.hermes.adapter import install_workstation_adapter

    tokens = set_session_vars(platform="desktop", source="desktop", session_id=args.session_id)
    try:
        install_workstation_adapter()
        result = probe_native_schema(task_id=args.task_id, session_id=args.session_id)
        if not isinstance(result, dict):
            raise ValueError("Invalid diagnostic result")
    except Exception:
        # Controller/authorization errors must never print private chat data.
        _print({"status": "HOLD", "reason": "NATIVE_PROBE_ERROR",
                "can_send": False, "independently_verified": False})
        return 1
    finally:
        clear_session_vars(tokens)

    _print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
