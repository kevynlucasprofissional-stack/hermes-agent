import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sessions_dir = Path("workstation/dogfood/dados/Sessões Hermes")
reports_dir = Path("workstation/dogfood/dados/Relatório de sessões de IA")

print("--- ANALISANDO RELATÓRIOS TÉCNICOS ESPECÍFICOS DE WHATSAPP ---")
if reports_dir.exists():
    for rpath in reports_dir.glob("*WhatsApp*.md"):
        print(f"\nRelatório: {rpath.name}")
        with open(rpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Look for failures and learnings
        lines = content.splitlines()
        print("Total de linhas:", len(lines))
        alert_lines = [l.strip() for l in lines if any(k in l.lower() for k in ["falha", "erro", "stale", "bloqueio", "risco", "incidente", "guard", "trava", "limite", "reconciliation"])]
        print(f"Linhas relevantes de risco/aprendizado ({len(alert_lines)}):")
        for al in alert_lines[:8]:
            print(f"  * {al[:140]}")

print("\n--- ANALISANDO SESSÕES JSON MAIS RECENTES ---")
recent_files = [
    "enviar-convites-de-oficina-via-wa.me-20261023.json",
    "abrir-aplicativo-whatsapp-2-20261023.json",
    "criar-banco-de-dados-para-controle-do-whatsapp-20261022.json",
    "enviar-mensagem-de-agradecimento-pelo-whatsapp-20261021.json",
    "automatizar-envio-de-mensagem-no-whatsapp-web-20261021.json",
]

for fname in recent_files:
    fpath = sessions_dir / fname
    if not fpath.exists():
        continue
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    msgs = data if isinstance(data, list) else data.get("messages", data.get("history", []))
    print(f"\n======================================")
    print(f"Sessão: {fname} (Total steps: {len(msgs)})")

    tools = set()
    user_requests = []
    assistant_issues = []

    for m in msgs:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content") or ""

        if role == "user" and isinstance(content, str):
            user_requests.append(content[:150])

        for tc in (m.get("tool_calls") or []):
            if isinstance(tc, dict):
                fn = tc.get("function", {})
                if fn.get("name"):
                    tools.add(fn.get("name"))

        # Check if assistant experienced an error or blocker
        if role in ["assistant", "tool"]:
            c_str = str(content)
            for line in c_str.split("\n"):
                lower = line.lower()
                if any(k in lower for k in ["stale", "reconciliation_required", "bloquead", "limite", "ban", "spam", "não encontrado", "error", "falhou"]):
                    s = line.strip()
                    if len(s) > 15 and not s.startswith("```"):
                        assistant_issues.append(s[:140])

    print(f"User Request Inicial: {user_requests[0] if user_requests else 'N/A'}")
    if len(user_requests) > 1:
        print(f"User Request Secundário: {user_requests[1]}")
    print(f"Ferramentas usadas: {list(tools)}")
    print(f"Problemas / Travas encontrados ({len(assistant_issues)}):")
    # Deduplicate issues while preserving order
    seen = set()
    dedup_issues = []
    for iss in assistant_issues:
        if iss not in seen:
            seen.add(iss)
            dedup_issues.append(iss)
    for iss in dedup_issues[:8]:
        print(f"  * {iss}")
