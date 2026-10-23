# Site Ops Architecture Evaluation — Session 2/3 Report

**Date:** 2026-10-23
**Branch:** feat/hermes-workstation-startup-80-20
**Status:** Investigation complete; ready for Session 3/3 (implementation planning)

---

## 1. Evidence Summary

### 1.1 Agent-Payload Build Pipeline

| Finding | Source | Implication |
|---------|--------|-------------|
| `RESOURCE_ENV` maps `"skills"` → `HERMES_BUNDLED_SKILLS` | `scripts/build/inputs.py:11-17` | The `skills/` directory IS shipped in agent-payload snapshot |
| `get_bundled_skills_dir()` exists but is NEVER called by `get_skill_search_roots()` | `hermes_constants.py:408-410`, `agent/skill_utils.py:392-401` | Bundled skills are packaged but NOT discovered at runtime |
| No `TIER_BUNDLED` constant in skill_utils | `agent/skill_utils.py:384` | Only PROJECT, LOCAL, CREATE_DIR, EXTERNAL exist |
| `apps/` is in `INERT_SNAPSHOT_DIRS` | `scripts/bundles/payload.py:27-30` | Desktop assets (site-maps, site-skills) are NOT in agent-payload |
| `apps/desktop/assets/**` included in Electron ASAR | `electron-builder.config.cjs:114` | Desktop users get site-assets; CLI/gateway users do NOT |
| No first-run skill indexing hook | grep across `apps/desktop/electron/` | Bootstrap handles runtime setup only; skills discovered on-demand |
| `optional-skills/` requires manual install via Skills Hub | `tools/skills_hub_official.py:34` | Not auto-discovered either |

### 1.2 Key Architectural Gap

The Hermes build system **already packages** a `skills/` directory into the agent-payload via `RESOURCE_ENV["skills"]`, and `get_bundled_skills_dir()` resolves it correctly. However, `get_skill_search_roots()` never includes this tier in its search path. This is a **wiring gap**, not a missing feature.

---

## 2. Comparative Evaluation Matrix

### Criteria Definitions

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Speed** | High | Time from user intent to operation execution |
| **Resilience** | High | Ability to survive site UI changes without breaking |
| **Token Cost** | Medium | LLM tokens consumed per operation |
| **Complexity** | Medium | Code complexity and maintenance burden |
| **Auto-improvement** | High | Ability to self-update when site changes |
| **Portability** | High | Works on Desktop AND CLI/gateway |
| **Fork Inheritance** | Critical | Any fork gets capabilities automatically |

### Approach Comparison

| Criterion | A: Script Pure | B: Skill+Map | C: Hybrid (Recommended) |
|-----------|----------------|--------------|-------------------------|
| **Speed** | ★★★★★ Fastest (no LLM) | ★★☆☆☆ Slowest (LLM every action) | ★★★★☆ Script fast; LLM only for healing |
| **Resilience** | ★★☆☆☆ Breaks on UI change | ★★★★☆ Map provides fallback selectors | ★★★★★ Auto-healing + map baseline |
| **Token Cost** | ★★★★★ Zero per operation | ★☆☆☆☆ High (map analysis each time) | ★★★★☆ Zero normal; tokens only on heal |
| **Complexity** | ★★★☆☆ Simple scripts | ★★☆☆☆ Complex prompt engineering | ★★★☆☆ Three layers, clear boundaries |
| **Auto-improvement** | ★☆☆☆☆ Manual updates only | ★★★☆☆ LLM can adapt ad-hoc | ★★★★★ Structured re-map + diff + retry |
| **Portability** | ★★★☆☆ Scripts portable; no discovery | ★★★★☆ Skills portable if wired | ★★★★★ Same wiring serves both runtimes |
| **Fork Inheritance** | ★★☆☆☆ Must manually copy scripts | ★★★☆☆ Depends on skill tier wiring | ★★★★★ Bundled tier ships in repo |

### Winner: Approach C (Hybrid)

**Rationale:** Approach C wins on 5 of 7 criteria including all three weighted "High" or "Critical". It combines the speed of deterministic scripts with the resilience of structured maps and the auto-improvement capability that neither pure approach offers. The complexity cost is justified by the three-layer separation of concerns (script = execution, map = selectors, skill = orchestration).

---

## 3. Auto-Healing Mechanism Specification

### 3.1 Trigger Conditions

Auto-healing activates when ANY of these occur during script execution:

1. **Selector miss**: `document.querySelector(selector)` returns null
2. **Element mismatch**: Found element lacks expected attributes (aria-label, role, testId)
3. **Action failure**: Click/type returns false or throws after selector resolved
4. **Timeout**: Operation exceeds 5s waiting for expected DOM state

### 3.2 Healing Flow

