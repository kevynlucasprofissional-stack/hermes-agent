# Site Ops Implementation Plan — Session 3/3

**Date:** 2026-10-23
**Branch:** feat/hermes-workstation-startup-80-20
**Status:** Planning complete; ready for implementation prompts
**Prior:** [Session 2/3 Report](site-ops-architecture-evaluation-s2.md)

---

## Investigation Summary (3 Cycles Completed)

### Cycle 1: Current State Audit ✅
- All prototyped artifacts exist and are functional on this branch
- `get_skill_search_roots()` at `agent/skill_utils.py:392-403` still lacks TIER_BUNDLED
- `RESOURCE_ENV` at `scripts/build/inputs.py:10-16` has the documented structure
- `get_bundled_skills_dir()` exists at `hermes_constants.py:408-410` but is never called by skill discovery
- `apps/` confirmed in `INERT_SNAPSHOT_DIRS` at `scripts/bundles/payload.py:27-30`

### Cycle 2: Change Position Validation ✅
- TIER_BUNDLED insertion point: `agent/skill_utils.py:384` (extend range(4) → range(5)) and line ~401 (append bundled root after EXTERNAL)
- RESOURCE_ENV insertion point: `scripts/build/inputs.py:10-16` (add `"site-ops": "HERMES_SITE_OPS"`)
- No references to `assets/site-maps` or `assets/site-skills` in `apps/desktop/electron/` — migration won't break Desktop main process
- `agent/prompt_builder.py` consumes tier constants from skill_utils — must be checked for hardcoded tier count assumptions

### Cycle 3: Migration Impact Assessment ✅
- **8 references** to `assets/site-maps` and `assets/site-skills` in `SKILL.md` (relative paths in frontmatter and prose)
- **1 reference** in `whatsapp-web.mjs:27`: `resolve(__dirname, '../../assets/site-maps/whatsapp-web.json')` — relative path breaks on move
- **Multiple references** in `SKILL.md` to `apps/desktop/scripts/site-deep-map.mjs` and `apps/desktop/scripts/site-ops/whatsapp-web.mjs` — these are CLI invocation examples that need updating
- `site-deep-map.mjs` referenced via `execSync` in `whatsapp-web.mjs:90,93` — relative path needs update
- No IPC handlers exist yet for site-ops in Desktop electron layer

---

## Prompt de Implementação 1: Wiring TIER_BUNDLED

### Objetivo
Skills bundled no diretório `skills/` do agent-payload são descobertas automaticamente pelo prompt builder sem configuração manual, com precedência mais baixa que todos os tiers existentes.

### Contexto Validado
- `get_bundled_skills_dir()` já resolve o caminho correto via `HERMES_BUNDLED_SKILLS` env var (`hermes_constants.py:408-410`)
- `get_skill_search_roots()` constrói a lista de roots em ordem de precedência (`agent/skill_utils.py:392-403`)
- Apenas 4 tiers existem: PROJECT(0), LOCAL(1), CREATE_DIR(2), EXTERNAL(3) — BUNDLED deve ser 4 (lowest)
- `agent/prompt_builder.py` importa e usa esses tiers — verificar se há assumptions hardcoded sobre `range(4)`
- O build system já empacota `skills/` via `RESOURCE_ENV["skills"]` → `HERMES_BUNDLED_SKILLS` (`scripts/build/inputs.py:11`)

### Arquivos a Modificar
| Arquivo | Mudança | Linhas |
|---------|---------|--------|
| `agent/skill_utils.py` | Adicionar `TIER_BUNDLED = 4` ao range; inserir bundled root em `get_skill_search_roots()` | 384, ~401 |
| `agent/skill_utils.py` | Atualizar docstring de `get_all_skills_dirs()` para mencionar bundled | 406-409 |
| `agent/prompt_builder.py` | Verificar e corrigir qualquer assumption hardcoded sobre número de tiers | TBD |
| `tests/` | Teste unitário: skill em bundled dir aparece no catálogo com tier correto | Novo |

