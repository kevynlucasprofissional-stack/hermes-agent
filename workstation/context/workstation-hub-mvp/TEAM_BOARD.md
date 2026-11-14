# HWH-001 — quadro de coordenação
Atualizado: 2026-10-25. **Este arquivo é um snapshot durável, não um lock.** Estado vivo: `python workstation/scripts/multi_agent_coordination.py status`.

## Política vigente

- O ciclo compartilhado aberto em 2026-10-13 foi encerrado. `main` é a branch canônica para o trabalho atual; `feat/hermes-workstation-mvp-20261013` e as atribuições abaixo são históricas, não uma ordem ativa de checkout ou ownership.
- Branch futura só vale quando for explicitamente definida pela tarefa atual ou por maintainer. `COLLABORATION_BRANCH` é override opcional do hook para esse ciclo explicitamente autorizado; não autoriza por si só uma troca de branch. Nunca recomende `git switch` baseado apenas em documentos históricos.
- Antes de editar, consultar claims reais com `python workstation/scripts/multi_agent_coordination.py status` e obter claim exclusiva dos paths. Claims locais são cooperativas, não locks distribuídos. Preservar todo trabalho dirty/untracked e parar diante de conflito.
- Integrador, quando necessário, é designado explicitamente por tarefa. Só esse integrador realiza staging, commits, push/pull/merge/rebase/switch e atualização canônica do quadro; não assumir a identidade histórica `agent-integrator`.
- O checkout verificado nesta atualização estava em `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, um commit atrás de `origin/main@bafa3c43f4ecf7953e377e29cca6515089e530fe`, com trabalho local dirty. Nenhum fast-forward ou troca de branch foi feito.

## Snapshot histórico — ciclo de 2026-10-13 (encerrado)

O conteúdo abaixo registra o planejamento e o estado declarado naquele checkpoint. Não concede claims atuais nem prova o estado do HEAD de hoje.

## Ciclo de integração
- Repositório: `kevynlucasprofissional-stack/hermes-agent`
- Única branch: `feat/hermes-workstation-mvp-20261013`.
- Único checkout: `C:\Github\hermes-agent`.
- Base inicial observada: `b80d10a4d6d4536b65df52eb4e011ad8d5eef672`.
- Integrador: `agent-integrator` (designação operacional, não identidade autenticada).
- PR agregado: ainda não aberto neste checkpoint; atualizar após push/abertura.
- Política: `workstation/context/AGENT_COLLABORATION_PROTOCOL.md`.

## Áreas de atuação — nenhuma concedida automaticamente
| Agente | Lane | Objetivo | Dono dos arquivos | Estado inicial | Pode contribuir | Não pode |
|---|---|---|---|---|---|---|
| A | creative-agent | Capability do Agent para abrir Creative | Registrar claim exato | AVAILABLE | Ferramenta, intent, testes | Reescrever Browser runtime, editar arquivo de B/C |
| B | hub-ui | Workstation sidebar + aba React Creative | Registrar claim exato | AVAILABLE | UI e occlusion | Criar Browser ou session stores paralelos |
| C | session-handoff | Adoção de tab existente em sessão canônica | Registrar claim exato | AVAILABLE | Electron/BrowserTask/Gateway/human lease | Ignorar authority, recarregar WebContentsView |
| D | integration-qa | Integrar, CI, provas nativas, documentação | Registrar claim exato | AVAILABLE | Testes transversais, commits e PR | Alterar arquivo reclamado por A/B/C sem transferir owner |

**Todos usam a mesma branch**, mas claims dos arquivos são exclusivos. A atribuição só começa quando o registro local confirmar `claim`. O integrador faz as operações Git e publica HEADs.

## Estado funcional da missão
| Critério | Verificação em 2026-10-13 | Próximo dono |
|---|---|---|
| HWH-01 Agent → Creative | VERIFIED (open_creative_workstation, desktop_ui bridge, 4/4 pytests PASS) | A/D |
| HWH-02 Browser → Workstation | VERIFIED (sidebar 'Workstation', internal Creative tab, 3/3 tab vitests PASS, route test PASS, code health 0 blocking) | B/D |
| HWH-03 Levar para sessão | VERIFIED (adoção de tab manual na sessão Gateway, preservação da WebContentsView sem loadURL, lease humano e 409 USER_CONTROL_ACTIVE, 36/36 electron tests PASS, 3/3 UI adoption vitests PASS, code health 0 blocking) | C/D |
| Native E2E A/B/C | VERIFIED (9/9 Playwright E2E tests PASS no Electron real: alinhamento de 4 tarefas nativas, execução concorrente de tarefas e chat, restauração de viewport sem foreground theft, recusa 409 em takeover humano, clique real em Take/Release Control, mutação persistente após ack perdido, handoff canônico incerto sem replay, cold restart de Electron com recuperação de lease, e jornada completa HWH-MVP de abertura de aba Creative, alternância de abas e adoção de tab em sessão Gateway com preservação de lease) | D |

O CreativeWorkspaceProvider aparece em `CreativeWorkspacePage.tsx` no HEAD inspecionado; **não** reimplementar só por ser pendência histórica do PR #77. Os PRs anteriores já foram consolidados; `STATE.md` antigo contém identidades históricas e não deve ordenar retomada de worktree inexistente.

## Histórico de próxima integração — checkpoint de 2026-10-13
- Etapa 1 / Prompt 1: fechar HWH-01 e HWH-02 como **um incremento vertical** (Agent→Hub→Creative) — CONCLUÍDO E INTEGRADO.
- Etapa 2 / Prompt 2: HWH-03 Browser manual→sessão existente→Chat com a mesma WebContentsView e lease humano — CONCLUÍDO E INTEGRADO.
- Etapa 3 / Prompt 3: execução E2E real, hardening direcionado, CI, PR final — CONCLUÍDO E INTEGRADO.
- Se etapas anteriores já estiverem aprovadas no HEAD, avançar imediatamente sem reexecutar pesquisa ampla.
- Em qualquer suspensão, publicar o próximo prompt integral, factual e recursivo.