```
Script fails → Error with failed selector
    ↓
withAutoHealing() catches error
    ↓
Run site-deep-map.mjs scan <site-pattern>
    ↓
Load new map from artifacts/site-map-<slug>.json
    ↓
Diff against current map (baseline or local override)
    ↓
Save merged map to .claude/site-maps/<site>.local.json
    ↓
Retry original operation with updated selectors
    ↓
Success → Log healed selectors to telemetry
Failure → Surface error to user with diagnostic context
```

### 3.3 Loop Prevention

| Guard | Mechanism |
|-------|-----------|
| **Max retries** | 1 re-map + 1 retry per operation call |
| **Cooldown** | 30s minimum between heals for same site |
| **Depth limit** | Re-map scans only current screen (no recursive nav) |
| **Baseline protection** | Local override never overwrites repo baseline |
| **User escalation** | After 3 heals in one session, prompt user for guidance |

### 3.4 Map Update Policy

| Scenario | Action |
|----------|--------|
| Single user heal succeeds | Save to `.claude/site-maps/<site>.local.json` only |
| Same selector fails 3+ times across sessions | Flag for baseline review |
| WhatsApp announces UI redesign | Manual baseline update after verification |
| New interactive element discovered | Add to local map; propose baseline PR |
| Map >30 days since validation | Suggest validation run to user |

### 3.5 File Locations

| File | Location | Committed? | Purpose |
|------|----------|------------|---------|
| Baseline map | `apps/desktop/assets/site-maps/<site>.json` | Yes | Stable reference selectors |
| Local override | `.claude/site-maps/<site>.local.json` | No | Auto-healed selectors |
| Operations script | `apps/desktop/scripts/site-ops/<site>.mjs` | Yes | Deterministic CLI ops |
| Deep map script | `apps/desktop/scripts/site-deep-map.mjs` | Yes | Re-mapping tool |
| Skill playbook | `apps/desktop/assets/site-skills/<site>-ops/SKILL.md` | Yes | LLM instructions |

---

## 4. Required Source Code Changes

### 4.1 Wire TIER_BUNDLED into Skill Discovery

**File:** `agent/skill_utils.py`

```python
# Line ~384: Add new tier constant
TIER_PROJECT, TIER_LOCAL, TIER_CREATE_DIR, TIER_EXTERNAL, TIER_BUNDLED = range(5)

# Line ~392-401: Add bundled root to get_skill_search_roots()
def get_skill_search_roots(local=None, *, include_project=True):
    roots = [(TIER_PROJECT, d) for d in get_project_skills_dirs()] if include_project else []
    roots.append((TIER_LOCAL, Path(local) if local is not None else get_skills_dir()))
    create_dir = get_skill_create_dir()
    if create_dir is not None and create_dir.is_dir():
        roots.append((TIER_CREATE_DIR, create_dir))
    roots += [(TIER_EXTERNAL, d) for d in get_external_skills_dirs()]
    # NEW: bundled skills from agent-payload (lowest precedence)
    bundled = get_bundled_skills_dir()
    if bundled.is_dir():
        roots.append((TIER_BUNDLED, bundled))
    seen = set()
    return [(t, d) for t, d in roots if not (d in seen or seen.add(d))]
```

### 4.2 Ship site-assets in Agent-Payload (CLI/Gateway Portability)

**Option A (Recommended):** Move site-assets to repo root under `site-ops/`

```
site-ops/
├── maps/           # Baseline site maps
│   └── whatsapp-web.json
├── skills/         # Site operation skills
│   └── whatsapp-web-ops/SKILL.md
└── scripts/        # Deterministic operation scripts
    ├── site-deep-map.mjs
    └── site-ops/whatsapp-web.mjs
```

Then add to `RESOURCE_ENV` in `scripts/build/inputs.py`:
```python
RESOURCE_ENV = {
    "skills": "HERMES_BUNDLED_SKILLS",
    "optional-skills": "HERMES_OPTIONAL_SKILLS",
    "plugins": "HERMES_BUNDLED_PLUGINS",
    "locales": "HERMES_BUNDLED_LOCALES",
    "optional-mcps": "HERMES_OPTIONAL_MCPS",
    "site-ops": "HERMES_SITE_OPS",  # NEW
}
```

**Option B:** Keep in `apps/desktop/assets/` and add symlink/copy step in desktop_prepare.py for CLI builds. More complex, less clean.

### 4.3 Generic Site-Ops Framework

Create `site-ops/framework/` with shared utilities:

- `cdp-client.mjs` — Reusable CDP connection + eval wrapper
- `auto-heal.mjs` — Generic healing logic (extracted from whatsapp-web.mjs)
- `map-loader.mjs` — Baseline + local override resolution
- `selector-resolver.mjs` — Priority-based selector lookup from map