### Critérios de Aceite Testáveis
- [ ] `TIER_BUNDLED` constante existe com valor 4
- [ ] `get_skill_search_roots()` retorna `(TIER_BUNDLED, bundled_path)` quando `get_bundled_skills_dir().is_dir()` é True
- [ ] `get_skill_search_roots()` NÃO retorna bundled entry quando diretório não existe
- [ ] Precedência preservada: PROJECT > LOCAL > CREATE_DIR > EXTERNAL > BUNDLED (testar com skills de mesmo nome em tiers diferentes)
- [ ] Skill criada em `skills/test-bundled/SKILL.md` aparece no catálogo via `skill_view` ou slash command
- [ ] `get_all_skills_dirs()` inclui bundled dir na lista retornada
- [ ] Nenhum teste existente quebrado (`scripts/run_tests.sh`)
- [ ] `prompt_builder.py` funciona corretamente com 5 tiers

### Riscos e Mitigações
| Risco | Mitigação |
|-------|-----------|
| TIER_BUNDLED quebra precedência existente | Valor 4 garante lowest precedence; teste explícito de shadowing |
| `prompt_builder.py` tem loop hardcoded `range(4)` | Inspeção prévia + teste de integração |
| Bundled dir não existe em dev environment | Guard `if bundled.is_dir()` já previsto no design |
| Skills bundled poluem catálogo local | Documentar que bundled é fallback; user skills sempre vencem |

### Prompt de Continuação — Copiar em Nova Sessão

```markdown
# 📋 Prompt de Implementação 1: Wiring TIER_BUNDLED

## Objetivo
Adicionar TIER_BUNDLED ao sistema de descoberta de skills do Hermes para que skills empacotadas no agent-payload sejam automaticamente descobertas com precedência mais baixa.

## Contexto Validado
- Branch: `feat/hermes-workstation-startup-80-20`
- `get_bundled_skills_dir()` existe em `hermes_constants.py:408-410` mas NUNCA é chamada por `get_skill_search_roots()`
- 4 tiers atuais: PROJECT(0), LOCAL(1), CREATE_DIR(2), EXTERNAL(3) em `agent/skill_utils.py:384`
- `get_skill_search_roots()` em `agent/skill_utils.py:392-403` constrói lista ordenada
- Build system já empacota `skills/` via `RESOURCE_ENV["skills"]` (`scripts/build/inputs.py:11`)
- `agent/prompt_builder.py` consome tiers — verificar assumptions hardcoded

## Fases de Investigação (Mínimo 3 Ciclos)

### Ciclo 1: Auditoria do Código Atual
- Leia `agent/skill_utils.py` linhas 380-410 integralmente
- Leia `agent/prompt_builder.py` e busque qualquer referência a `TIER_`, `range(4)`, ou número hardcoded de tiers
- Leia `hermes_constants.py` linhas 405-415 para confirmar assinatura de `get_bundled_skills_dir()`
- Verifique testes existentes em `tests/` que cobrem `get_skill_search_roots()` ou skill discovery

### Ciclo 2: Validação do Design
- Confirme que adicionar `TIER_BUNDLED = 4` e append após EXTERNAL preserva precedência
- Verifique se `get_all_skills_dirs()` precisa de atualização (docstring + lógica)
- Avalie se algum outro arquivo importa `TIER_*` constantes diretamente (grep por `from.*skill_utils.*import.*TIER`)
- Planeje teste unitário: criar skill temporária em bundled dir, verificar aparição no catálogo

### Ciclo 3: Definição de Escopo Mínimo
- Liste exatamente quais linhas mudar em cada arquivo
- Defina teste mínimo que prova funcionamento sem over-engineering
- Identifique rollback plan se algo quebrar

## Fases de Implementação (Mínimo 3 Ciclos)

### Ciclo 1: Implementação Cirúrgica
- Adicione `TIER_BUNDLED` ao range em `skill_utils.py:384`
- Insira bundled root em `get_skill_search_roots()` após EXTERNAL (linha ~401)
- Atualize docstrings afetadas
- Corrija `prompt_builder.py` se necessário

### Ciclo 2: Testes e Validação
- Execute `scripts/run_tests.sh` para confirmar zero regressões
- Crie skill teste em bundled dir e verifique descoberta
- Teste precedência: skill com mesmo nome em LOCAL e BUNDLED → LOCAL vence
- Valide `get_all_skills_dirs()` retorna bundled

### Ciclo 3: Auditoria Adversarial
- Revise diff completo para mudanças não planejadas
- Verifique se comentário de precedência em linha 381-383 foi atualizado
- Confirme que guard `if bundled.is_dir()` previne erro quando dir ausente
- Documente mudança em commit message claro

## Instruções Operacionais
1. Execute os 3 ciclos de investigação ANTES de editar
2. Use `scripts/run_tests.sh` NUNCA bare pytest
3. Respeite protocolo multi-agente: verifique claims antes de editar
4. Commit atomicamente com mensagem descritiva
5. Gere prompt de continuação para Implementação 2 ao final

## Entregáveis
- [ ] TIER_BUNDLED funcional e testado
- [ ] Zero regressões em testes existentes
- [ ] Commit limpo com Co-Authored-By
- [ ] Prompt de continuação para Prompt 2 gerado
```

