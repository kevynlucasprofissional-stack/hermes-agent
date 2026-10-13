# HWH-001 — quadro compartilhado (snapshot)
Atualizado: 2026-10-13. **Este arquivo é um snapshot durável, não um lock.** Estado vivo: `python workstation/scripts/multi_agent_coordination.py status`. Só o integrador escreve este quadro.

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
| Native E2E A/B/C | NOT_RUN nesta frente | D |

O CreativeWorkspaceProvider aparece em `CreativeWorkspacePage.tsx` no HEAD inspecionado; **não** reimplementar só por ser pendência histórica do PR #77. Os PRs anteriores já foram consolidados; `STATE.md` antigo contém identidades históricas e não deve ordenar retomada de worktree inexistente.

## Próxima integração
- Etapa 1 / Prompt 1: fechar HWH-01 e HWH-02 como **um incremento vertical** (Agent→Hub→Creative) — CONCLUÍDO E INTEGRADO.
- Etapa 2 / Prompt 2: HWH-03 Browser manual→sessão existente→Chat com a mesma WebContentsView e lease humano — CONCLUÍDO E INTEGRADO.
- Etapa 3 / Prompt 3: execução E2E real, hardening direcionado, CI, PR final.
- Se etapas anteriores já estiverem aprovadas no HEAD, avançar imediatamente sem reexecutar pesquisa ampla.
- Em qualquer suspensão, publicar o próximo prompt integral, factual e recursivo.
