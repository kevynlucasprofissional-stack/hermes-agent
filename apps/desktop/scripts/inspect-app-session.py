import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open('workstation/dogfood/dados/Sessões Hermes/abrir-aplicativo-whatsapp-2-20261023.json', 'r', encoding='utf-8', errors='ignore') as f:
    d = json.load(f)

msgs = d if isinstance(d, list) else d.get('messages', [])

print(f"Total mensagens: {len(msgs)}")
for i, m in enumerate(msgs):
    if m.get('role') == 'user':
        print(f"User [{i}]:", str(m.get('content'))[:200])

for i, m in enumerate(msgs):
    c = str(m.get('content') or '')
    if any(k in c.lower() for k in ["desktop", "aplicativo", "app", "nativo", "uwp", "store"]):
        for line in c.splitlines():
            if any(k in line.lower() for k in ["desktop", "aplicativo", "uwp", "store"]):
                print(f"[{i}] {line.strip()[:140]}")
                break
