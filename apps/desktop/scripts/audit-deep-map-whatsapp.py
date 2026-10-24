import json
import os
from pathlib import Path
import urllib.request
import re

def get_control():
    base = os.environ.get("LOCALAPPDATA", "")
    ctrl_path = Path(base) / "HermesWorkstation" / "Runtime" / "browser-control.json"
    with open(ctrl_path, "r", encoding="utf-8") as f:
        return json.load(f)

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
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    ctrl = get_control()

    # 1. Load reference deep map
    ref_map_path = Path("workstation/dogfood/artifacts/site-map-web-whatsapp-com.json")
    with open(ref_map_path, "r", encoding="utf-8") as f:
        ref_map = json.load(f)

    ref_elements = ref_map.get("screens", {}).get("main", {}).get("elements", [])
    print(f"Loaded reference Deep Map: {len(ref_elements)} cataloged elements.")

    # 2. Capture live snapshot (full=True to get raw elements list with attributes)
    print("Capturing live snapshot from Workstation Browser...")
    snap_res = execute_action(ctrl, "browser_snapshot", {"full": True})
    result = snap_res.get("result", {})
    live_elements = result.get("elements", [])
    live_text = result.get("snapshot", "")
    element_count = result.get("element_count", len(live_elements))
    print(f"Live snapshot: {element_count} interactive elements detected in DOM.")

    # 3. Audit Critical Selectors
    critical_checks = {}

    # Check A: Header / Navigation icons (Conversas, Status, Canais, Comunidades)
    nav_icons = ["Conversas", "Ligações", "Status", "Canais", "Comunidades", "Meta AI"]
    found_nav = [icon for icon in nav_icons if any(icon.lower() in (e.get("label") or e.get("text") or "").lower() for e in live_elements)]
    critical_checks["nav_primary_section"] = {
        "expected": nav_icons,
        "found": found_nav,
        "status": "PASS" if len(found_nav) >= 4 else "WARN"
    }

    # Check B: Search Field
    search_el = next((e for e in live_elements if e.get("role") == "textbox" or "pesquisar" in (e.get("label") or "").lower()), None)
    critical_checks["search_input"] = {
        "found": search_el is not None,
        "ref": search_el.get("ref") if search_el else None,
        "role": search_el.get("role") if search_el else None,
        "label": search_el.get("label") if search_el else None,
        "status": "PASS" if search_el else "FAIL"
    }

    # Check C: Filter unread button
    filter_el = next((e for e in live_elements if "filtro" in (e.get("label") or "").lower() or "não lid" in (e.get("label") or "").lower() or "unread" in (e.get("label") or "").lower()), None)
    critical_checks["unread_filter"] = {
        "found": filter_el is not None,
        "ref": filter_el.get("ref") if filter_el else None,
        "label": filter_el.get("label") if filter_el else None,
        "status": "PASS" if filter_el else "WARN"
    }

    # Check D: Active conversation panel (header, composer, send button)
    conv_header = next((e for e in live_elements if e.get("role") == "heading" or "conversation-info-header" in str(e.get("attributes", {}))), None)
    composer = next((e for e in live_elements if e.get("role") == "textbox" and ("mensagem" in (e.get("label") or "").lower() or "message" in (e.get("label") or "").lower())), None)
    send_btn = next((e for e in live_elements if any(kw in (e.get("label") or "").lower() for kw in ["enviar", "send", "mensagem de voz", "voice message"])), None)

    critical_checks["conversation_panel"] = {
        "active_header": conv_header.get("text") or conv_header.get("label") if conv_header else None,
        "composer_found": composer is not None,
        "composer_ref": composer.get("ref") if composer else None,
        "send_or_voice_btn": send_btn.get("label") if send_btn else None,
        "send_ref": send_btn.get("ref") if send_btn else None,
        "status": "ACTIVE_CHAT_DETECTED" if (composer or send_btn) else "CHAT_LIST_ONLY"
    }

    # 4. Compare Live Elements vs Reference Selectors
    matched_selectors = 0
    tested_selectors = 0
    selector_audit = []

    for ref_el in ref_elements[:40]: # Sample 40 primary selectors
        sel = ref_el.get("selector")
        test_id = ref_el.get("testId")
        aria = ref_el.get("ariaLabel")
        tested_selectors += 1

        # Check if matched in live elements
        match = False
        for le in live_elements:
            if test_id and le.get("attributes", {}).get("data-testid") == test_id:
                match = True
                break
            if aria and (le.get("label") == aria or aria.lower() in (le.get("label") or "").lower()):
                match = True
                break
            if ref_el.get("text") and ref_el.get("text") in (le.get("text") or ""):
                match = True
                break

        if match:
            matched_selectors += 1
        selector_audit.append({
            "selector": sel,
            "testId": test_id,
            "ariaLabel": aria,
            "matched": match
        })

    match_rate = (matched_selectors / tested_selectors) * 100 if tested_selectors else 0

    report = {
        "timestamp": "2026-10-24T21:35:00Z",
        "liveTab": {
            "title": "(14) WhatsApp",
            "url": "https://web.whatsapp.com/",
            "element_count": element_count
        },
        "critical_checks": critical_checks,
        "deep_map_match": {
            "tested_sample": tested_selectors,
            "matched": matched_selectors,
            "match_rate_pct": round(match_rate, 1)
        },
        "sample_selector_audit": selector_audit[:10]
    }

    out_file = Path("workstation/dogfood/artifacts/whatsapp-validation-report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n--- RESUMO DA AUDITORIA ---")
    print(f"Taxa de correspondência do Deep Map: {match_rate:.1f}% ({matched_selectors}/{tested_selectors})")
    print(f"Seções críticas:")
    for k, v in critical_checks.items():
        print(f"  - {k}: {v.get('status')}")
    print(f"Relatório gerado em: {out_file}")

if __name__ == "__main__":
    main()
