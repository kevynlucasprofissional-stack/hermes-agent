import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open('workstation/dogfood/dados/Sessões Hermes/abrir-aplicativo-whatsapp-2-20261023.json', 'r', encoding='utf-8', errors='ignore') as f:
    d = json.load(f)

msgs = d if isinstance(d, list) else d.get('messages', [])

for i in range(150, min(166, len(msgs))):
    m = msgs[i]
    role = m.get('role')
    content = str(m.get('content') or '')
    print(f"\n--- Mensagem [{i}] ({role}) ---")
    print(content[:600])