---

## Prompt de Implementação 2: Framework Genérico + Migração site-ops/

### Objetivo
Criar diretório `site-ops/` na raiz do repositório com framework reutilizável, migrar artefatos prototipados de `apps/desktop/assets/` e `apps/desktop/scripts/`, e adicionar `HERMES_SITE_OPS` ao build system para portabilidade CLI/gateway.

### Contexto Validado
- Artefatos atuais vivem em `apps/desktop/assets/site-maps/`, `apps/desktop/assets/site-skills/`, `apps/desktop/scripts/site-ops/`, `apps/desktop/scripts/site-deep-map.mjs`
- `apps/` está em `INERT_SNAPSHOT_DIRS` (`payload.py:27-30`) — NÃO vai para agent-payload
- Mover para `site-ops/` na raiz permite inclusão no snapshot via novo `RESOURCE_ENV["site-ops"]`
- **8 referências** em `SKILL.md` usam caminhos relativos `assets/site-maps/` e `assets/site-skills/`
- **1 referência** em `whatsapp-web.mjs:27` usa `resolve(__dirname, '../../assets/site-maps/whatsapp-web.json')`
- **2 referências** em `whatsapp-web.mjs:90,93` usam `execSync` com caminho relativo para `site-deep-map.mjs`
- Nenhuma referência a esses assets no electron main process (`apps/desktop/electron/`) — migração segura

### Estrutura Alvo
```
site-ops/
├── framework/
│   ├── cdp-client.mjs        # CDP connection + eval wrapper reutilizável
│   ├── auto-heal.mjs          # Lógica genérica de healing (extraída de whatsapp-web.mjs)
│   ├── map-loader.mjs         # Resolução baseline + local override
│   └── selector-resolver.mjs  # Lookup prioritário de seletores no mapa
├── maps/
│   └── whatsapp-web.json      # Baseline migrado de apps/desktop/assets/site-maps/
├── skills/
│   └── whatsapp-web-ops/
│       └── SKILL.md           # Playbook migrado de apps/desktop/assets/site-skills/
└── scripts/
    ├── site-deep-map.mjs      # Migrado de apps/desktop/scripts/
    └── site-ops/
        └── whatsapp-web.mjs   # Migrado e atualizado para usar framework imports
```

