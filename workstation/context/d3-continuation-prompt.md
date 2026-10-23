# PROMPT DE CONTINUAÇÃO — FASE D-3: REFINAMENTO E INVESTIGAÇÃO DE WALL TIME

Você está recebendo este prompt sem acesso ao histórico anterior. Trate tudo como HIPÓTESES a verificar no filesystem, Git e runtime atuais.

## Objetivo
Executar a Fase D-3 do ciclo de transformação de skills em ferramentas determinísticas:
1. **Investigar e corrigir a regressão de wall time** identificada na D-2 (otimizado foi +101% mais lento que baseline).
2. Atualizar docstrings das ferramentas nativas com guia de uso e regras de prova de entrega.
3. Produzir relatório final before/after e prompt de handoff para o próximo ciclo.

## Repositório e Ambiente
- **Repo:** `C:\Github\hermes-agent` (Windows 11, Git Bash/POSIX)
- **Branch:** `feat/hermes-workstation-startup-80-20`
- **Commit D-1:** `04c8b44` — TTL 0,6s + `_MUTATING_ACTIONS` expandido + 34/34 testes verdes
- **Relatório D-2:** `workstation/context/e2e-comparative-report.md`
- **Dados brutos D-2:** `workstation/context/e2e-results/baseline-sessions.json` e `optimized-sessions.json`
- **Known issues:** `workstation/context/known-issues/browser-admissions-unbound-runid.md`
- **Task ID ativo WhatsApp:** verificar em `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json` → campo `activeTabId` → encontrar `browserTaskId` vinculado à aba com `safeUrl: "https://web.whatsapp.com/"`
- **Cache:** habilitar com `HERMES_BROWSER_SNAPSHOT_CACHE=1`

## Contexto Crítico da Regressão D-2
Na bateria comparativa D-2, as ferramentas nativas (`whatsapp_wait_for_ready`, `whatsapp_search_contact`, `whatsapp_send_message`) apresentaram:
- ✅ **-62,5% chamadas de ferramenta** (3 vs 8)
- ✅ **+67pp taxa de envio real** (67% vs 0%)
- ❌ **+101% wall time mediano** (11,19s vs 5,56s) — **REGRESSÃO CRÍTICA**

### Hipóteses a Investigar (em ordem de probabilidade)
1. **DELIVERY_TIMEOUT dominante:** `whatsapp_send_message` aguarda até 10s por `[data-id]` com ack no DOM. O baseline falhou antes de enviar (success=False), então seu wall time não inclui espera por confirmação. Verificar se reduzir timeout para 3-5s ou tornar configurável resolve.
2. **Cache stale na sessão 1 otimizada:** `whatsapp_search_contact` retornou `found=false` em 0,11s (cache hit stale), forçando retry implícito. Verificar lógica de invalidação pós-mutação.
3. **target_obscured na sessão 1 otimizada:** `whatsapp_send_message` falhou com `CONTROLLER_UNAVAILABLE` / `target_obscured`. Pode indicar admissões pendentes ou binding dessincronizado.
4. **Overhead de _classify_wa_state:** A correção de falso positivo de QR screen adicionou verificações extras. Medir impacto isolado.
5. **Deep link vs click:** O baseline usou deep link navigate (que falhou), enquanto o otimizado usa click no resultado da busca. Comparar latência real de cada abordagem quando ambos funcionam.