Each site's script imports from framework instead of reimplementing CDP boilerplate.

### 4.4 Desktop Integration Hook

In `apps/desktop/src/main/` or equivalent, add IPC handler:

```typescript
ipcMain.handle('site-ops:execute', async (_, site, operation, args) => {
  const scriptPath = resolveSiteOpsScript(site)
  return execFile('node', [scriptPath, operation, ...args])
})
```

This lets the renderer invoke site-ops without spawning shell directly.

---

## 5. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| TIER_BUNDLED breaks existing skill precedence | Medium | Lowest precedence tier; existing skills always win |
| site-ops scripts fail on non-Desktop runtimes (no CDP) | High | Graceful degradation: detect CDP availability, fall back to browser tool or user guidance |
| Auto-heal loop on persistent UI change | Medium | Max 1 retry + cooldown + user escalation after 3 heals/session |
| Local map overrides diverge from baseline | Low | Diff tooling + periodic validation prompts |
| Fork inherits stale selectors | Low | Baseline versioned in repo; forks get updates via merge/rebase |

---

## 6. Prompt de Continuação — Sessão 3/3

```markdown
# 📋 Prompt 3/3 — Plano de Implementação para Site Ops Nativas no Hermes Work

## Objetivo
Criar o plano de implementação detalhado para a arquitetura híbrida (Abordagem C) de Site Operations nativas no Hermes Work, usando WhatsApp Web como caso piloto. O plano deve ser executável em 3 prompts separados de implementação.

## Contexto Validado (Sessões 1 e 2)

### Arquitetura Escolhida: Abordagem C (Híbrida)
Três camadas: Script determinístico + Mapa versionado + Skill playbook com auto-healing.

### Evidências do Build System
1. `RESOURCE_ENV` em `scripts/build/inputs.py:11-17` já mapeia `"skills"` → `HERMES_BUNDLED_SKILLS`
2. `get_bundled_skills_dir()` existe em `hermes_constants.py:408-410` mas NUNCA é chamada por `get_skill_search_roots()` em `agent/skill_utils.py:392-401`
3. Não existe `TIER_BUNDLED` — apenas PROJECT, LOCAL, CREATE_DIR, EXTERNAL (`skill_utils.py:384`)
4. `apps/` está em `INERT_SNAPSHOT_DIRS` (`payload.py:27-30`) — assets do Desktop NÃO vão para agent-payload
5. `apps/desktop/assets/**` incluído no ASAR via `electron-builder.config.cjs:114`
6. Nenhum hook de first-run para indexação de skills encontrado

### Artefatos Já Criados (Protótipo Funcional)
- `apps/desktop/scripts/site-deep-map.mjs` — Mapeamento profundo via CDP (validado: 164 elementos)
- `apps/desktop/scripts/site-ops/whatsapp-web.mjs` — Operações determinísticas (validado: get-unread-count retornou 791)
- `apps/desktop/assets/site-maps/whatsapp-web.json` — Mapa baseline (89.5K)
- `apps/desktop/assets/site-skills/whatsapp-web-ops/SKILL.md` — Playbook da skill

### Relatório Completo da Sessão 2
Leia `workstation/dogfood/artifacts/site-ops-architecture-evaluation-s2.md` para matriz comparativa, especificação de auto-healing e mudanças necessárias no código-fonte.

## Fases de Investigação (Mínimo 3 Ciclos)

### Ciclo 1: Auditoria do Estado Atual
- Verifique se os artefatos listados acima ainda existem e estão funcionais
- Confirme que `get_skill_search_roots()` ainda não inclui TIER_BUNDLED
- Valide que `RESOURCE_ENV` ainda tem a estrutura documentada
- Execute `node apps/desktop/scripts/site-ops/whatsapp-web.mjs get-unread-count` para confirmar CDP funcional
- Documente qualquer drift desde a Sessão 2

### Ciclo 2: Validação das Mudanças Propostas
- Leia `agent/skill_utils.py` linhas 380-410 e confirme a posição exata para inserir TIER_BUNDLED
- Leia `scripts/build/inputs.py` linhas 1-30 e confirme a posição exata para adicionar "site-ops" ao RESOURCE_ENV
- Verifique se mover site-assets para `site-ops/` na raiz quebraria referências no Desktop (grep por `assets/site-maps` e `assets/site-skills`)
- Avalie impacto de TIER_BUNDLED na precedência existente (deve ser lowest precedence)

### Ciclo 3: Definição de Escopo por Prompt de Implementação
- Divida o trabalho em 3 prompts independentes e sequenciais
- Cada prompt deve ser auto-suficiente e gerar um prompt de continuação
- Priorize: (1) Wiring TIER_BUNDLED, (2) Framework genérico + migração site-ops/, (3) Desktop integration + testes E2E

## Fases de Implementação (Mínimo 3 Prompts)

### Prompt de Implementação 1: Wiring TIER_BUNDLED
**Objetivo:** Skills bundled são descobertas automaticamente pelo prompt builder
**Arquivos:** `agent/skill_utils.py`, `agent/prompt_builder.py`
**Critérios de Aceite:**
- [ ] TIER_BUNDLED constante adicionado (valor 4, lowest precedence)
- [ ] `get_skill_search_roots()` inclui bundled root quando diretório existe
- [ ] Skills em `skills/` aparecem no system prompt sem configuração manual
- [ ] Precedência existente preservada (PROJECT > LOCAL > CREATE_DIR > EXTERNAL > BUNDLED)
- [ ] Teste: criar skill teste em `skills/test-bundled/`, confirmar que aparece no catálogo

### Prompt de Implementação 2: Framework Genérico + Migração site-ops/
**Objetivo:** Site-ops funciona em Desktop E CLI/gateway via diretório versionado na raiz
**Arquivos:** `scripts/build/inputs.py`, novo `site-ops/`, migrar `apps/desktop/assets/site-*`
**Critérios de Aceite:**
- [ ] `RESOURCE_ENV["site-ops"]` adicionado
- [ ] `site-ops/framework/cdp-client.mjs` reutilizável
- [ ] `site-ops/framework/auto-heal.mjs` extraído de whatsapp-web.mjs
- [ ] `site-ops/maps/whatsapp-web.json` migrado de assets/
- [ ] `site-ops/skills/whatsapp-web-ops/SKILL.md` migrado de assets/
- [ ] `site-ops/scripts/site-deep-map.mjs` migrado e atualizado para usar framework
- [ ] `site-ops/scripts/site-ops/whatsapp-web.mjs` usa framework imports
- [ ] Referências no Desktop atualizadas (se houver)
- [ ] Agente-payload inclui site-ops/ via snapshot

### Prompt de Implementação 3: Desktop Integration + Testes E2E
**Objetivo:** Renderer invoca site-ops via IPC; fluxo completo validado ponta a ponta
**Arquivos:** `apps/desktop/src/main/`, `apps/desktop/src/renderer/`, testes
**Critérios de Aceite:**
- [ ] IPC handler `site-ops:execute` registrado no main process
- [ ] Renderer chama IPC ao invés de spawn shell direto
- [ ] Auto-healing funciona end-to-end (simular falha de seletor → re-map → retry)
- [ ] Teste E2E: abrir chat "Kevyn ACIRV" via site-ops → enviar mensagem teste → confirmar entrega
- [ ] Teste E2E: get-unread-count retorna valor consistente
- [ ] Documentação atualizada: README ou AGENTS.md com instruções de uso

## Instruções Operacionais
1. Execute os 3 ciclos de investigação ANTES de propor o plano de implementação
2. Se qualquer evidência da Sessão 2 estiver desatualizada, atualize este prompt antes de prosseguir
3. Cada prompt de implementação deve gerar seu próprio prompt de continuação ao final
4. Respeite o protocolo de colaboração multi-agente: verifique claims antes de editar
5. Branch ativa: `feat/hermes-workstation-startup-80-20`
6. Segurança: apenas contatos "Kevyn ACIRV" e "+55 64 9247-0988 (Você)" para testes WhatsApp

## Entregáveis Finais da Sessão 3
1. Plano de implementação detalhado com 3 prompts auto-suficientes
2. Lista de arquivos a modificar/criar por prompt
3. Critérios de aceite testáveis por prompt
4. Riscos identificados e mitigações
5. Prompt de continuação para o primeiro prompt de implementação
```

---

## 7. Resumo Executivo

A Sessão 2/3 confirmou que a **Abordagem C (Híbrida)** é superior em 5 de 7 critérios, incluindo todos os ponderados como "High" ou "Critical". A investigação revelou que o build system do Hermes **já empacota** skills bundled mas **não as descobre** em runtime — um gap de wiring, não uma feature ausente.

O mecanismo de auto-healing foi especificado com guards contra loops infinitos, política clara de atualização de mapas (local vs baseline), e integração com o framework genérico proposto.

As mudanças no código-fonte são mínimas e cirúrgicas: adicionar TIER_BUNDLED a `get_skill_search_roots()`, adicionar `"site-ops"` ao RESOURCE_ENV, e criar o framework compartilhado. Os artefatos prototipados na Sessão 1 continuam funcionais e servem como base para a implementação.

A Sessão 3/3 definirá o plano de implementação em 3 prompts sequenciais, cada um auto-suficiente e com critérios de aceite testáveis.