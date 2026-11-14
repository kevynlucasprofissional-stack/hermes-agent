# Auditoria de qualidade — consolidação crítica dos relatórios de sessões Claude

**Data:** 23/10/2026  
**Repositório:** `C:\Github\hermes-agent`  
**Checkout consultado:** `main`, HEAD `e9fe6b38a0ba2d28907b182272dea04e2e1a6ce0` (fotografia do momento da auditoria).

## 1. Escopo e limites da evidência

Foram relidas qualitativamente as **31 sessões que receberam relatórios automáticos**, distinguindo ações comprovadas, resultados reportados, falhas de execução e decisões que permaneceram no planejamento. Os documentos individuais identificam as transcrições pelo UUID completo e remetem a linhas específicas do JSONL; o controle possui SHA-256 para permitir reconciliação.

A inspeção de qualidade executou leitura estática e consulta ao histórico Git de módulos críticos, além de testes unitários/contratuais. **Não foi executada uma bateria E2E autenticada de WhatsApp, Gmail ou o fluxo visual integral do Hermes Desktop.** Logo, não é correto inferir prontidão operacional apenas da presença do código ou de testes verdes.

Os 30 relatórios antigos permaneceram intocados; os 31 gerados inicialmente por extração automática foram substituídos por sínteses interpretativas. Cópias anteriores permanecem na pasta bruta ignorada pelo Git.

## 2. Evidências de testes executados nesta auditoria

