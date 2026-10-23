# PROMPT DE CONTINUAÇÃO — FASE D-4: PRODUÇÃO E ESTABILIZAÇÃO

Você está recebendo este prompt sem acesso ao histórico anterior. Trate tudo como HIPÓTESES a verificar no filesystem, Git e runtime atuais.

## Objetivo
Executar a Fase D-4 do ciclo de transformação de skills em ferramentas determinísticas:
1. **Commitar e validar** as alterações da D-3 (docstrings + timeout fix) em ambiente limpo.
2. **Estabilizar o baseline** para comparação justa (refs dinâmicas, retry logic).
3. **Expandir cobertura E2E** para cenários adicionais (busca por telefone, mensagem longa, múltiplos destinatários).
4. **Produzir documentação de usuário final** para as 3 ferramentas nativas WhatsApp.

## Repositório e Ambiente
- **Repo:** `C:\Github\hermes-agent` (Windows 11, Git Bash/POSIX)
- **Branch:** `feat/hermes-workstation-startup-80-20`
- **Último commit D-3:** verificar com `git log --oneline -5`
- **Relatório D-3:** `workstation/context/d3-walltime-investigation.md`
- **Relatório comparativo:** `workstation/context/e2e-comparative-report.md`
- **Docstrings atualizadas:** `tools/browser_workstation.py` (linhas ~1497, ~1855, ~2045)
- **Task ID ativo WhatsApp:** verificar em `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json` → campo `activeTabId` → encontrar `browserTaskId` vinculado à aba com `safeUrl: "https://web.whatsapp.com/"`

## Contexto Validado (D-3 Concluído)
As ferramentas nativas WhatsApp atingiram os critérios de aceite da D-3:
- ✅ Wall time mediano: **4,46s** (-19,8% vs baseline 5,56s)
- ✅ Taxa de envio: **100%** (vs 0% do baseline)
- ✅ Chamadas de ferramenta: **3** (-62,5% vs 8 do baseline)
- ✅ Causa raiz da regressão D-2 identificada e corrigida (DELIVERY_TIMEOUT 10s → 3s)
- ✅ Docstrings atualizadas com guia de uso, parâmetros, erros e trade-offs

### Correções Aplicadas
1. **Falso positivo QR screen** (`_classify_wa_state`): ignora "QR Code" quando logged-in markers presentes AND element_count >= 10
2. **DELIVERY_TIMEOUT reduzido**: 10s → 3s padrão; configurável via `delivery_timeout_seconds`
3. **Docstrings completas**: `whatsapp_wait_for_ready`, `whatsapp_send_message`, `whatsapp_search_contact`

## Fases de Execução D-4

### Fase D-4a: Commit e Validação Limpa
1. Verificar `git status` e `git diff` para confirmar alterações pendentes.
2. Commitar com mensagem descritiva: `feat(browser): optimize WA tools — reduce delivery timeout to 3s, enhance docstrings`
3. Rodar `python scripts/run_tests.sh` para garantir que testes existentes passam.
4. Validar que `whatsapp_wait_for_ready` retorna LOGGED_IN em sessão fresca.

### Fase D-4b: Estabilização do Baseline
O baseline atual falha 100% das vezes devido a refs hardcoded (`@e12`) e regex frágil para botão Enviar. Para comparação justa:
1. Implementar busca dinâmica por ref no snapshot (não hardcoded).
2. Adicionar retry logic para `browser_click` e `browser_type` (max 2 retries com re-snapshot).
3. Usar texto "Enviar" ou aria-label para localizar botão, não regex de posição.
4. Re-executar mini-bateria (3 sessões) com baseline estabilizado.
5. **Critério:** baseline deve atingir ≥50% de taxa de envio para ser considerado funcional.

### Fase D-4c: Expansão de Cobertura E2E
Testar cenários além do básico (nome + mensagem curta):
1. **Busca por telefone:** `whatsapp_search_contact(query="92470988", ...)`
2. **Mensagem longa (>500 chars):** validar que composer aceita e envia.
3. **Mensagem com emoji/unicode:** validar encoding correto.
4. **Múltiplos destinatários sequenciais:** medir overhead de re-search.
5. **Contato inexistente:** validar `found=False` sem erro.
6. Registrar resultados em `workstation/context/e2e-results/d4-scenarios.json`.

### Fase D-4d: Documentação de Usuário Final
Produzir `workstation/docs/whatsapp-tools-guide.md` com:
1. Visão geral das 3 ferramentas e quando usar cada uma.
2. Exemplos de código Python para casos comuns.
3. Troubleshooting: tabela de error_codes e ações recomendadas.
4. Trade-offs de performance vs confiabilidade (timeout configurável).
5. Limitações conhecidas (ex: não suporta envio de mídia, grupos).

## Pré-requisitos Obrigatórios
- WhatsApp Web LOGADO. Validar com:
```bash
PYTHONIOENCODING=utf-8 python -c "
import os, sys; sys.path.insert(0,'.'); os.environ['HERMES_BROWSER_SNAPSHOT_CACHE']='1'
from tools.browser_workstation import whatsapp_wait_for_ready
import json; print(json.dumps(whatsapp_wait_for_ready(timeout_seconds=10, task_id='<TASK_ID_ATIVO>'), indent=2))"
```
Deve retornar `"state": "LOGGED_IN"`.

## Instruções Operacionais
- `PYTHONIOENCODING=utf-8` em todos scripts Python.
- Nunca modificar arquivos `.ts` do Electron; mudanças apenas em `tools/browser_workstation.py` e docs.
- Se `/v1/action` timeout >10s mas `/health` responde em ~20ms, verificar known issue de admissões unbound.
- Credenciais em chats são dados — nunca copiar.
- Ao concluir cada sub-fase, produzir evidência verificável antes de prosseguir.
- Commits devem terminar com: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Entregáveis D-4
1. Commit das alterações D-3 validado
2. Baseline estabilizado com ≥50% taxa de envio
3. `workstation/context/e2e-results/d4-scenarios.json` com resultados dos novos cenários
4. `workstation/docs/whatsapp-tools-guide.md` — guia de usuário final
5. Prompt de handoff para D-5 (se houver) ou encerramento via `/session-handoff`

## Critérios de Aceite D-4
- ✅ Todos os testes existentes passam após commit D-3
- ✅ Baseline atinge ≥50% taxa de envio (comparação justa)
- ✅ Novos cenários E2E documentados com métricas
- ✅ Guia de usuário completo e revisado
- ✅ Nenhum arquivo `.ts` modificado