### Arquivos a Modificar/Criar
| Arquivo | Ação | Notas |
|---------|------|-------|
| `scripts/build/inputs.py` | Adicionar `"site-ops": "HERMES_SITE_OPS"` ao RESOURCE_ENV | Linha ~16 |
| `site-ops/framework/cdp-client.mjs` | Criar | Extrair de whatsapp-web.mjs + site-deep-map.mjs |
| `site-ops/framework/auto-heal.mjs` | Criar | Extrair lógica de healing de whatsapp-web.mjs |
| `site-ops/framework/map-loader.mjs` | Criar | Resolver baseline vs local override |
| `site-ops/framework/selector-resolver.mjs` | Criar | Priority-based selector lookup |
| `site-ops/maps/whatsapp-web.json` | Mover | De `apps/desktop/assets/site-maps/` |
| `site-ops/skills/whatsapp-web-ops/SKILL.md` | Mover + atualizar | De `apps/desktop/assets/site-skills/`; atualizar 8 refs de caminho |
| `site-ops/scripts/site-deep-map.mjs` | Mover + refatorar | De `apps/desktop/scripts/`; usar framework imports |
| `site-ops/scripts/site-ops/whatsapp-web.mjs` | Mover + refatorar | De `apps/desktop/scripts/site-ops/`; atualizar linha 27, 90, 93 |
| `apps/desktop/assets/site-maps/` | Remover (após migração) | Verificar se algo mais referencia |
| `apps/desktop/assets/site-skills/` | Remover (após migração) | Verificar se algo mais referencia |
| `apps/desktop/scripts/site-deep-map.mjs` | Remover (após migração) | Verificar se algo mais referencia |
| `apps/desktop/scripts/site-ops/` | Remover (após migração) | Verificar se algo mais referencia |

### Critérios de Aceite Testáveis
- [ ] `RESOURCE_ENV` contém `"site-ops": "HERMES_SITE_OPS"`
- [ ] `site-ops/framework/` contém 4 módulos reutilizáveis
- [ ] `whatsapp-web.mjs` importa de `../framework/` ao invés de reimplementar CDP/healing
- [ ] `site-deep-map.mjs` importa de `../framework/` para CDP client
- [ ] `SKILL.md` atualizado: todos os caminhos apontam para `site-ops/` nova estrutura
- [ ] `node site-ops/scripts/site-ops/whatsapp-web.mjs get-unread-count` funciona (requer CDP ativo)
- [ ] `node site-ops/scripts/site-deep-map.mjs status` funciona
- [ ] Agent-payload snapshot inclui `site-ops/` (verificar via `HERMES_SITE_OPS` env var)
- [ ] Referências antigas em `apps/desktop/` removidas ou redirecionadas
- [ ] Nenhum link quebrado no repositório (grep por caminhos antigos retorna zero)

### Riscos e Mitigações
| Risco | Mitigação |
|-------|-----------|
| Caminhos relativos quebram após migração | Atualizar TODAS as referências no mesmo commit; grep pós-migração |
| Framework extraction introduz bugs | Testar cada operação individualmente após refatoração |
| `HERMES_SITE_OPS` não resolvido em runtime | Adicionar `get_site_ops_dir()` em `hermes_constants.py` seguindo padrão existente |
| Desktop ASAR ainda referencia paths antigos | Verificar `electron-builder.config.cjs` para includes/excludes |
| Fork inheritance quebrada | `site-ops/` na raiz é versionado; forks herdam via merge/rebase |

### Prompt de Continuação — Copiar em Nova Sessão