| Procedimento | Resultado observado | Limite |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q tests/tools/test_whatsapp_browser_tools.py workstation/tests/test_whatsapp_browser_executor.py workstation/tests/test_email_provider.py` | **61 passed** em aproximadamente 6s | Contratos/unitários; não houve envio real nem medição de SLA |
| `.venv\Scripts\python.exe -m pytest -q workstation/tests/test_site_ops_e2e.py workstation/tests/test_browser_operational_admission.py` | **20 passed, 5 skipped, 1 warning** em aproximadamente 74s | Marcador `pytest.mark.e2e` não registrado; mensagem indicando ausência de CLI `agent-browser`. Os testes ignorados não comprovam E2E real. |

As saídas da execução foram preservadas temporariamente em `%TEMP%\auditoria_tres_suites_pytest.txt` e `%TEMP%\auditoria_siteops_admission_pytest.txt`.

## 3. Achados de maior prioridade

### P0 — O typecheck atual do Desktop falha em seis pontos

**Procedimento executado:** `npm run typecheck --workspace apps/desktop` com checkout `main`. **Resultado: FALHOU**, código de saída do npm 2. A compilação `tsc --noEmit` identificou:

| Arquivo | Local | Erro |
|---|---|---|
| `apps/desktop/electron/ipc/site-ops.ts` | linha 7 | `TS2552`: usa `dirname` sem importá-lo de `node:path` |
| `apps/desktop/electron/workstation-learning-session.ts` | linha 971 | `TS2304`: `result` não está definido no escopo |
| `apps/desktop/electron/fixtures/run-electron-learning-proof.ts` | linhas 50 e 98 | `TS2353`: opção `fps` não consta nas interfaces de configuração |
| Mesmo fixture | linhas 134 e 165 | `TS2339`: `framesCount` não existe em `LearningSessionState` |

**Efeito/qualidade:** o erro de `dirname` pode provocar falha de carregamento do IPC site-ops; a referência `result.pngBuffer` dentro do `try/catch` pode ocultar falha de persistência das capturas do modo Aprender. O fixture da prova Electron ficou dessincronizado das interfaces. Essas consequências são análises estáticas, não reprodução de runtime.

**Prioridade:** resolver a compilação sem desabilitar checagens e reexecutar `typecheck`; em seguida retestar site-ops e captura real do modo Aprender. Os testes Python aprovados não cobrem esses erros TypeScript.

### P1 — Estimador de tokens e guards do BrowserOS não comprovadamente integrados

- **Código presente:** `workstation/token_estimate.py`, `workstation/browser_guards.py`, `workstation/browser_error_messages.py`.
- **Evidência:** funções `estimate_tool_output_tokens`, `create_default_registry`, `classify_browser_error` existem no checkout e os arquivos estão no histórico Git.
- **Lacuna:** a busca de referências no checkout não encontrou consumidores externos a seus próprios módulos para `estimate_tool_output_tokens` ou `create_default_registry`. A existência de algoritmos e microbenchmarks isolados **não comprova execução no dispatcher**.
- **Critério de fechamento:** teste de integração que instrumente a chamada real, demonstre aplicação de guard/estimador antes do efeito e meça impacto de token/latência em tarefa comparável. Não tratar o ganho anunciado de 87% como economia já alcançada em produção.

### P1 — Ferramentas WhatsApp e mensageria: código real, E2E ainda pendente

- **Código presente:** `tools/browser_workstation.py` contém `whatsapp_wait_for_ready`, `whatsapp_send_message`, `whatsapp_search_contact` e `windows_app_launch`; `workstation/integrations/hermes/email_provider.py` contém providers Gmail, fallback e `EmailBatchSender`.
- **Resultado atual:** 61 testes do conjunto de módulos relevantes passaram.
- **Lacunas:** as métricas históricas de 4,46s (-19,8%) e 100% de taxa de envio eram de um cenário específico da sessão, não de escala real; não há prova contemporânea de envio autorizado end-to-end, nem da meta operacional de ≤1 mensagem/minuto.
- **Observação de integração:** o símbolo `wa_worker`, citado nos relatórios históricos, não foi localizado em `workstation/prefabs/integration.py` no HEAD atual. A arquitetura pode ter sido movida/reorganizada; confirmar o caminho do worker e seu registro antes de concluir quebra ou funcionamento.

### P1 — Aprender: binding de sessão corrigido, UX precisa de prova

- **Código presente:** referências `ownerTaskId`, `sessionHost` e `storedSessionId` em `apps/desktop/electron/workstation-browser-runtime.ts`.
- **Histórico:** o problema relatado era a emissão de perguntas sob ID sintético sem corresponder ao chat selecionado; houve alteração e testes de renderer/learning.
- **Lacuna:** nenhum teste manual completo nesta auditoria demonstrou uma nova pergunta aparecer no chat correto após ativar Aprender e iniciar TaskRun. Verificar também se o evento chega ao compiler/registro sem duplicação.

### P1 — Site Ops: integração presente, testes E2E reais ausentes

- **Código presente:** `agent/skill_utils.py` usa `TIER_BUNDLED`; há diretório `site-ops/`, módulo IPC `apps/desktop/electron/ipc/site-ops.ts` e testes.
- **Commits no histórico:** `9910ee097e`, `11c7c1ffac`, `3caf520c0e`.
- **Teste contemporâneo:** 20 passaram e 5 foram ignorados nas suítes de site-ops/admission.
- **Limitação de qualidade:** não é aceitável declarar auto-healing e migração de mapas como válidos em múltiplos sites enquanto faltarem execuções CDP/browser reais, testes de fallback e prova de segurança sobre persistência/rollback dos seletores.

### P1 — Coordenação multi-sessão incompleta fora dos hooks

- **Código presente:** `workstation/scripts/multi_agent_coordination.py`, `.claude/hooks`, `AGENTS.md`.
- **Conhecimento do histórico:** as instruções cooperativas em arquivo não impediam duas sessões de sobrescrever o mesmo caminho.
- **Risco residual:** hooks só cobrem ferramentas e ambientes que realmente os invocam; editores externos, scripts arbitrários e stale claims podem contornar/impedir trabalho. Verificar prova adversarial com duas sessões e expiração de claims.

### P2 — Startup corrigido, desempenho ainda precisa de baseline padronizado

- **Código presente:** `workstation/install.ps1`, `workstation/start.ps1`, script de cleanup e eventos de hidratação via `logLine` no `use-gateway-boot.ts`.
- **Commits relevantes:** `2f6ec41`, `bea3195`, `4024bd7`, `a6cead9`, `3be9208`.
- **Diagnóstico histórico:** Python backend ~60s cold e ~12s warm; Electron/Vite/renderer em geral mais rápidos.
- **Limite:** há evidência de melhoria de instrumentação e correções de abertura, mas não benchmark repetido no checkout atual com P50/P95 cold e sem processos residuais.

### P2 — Alguns relatórios antigos tinham atribuições equivocadas por semelhança temática

Uma sessão que solicitava consolidar Git foi interrompida por erro HTTP 524/classificador de Bash: **não fez merge/push**, mesmo havendo relatórios de outras consolidações. Outra sessão de investigação de backend observou o servidor saudável em `/api/health`, mas não entregou correção da corrida de attach. Os novos relatórios separam essas ações de implementações efetivas de outras sessões.

## 4. Critérios de qualidade utilizados

| Categoria | Significado |
|---|---|
| **VERIFICADO — código** | Arquivo, símbolo ou commit existe no checkout/Git consultado |
| **VERIFICADO — teste** | Comando executado com resultado que demonstra o comportamento abrangido pelo teste |
| **REPORTADO** | Conclusão apresentada pelo assistente da época, sem prova suficiente em código/teste |
| **PARCIAL** | Código presente, mas integração, E2E, desempenho ou aceitação incompletos |
| **PENDENTE** | Pedido não executado ou explicitamente interrompido |
| **INDETERMINADO** | Evidências insuficientes ou divergentes |

A avaliação de qualidade não confunde um teste `pytest` passando com sucesso de envio WhatsApp, nem TypeScript compilando com estabilidade de UI, nem ganho potencial de tokens com economia monetária medida.

## 5. Ordem de ações recomendada

1. Instrumentar e testar **uso efetivo dos guards e do estimador de tokens no dispatcher**; se não integrados, qualificá-los como protótipos e evitar percentuais de economia em relatórios operacionais.
2. Executar **um fluxo autorizado real de WhatsApp** com prova de entrega e retry não duplicante; checar também integração do executor atual.
3. Validar **Aprender → task real → pergunta no chat correto → persistência/compilação** com journal correlacionado.
4. Configurar um ambiente reprodutível para rodar os **5 E2E ignorados do Site Ops**, incluindo dependências de browser e sem alterar configurações de produção.
5. Testar enforcement multiagente com duas sessões concorrentes; medir depois cold/warm startup sob condições controladas.

**Conclusão:** o Hermes possui avanços reais e versionados nos componentes analisados. O principal déficit é a distância entre código escrito, testes unitários e comportamento operacional integrado. Os relatórios revisados descrevem essa distância, evitando transformar uma promessa de sessão em funcionalidade certificada.
