import json
import os
from collections import Counter

base = r"C:\Github\hermes-agent\workstation\dogfood\dados\Sessões Hermes"
files = [
    "automatizar-envio-de-mensagem-no-whatsapp-web-20261021.json",
    "enviar-mensagem-teste-para-kevyn-acirv-no-whatsa-20261021.json",
    "enviar-mensagem-de-agradecimento-pelo-whatsapp-20261021.json",
]

for fname in files:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print(f"NOT FOUND: {fname}")
        continue
    with open(path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    msgs = d.get("messages", [])
    print(f"=== {fname} ({len(msgs)} msgs) ===")

    tool_calls = []
    errors = []
    browser_tools = []
    token_mentions = 0

    for m in msgs:
        content = m.get("content", "")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "tool_use":
                    name = block.get("name", "unknown")
                    tool_calls.append(name)
                    if "browser" in name.lower():
                        browser_tools.append(name)
                elif btype == "tool_result":
                    rc = block.get("content", "")
                    if isinstance(rc, str):
                        low = rc.lower()
                        if any(k in low for k in ("error", "fail", "timeout", "exception")):
                            errors.append(rc[:200])
        elif isinstance(content, str):
            low = content.lower()
            if "token" in low:
                token_mentions += 1

    tc_counter = Counter(tool_calls)
    bt_counter = Counter(browser_tools)
    print(f"  Top tool calls: {dict(tc_counter.most_common(15))}")
    print(f"  Browser tools: {dict(bt_counter.most_common(10))}")
    print(f"  Errors: {len(errors)}")
    for e in errors[:5]:
        print(f"    ERR: {e[:180]}")
    print(f"  Token mentions in assistant text: {token_mentions}")
    print()