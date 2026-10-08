# Hermes Creative Workstation — prompt inicial para IA implementadora

**Repositório:** `kevynlucasprofissional-stack/hermes-agent`. **Iniciativa:** `workstation/creative-workstation/`. **Status:** planejamento; **NENHUM runtime criativo qualificado**. Documentação no PR #50 (`docs/creative-workstation-foundation-20261008`) até ser incorporada.

## Missão e ponto de partida

Implemente o Creative Workstation incrementalmente **reutilizando o Hermes**: projetos editáveis pelo humano/agente, APIs/MCP/CLI tipados, preview no Chromium Electron, outputs verificados e reuso futuro pelo Experience Compiler.

**Leitura (em ordem):**
1. **Obrigatória e sem atalhos:** `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md` e todas as leituras/gates ali exigidos. Obedeça H-079, H-080 e bloqueios P0.
2. **Compacta:** `workstation/creative-workstation/EXECUTION_BRIEF.md`.
3. **Só fase atual:** seção CW-01 de `IMPLEMENTATION_PLAN.md`, testes dessa fase em `VERIFICATION_MATRIX.md` e fonte/owner específico quando necessário.
4. **Depois:** `PHASE_PROMPTS.md` contém instruções de cada próxima fase. Não carregue históricos completos ou projetos externos sem necessidade e **não pule** leituras canônicas obrigatórias.

## Execute agora SOMENTE CW-01 — auditoria e liberação

1. Identifique `main`, situação do PR #50, upstream pin, merge-base, CI required, owners/seams. Não faça merge.
2. Execute o gate H-079 no baseline correto e classifique H-080A/H-080B, KI-024 e demais bloqueios, incluindo auditoria de dependências.
3. Inspecione código atual e produza tabela `owner → arquivo::símbolo → comportamento existente → gap mínimo` para lifecycle/processo, MCP/skills, Browser Electron, Control Plane, TaskCompiler, ArtifactStore/Journal e Experience Compiler.
4. Verifique repositório/SHA/licença/segurança de Penpot MCP e AI Kit, Three.js Editor, FFmpeg e Remotion (licença comercial/redistribuição). Não instale nada.
5. Registre achados e falsificadores no journal; entregue `GO` ou `BLOCKED` com SHAs, links, testes/CI efetivos e lista mínima de arquivos para CW-02. **Se gate vermelho, não altere runtime.**

## Fases posteriores, cada uma com PR e provas próprios

`CW-02` app/capability discovery + health/opt-in → `CW-03A` React/SVG + preview real Electron + PNG → `CW-03B` FFmpeg/ffprobe → `CW-03C` Remotion **somente se licença aprovada** → `CW-04` Penpot e `CW-05` Three.js em PRs independentes → `CW-06` engines opcionais por necessidade → `CW-07` Experience Compiler após uma vertical com efeitos comprovados. Siga a fase específica em `PHASE_PROMPTS.md`; não implemente tudo num PR.

## Invariantes e aprovação

- Não duplicar Session/TaskRun/Kanban/BrowserTask, Control Plane, approvals, Journal, ArtifactStore ou registry/Experience Compiler.
- Sem execução privilegiada arbitrária, instalação automática, segredos em logs, writes fora do workspace, sobrescrita de revisão humana ou retry cego de mutações incertas.
- Skill instrui; MCP/API/CLI executam; certificação exige verificador empírico/negative replay/policy.
- `VERIFICATION_MATRIX.md` define os oráculos, negativos, Windows/Electron E2E, rollbacks e gates. Não invente comandos, PASS, CI ou recibos; `NOT_RUN` e `BLOCKED` são válidos.
- Conserve `main`, upstream-first, SHAs fixos e PRs pequenos. Não faça merge automaticamente.

## Saída obrigatória

```text
FASE / STATUS: CW-xx — GO | BLOCKED | IMPLEMENTED | E2E_PASS | QUALIFIED
BASELINE: main SHA / upstream pin / gates / exact-head CI
OWNERS: caminho::símbolo → reutilização/gap
EXTERNAL: ref/license/risco
TESTS: comandos executados e outcomes (ou NOT_RUN); negativos
EVIDENCE: receipts, revisões, hashes, outputs
BLOCKERS: motivo / menor correção segura / rollback
GITHUB: branch / commit / PR / checks / merge status
```

**Comece por CW-01. Priorize evidência e mudanças pequenas, sem rediscutir a visão já consolidada.**