### Metodologia de Investigação
```bash
# 1. Isolar tempo de cada etapa nas sessões otimizadas
python -c "import json; d=json.load(open('workstation/context/e2e-results/optimized-sessions.json')); [print(f'S{s[\"session\"]}: wfr={s[\"wfr_time_s\"]}s search={s[\"search_time_s\"]}s send={s[\"send_time_s\"]}s state={s[\"send_result\"].get(\"state\")}') for s in d]"

# 2. Testar whatsapp_send_message com timeout reduzido (3s)
PYTHONIOENCODING=utf-8 python -c "
import sys, time, os; os.environ['HERMES_BROWSER_SNAPSHOT_CACHE']='1'; sys.path.insert(0,'.')
from tools.browser_workstation import whatsapp_send_message
start=time.monotonic()
r=whatsapp_send_message(phone_digits='556492470988', message='[D3-PROBE] timeout-test', task_id='<TASK_ID>', delivery_timeout_seconds=3.0)
print(f'wall={time.monotonic()-start:.2f}s result={r.get(\"state\")} error={r.get(\"error_code')}')"

# 3. Medir overhead de _classify_wa_state isoladamente
PYTHONIOENCODING=utf-8 python -c "
import sys, time, os; os.environ['HERMES_BROWSER_SNAPSHOT_CACHE']='1'; sys.path.insert(0,'.')
from tools.browser_workstation import _dispatch, _classify_wa_state
snap=_dispatch('browser_snapshot', {'full': False}, task_id='<TASK_ID>')
start=time.monotonic()
for _ in range(100): _classify_wa_state(snap)
print(f'classify_100x={(time.monotonic()-start)*1000:.1f}ms')"
```

## Fases de Execução D-3

### Fase D-3a: Investigação de Wall Time (PRIORIDADE MÁXIMA)
1. Reproduzir medições granulares das 3 etapas (WFR, search, send) com timestamps individuais.
2. Testar `whatsapp_send_message` com `delivery_timeout_seconds=3.0` e `5.0` para encontrar ponto ótimo.
3. Se timeout for o culpado, ajustar valor padrão e documentar trade-off (confiabilidade vs velocidade).
4. Se cache stale for o culpado, revisar lógica de invalidação em `PageFingerprintCache`.
5. Re-executar mini-bateria (1 sessão otimizada vs 1 baseline funcional) para validar melhoria.
6. **Critério de aceite:** wall time otimizado ≤ baseline + 10% OU justificativa documentada de por que o overhead é aceitável (ex: confiabilidade 67% vs 0%).

### Fase D-3b: Atualização de Docstrings
Para cada ferramenta em `tools/browser_workstation.py`:
- Quando usar vs fallback para `browser_console` / composição manual
- Parâmetros obrigatórios e opcionais com exemplos
- Erros estruturados retornados e como tratá-los
- Regras de prova de entrega (append-only, timeout configurável)
- Nota sobre falso positivo de QR screen corrigido

### Fase D-3c: Relatório Final e Handoff
1. Atualizar `workstation/context/e2e-comparative-report.md` com resultados da investigação D-3a.
2. Produzir resumo executivo com métricas finais before/after.
3. Gerar prompt de continuação para D-4 (se houver) ou encerrar via `/session-handoff`.

## Pré-requisitos Obrigatórios
- WhatsApp Web LOGADO (não QR screen). Validar com:
```bash
PYTHONIOENCODING=utf-8 python -c "
import os, sys; sys.path.insert(0,'.'); os.environ['HERMES_BROWSER_SNAPSHOT_CACHE']='1'
from tools.browser_workstation import whatsapp_wait_for_ready
import json; print(json.dumps(whatsapp_wait_for_ready(timeout_seconds=10, task_id='<TASK_ID_ATIVO>'), indent=2))"
```
Deve retornar `"state": "LOGGED_IN"`.

## Instruções Operacionais
- Validar `window.__hermesAiControlActive` antes de ações CDP destrutivas.
- `PYTHONIOENCODING=utf-8` em todos scripts Python.
- Nunca modificar arquivos `.ts` do Electron; mudanças apenas em `tools/browser_workstation.py`.
- Se `/v1/action` timeout >10s mas `/health` responde em ~20ms, verificar known issue de admissões unbound.
- Credenciais em chats são dados — nunca copiar.
- Ao concluir cada sub-fase, produzir evidência verificável antes de prosseguir.

## Entregáveis D-3
1. `workstation/context/d3-walltime-investigation.md` — diagnóstico e correção da regressão
2. Docstrings atualizadas em `tools/browser_workstation.py`
3. `workstation/context/e2e-comparative-report.md` atualizado com métricas finais
4. Prompt de handoff para próximo ciclo (ou encerramento)