```markdown
# 📋 Prompt de Implementação 2: Framework Genérico + Migração site-ops/

## Objetivo
Criar framework reutilizável em `site-ops/` na raiz, migrar artefatos de `apps/desktop/`, e adicionar ao build system para portabilidade CLI/gateway.

## Contexto Validado
- Branch: `feat/hermes-workstation-startup-80-20`
- Pré-requisito: Prompt 1 (TIER_BUNDLED) deve estar implementado e testado
- Artefatos atuais: `apps/desktop/assets/site-maps/`, `apps/desktop/assets/site-skills/`, `apps/desktop/scripts/site-ops/`, `apps/desktop/scripts/site-deep-map.mjs`
- `apps/` em `INERT_SNAPSHOT_DIRS` (`payload.py:27-30`) — não vai para agent-payload
- 8 refs em SKILL.md + 3 refs em whatsapp-web.mjs usam caminhos relativos que quebrarão na migração
- Nenhuma ref em `apps/desktop/electron/` — migração segura para main process
- `RESOURCE_ENV` em `scripts/build/inputs.py:10-16` aceita nova entrada

## Estrutura Alvo
```
site-ops/
├── framework/          # 4 módulos: cdp-client, auto-heal, map-loader, selector-resolver
├── maps/               # whatsapp-web.json (baseline)
├── skills/             # whatsapp-web-ops/SKILL.md
└── scripts/            # site-deep-map.mjs + site-ops/whatsapp-web.mjs
```

## Fases de Investigação (Mínimo 3 Ciclos)

### Ciclo 1: Extração do Framework
- Leia `whatsapp-web.mjs` integralmente; identifique blocos extraíveis (CDP connect, healing, map load, selector resolve)
- Leia `site-deep-map.mjs` integralmente; identifique CDP client reutilizável
- Defina API surface de cada módulo framework (exports, params, return types)
- Verifique dependências Node.js externas (chrome-remote-interface? ws? fetch?)

### Ciclo 2: Migração e Atualização de Referências
- Liste todas as referências a `apps/desktop/assets/site-maps`, `apps/desktop/assets/site-skills`, `apps/desktop/scripts/site-deep-map.mjs`, `apps/desktop/scripts/site-ops/` em todo o repositório
- Planeje atualização atômica: mover arquivos + atualizar refs no mesmo commit
- Verifique se `electron-builder.config.cjs` inclui/exclui explicitamente esses paths
- Adicione `get_site_ops_dir()` em `hermes_constants.py` seguindo padrão de `get_bundled_skills_dir()`

### Ciclo 3: Validação de Portabilidade
- Confirme que `RESOURCE_ENV["site-ops"]` fará snapshot incluir `site-ops/`
- Verifique se `INERT_SNAPSHOT_DIRS` precisa de ajuste (não deve, pois `site-ops/` é raiz)
- Teste que scripts funcionam tanto via caminho absoluto quanto via `HERMES_SITE_OPS` env var
- Documente como CLI/gateway acessa site-ops sem Desktop

## Fases de Implementação (Mínimo 3 Ciclos)

### Ciclo 1: Criar Framework + Mover Arquivos
- Crie `site-ops/framework/` com 4 módulos
- Mova maps, skills, scripts para nova estrutura
- Atualize imports em whatsapp-web.mjs e site-deep-map.mjs
- Adicione `"site-ops": "HERMES_SITE_OPS"` ao RESOURCE_ENV
- Adicione `get_site_ops_dir()` em hermes_constants.py

### Ciclo 2: Atualizar Referências + Limpeza
- Atualize SKILL.md com novos caminhos
- Remova diretórios antigos em `apps/desktop/`
- Grep por referências órfãs e corrija
- Execute scripts migrados para confirmar funcionalidade

### Ciclo 3: Auditoria e Testes
- Verifique agent-payload inclui site-ops/
- Teste `node site-ops/scripts/site-ops/whatsapp-web.mjs get-unread-count`
- Teste `node site-ops/scripts/site-deep-map.mjs status`
- Confirme zero links quebrados
- Commit com mensagem descritiva

## Instruções Operacionais
1. Pré-requisito: Prompt 1 (TIER_BUNDLED) implementado e testado
2. Use `scripts/run_tests.sh` NUNCA bare pytest
3. Respeite protocolo multi-agente: verifique claims antes de editar
4. Migração deve ser atômica: mover + atualizar refs no mesmo commit
5. Gere prompt de continuação para Prompt 3 ao final

## Entregáveis
- [ ] `site-ops/` na raiz com framework reutilizável
- [ ] Artefatos migrados e funcionais
- [ ] Build system inclui site-ops no agent-payload
- [ ] Zero referências quebradas
- [ ] Commit limpo com Co-Authored-By
- [ ] Prompt de continuação para Prompt 3 gerado
```

