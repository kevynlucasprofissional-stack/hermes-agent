import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open('workstation/dogfood/dados/Sessões Hermes/enviar-convites-de-oficina-via-wa.me-20261023.json', 'r', encoding='utf-8', errors='ignore') as f:
    d = json.load(f)

msgs = d if isinstance(d, list) else d.get('messages', [])

print(f"Total mensagens: {len(msgs)}")

tool_invocations = []
for i, m in enumerate(msgs):
    role = m.get('role')
    tcs = m.get('tool_calls') or []
    for tc in tcs:
        fn = tc.get('function', {})
        name = fn.get('name')
        args = fn.get('arguments', '')
        tool_invocations.append((i, name, args[:80]))

print(f"Total de tool calls: {len(tool_invocations)}")
from collections import Counter
counts = Counter([t[1] for t in tool_invocations])
print("Frequência de ferramentas:", counts)

# Inspect what went wrong or how sending was performed
for i, m in enumerate(msgs):
    content = str(m.get('content') or '')
    if any(k in content.lower() for k in ["bloqueio", "limite", "ban", "intervalo", "segundos", "antispam", "delay", "duplicad"]):
        for line in content.splitlines():
            if any(k in line.lower() for k in ["bloqueio", "limite", "ban", "intervalo", "antispam", "delay", "segundo", "duplicad"]):
                print(f"[{i}] {line.strip()[:140]}")
                break