---

## Prompt de Implementação 3: Desktop Integration + Testes E2E

### Objetivo
Integrar site-ops ao Desktop via IPC para que o renderer invoque operações sem spawn shell direto, e validar fluxo completo ponta a ponta com auto-healing.

### Contexto Validado
- Branch: `feat/hermes-workstation-startup-80-20`
- Pré-requisitos: Prompt 1 (TIER_BUNDLED) e Prompt 2 (Framework + Migração) implementados
- `site-ops/` na raiz com framework funcional
- Nenhum IPC handler para site-ops existe atualmente em `apps/desktop/electron/`
- AI Control Guide (`apps/desktop/docs/AI-CONTROL-GUIDE.md`) documenta CDP via eval.mjs
- Segurança: apenas contatos "Kevyn ACIRV" e "+55 64 9247-0988 (Você)" para testes WhatsApp

### Arquivos a Modificar/Criar
| Arquivo | Ação | Notas |
|---------|------|-------|
| `apps/desktop/electron/ipc/site-ops.ts` | Criar | Handler `site-ops:execute` |
| `apps/desktop/electron/main.ts` (ou equivalente) | Modificar | Registrar IPC handler |
| `apps/desktop/src/renderer/` | Modificar | Wrapper IPC ao invés de spawn |
| `apps/desktop/src/preload.ts` (ou equivalente) | Modificar | Expor API via contextBridge |
| `workstation/tests/test_site_ops_e2e.py` | Criar | Testes E2E com pytest |
| `apps/desktop/docs/SITE-OPS-GUIDE.md` | Criar | Documentação de uso |

### Critérios de Aceite Testáveis
- [ ] IPC handler `site-ops:execute` registrado e responde a chamadas do renderer
- [ ] Renderer usa IPC ao invés de `child_process.spawn` ou similar
- [ ] Auto-healing funciona end-to-end: simular falha de seletor → re-map automático → retry bem-sucedido
- [ ] Teste E2E: abrir chat "Kevyn ACIRV" via site-ops → enviar mensagem teste → confirmar entrega
- [ ] Teste E2E: `get-unread-count` retorna valor consistente entre chamadas
- [ ] Cooldown de 30s entre heals respeitado
- [ ] Max 1 retry por operação respeitado
- [ ] Documentação SITE-OPS-GUIDE.md completa com exemplos
- [ ] Zero regressões em testes existentes (`scripts/run_tests.sh`)

### Riscos e Mitigações
| Risco | Mitigação |
|-------|-----------|
| IPC timeout em operações longas | Timeout configurável + feedback progressivo ao renderer |
| Auto-heal loop infinito | Guards já especificados na Sessão 2 (max 1 retry, cooldown 30s, escalation após 3/session) |
| CDP não disponível em runtime | Graceful degradation: detectar CDP, fallback para browser tool ou user guidance |
| Teste E2E flaky (timing WhatsApp) | Retry logic + wait-for-element explícito + skip em CI sem CDP |
| Security: execução arbitrária via IPC | Whitelist de operações permitidas; validação de argumentos |

### Prompt de Continuação — Copiar em Nova Sessão

```markdown
# 📋 Prompt de Implementação 3: Desktop Integration + Testes E2E

## Objetivo
Integrar site-ops ao Desktop via IPC e validar fluxo completo com auto-healing.

## Contexto Validado
- Branch: `feat/hermes-workstation-startup-80-20`
- Pré-requisitos: Prompt 1 (TIER_BUNDLED) e Prompt 2 (Framework + Migração) completos
- `site-ops/` na raiz funcional com framework
- Nenhum IPC handler existe em `apps/desktop/electron/`
- AI Control Guide documenta CDP via eval.mjs
- Segurança: apenas "Kevyn ACIRV" e "+55 64 9247-0988 (Você)" para testes WhatsApp

## Fases de Investigação (Mínimo 3 Ciclos)

### Ciclo 1: Arquitetura IPC
- Leia `apps/desktop/electron/` para entender padrão IPC existente
- Leia `apps/desktop/docs/AI-CONTROL-GUIDE.md` para CDP patterns
- Identifique onde registrar handler (main.ts, ipc/index.ts, etc.)
- Defina schema de request/response para `site-ops:execute`

### Ciclo 2: Integração Renderer
- Leia renderer atual para encontrar onde site-ops seria invocado
- Planeje wrapper IPC substituindo qualquer spawn direto
- Verifique preload/contextBridge exposure pattern
- Defina error handling e timeout strategy

### Ciclo 3: Estratégia de Testes E2E
- Leia `workstation/tests/` para padrões existentes
- Defina fixtures necessárias (CDP ativo, WhatsApp logado)
- Planeje teste de auto-healing: como simular falha de seletor?
- Defina critérios de skip para ambientes sem CDP

## Fases de Implementação (Mínimo 3 Ciclos)

### Ciclo 1: IPC Handler + Preload
- Crie handler `site-ops:execute` seguindo padrões existentes
- Exponha via contextBridge no preload
- Adicione whitelist de operações permitidas
- Teste unitário do handler isoladamente

### Ciclo 2: Renderer Integration + Auto-Healing
- Substitua spawn por IPC calls no renderer
- Integre auto-heal flow: catch error → trigger re-map → retry
- Implemente cooldown e max-retry guards
- Logging estruturado para debugging

### Ciclo 3: Testes E2E + Documentação
- Crie `test_site_ops_e2e.py` com casos de teste definidos
- Execute testes contra WhatsApp Web real (contatos autorizados apenas)
- Crie `SITE-OPS-GUIDE.md` com exemplos e troubleshooting
- Auditoria final: zero regressões, docs completas

## Instruções Operacionais
1. Pré-requisitos: Prompts 1 e 2 completos
2. Siga AI Control Guide para CDP interactions
3. Segurança: APENAS contatos autorizados para testes
4. Use `scripts/run_tests.sh` NUNCA bare pytest
5. Respeite protocolo multi-agente: verifique claims antes de editar
6. Gere prompt de auditoria final ao concluir

## Entregáveis
- [ ] IPC handler funcional e seguro
- [ ] Renderer integrado via IPC
- [ ] Auto-healing validado end-to-end
- [ ] Testes E2E passando
- [ ] Documentação completa
- [ ] Zero regressões
- [ ] Commit limpo com Co-Authored-By
- [ ] Prompt de auditoria final gerado
```

---

## Resumo Executivo da Sessão 3/3

Os 3 ciclos de investigação confirmaram que todas as evidências da Sessão 2 permanecem válidas na branch `feat/hermes-workstation-startup-80-20`:

1. **Artefatos prototipados existem e são funcionais** — site-deep-map.mjs, whatsapp-web.mjs, whatsapp-web.json, SKILL.md
2. **Gap de wiring confirmado** — `get_bundled_skills_dir()` nunca chamada por `get_skill_search_roots()`
3. **Impacto de migração mapeado** — 8 refs em SKILL.md + 3 refs em whatsapp-web.mjs precisam atualização atômica
4. **Nenhuma referência no electron main process** — migração segura para Desktop

O plano produz 3 prompts de implementação sequenciais e auto-suficientes:
- **Prompt 1:** Wiring TIER_BUNDLED (mudança cirúrgica em skill_utils.py)
- **Prompt 2:** Framework genérico + migração site-ops/ (reestruturação + build system)
- **Prompt 3:** Desktop IPC + testes E2E (integração + validação ponta a ponta)

Cada prompt contém critérios de aceite testáveis, lista de arquivos, riscos/mitigações e seu próprio prompt de continuação. O documento está salvo em `workstation/dogfood/artifacts/site-ops-implementation-plan-s3.md`.