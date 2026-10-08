# Hermes Creative Workstation — prompt operacional para a IA implementadora

**Repositório:** `kevynlucasprofissional-stack/hermes-agent`. **Iniciativa:** `workstation/creative-workstation/`. **Estado inicial:** documentação apenas; sem runtime criativo instalado/qualificado. **Branch documental:** `docs/creative-workstation-foundation-20261008` (PR #50; use `main` quando a documentação estiver integrada).

## Ordem de leitura, sem gastar contexto desnecessário

1. **Mandatório:** siga integralmente `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md` e as leituras/gates requeridos pelo repositório. Não contorne a política H-079 nem leia apenas um resumo quando uma instrução canônica obrigar leitura.
2. **Operacional:** leia `workstation/creative-workstation/EXECUTION_BRIEF.md`, a unidade atual em `IMPLEMENTATION_PLAN.md`, e as seções relevantes de `VERIFICATION_MATRIX.md`.
3. **Por demanda:** consulte `ARCHITECTURE.md` e `INTEGRATIONS.md` somente para o subsistema/tool da fase; leia `SOURCE_MATRIX.md` e documentos históricos extensos por seção/símbolo/intervalo quando necessário. As transcrições em `research/` são fontes históricas, não leitura inicial obrigatória.
4. **Para a próxima fase:** use `PHASE_PROMPTS.md`, uma fase por vez.

## Execute AGORA: CW-01 — preflight e plano de integração

1. Resolva branch/PR #50 vs `main` **sem fazer merge automático**.
2. Registre `DOWNSTREAM_MAIN_SHA`, `UPSTREAM_MAIN_SHA_OBSERVED`, `CURRENT_PIN_SHA`, merge-base/ahead-behind, CI obrigatórios, owner e seam afetados. Execute preflight H-079 e obtenha status GO/BLOCKED.
3. Determine de forma concreta, lendo o código atual, os owners existentes de capability/adapter, managed processes, plugins/MCP/skills, Browser Electron, TaskCompiler, ArtifactStore/Journal, OperacionalCapabilityRegistry e Experience Compiler. Anote `arquivo::símbolo → função existente → lacuna mínima`.
4. Audite repositório/ref/licença/dependências de Penpot MCP/AI Kit, Three.js Editor, FFmpeg e Remotion (este último condicionado à licença); nenhum install automático.
5. Identifique blocker H-080A/H-080B/KI-024, quaisquer CVEs/auditoria de dependências e a qualificação real do baseline. **Se houver gate vermelho, pare antes de modificar runtime**; registre no journal e entregue plano mínimo para desbloquear.
6. Entregue relatório CW-01: `GO|BLOCKED`, SHAs, evidências, matriz owner→caminho, primeiros arquivos/contratos sugeridos para CW-02, riscos e menores passos.
7. Não mexa em `main`; faça PR independente para qualquer mudança posterior.

## Depois de CW-01

Somente se gates permitirem, implemente **CW-02** num PR pequeno, com descoberta/health e lifecycle opt-in, sem novo DB/Browser/autoridade. Siga uma fase por vez:

`CW-02 → CW-03A React/SVG + Electron + PNG → CW-03B FFmpeg → CW-03C Remotion (somente licença) → CW-04 Penpot / CW-05 Three.js (PRs independentes) → CW-06 engines opcional → CW-07 Experience Compiler reuso verificado`.

CW-07 pode começar após uma vertical comprovada; não precisa aguardar todas as engines.

## Invariantes não negociáveis

- Reutilizar Control Plane Router/Policy/Verifier, TaskRun/Kanban, BrowserTask/WebContentsView, ArtifactStore/Journal, OperationalCapabilityRegistry e Experience Compiler existentes.
- Skills são instruções; MCP/API/CLI oferecem ações; capabilities aprendidas exigem prova causal externa/replay/promoção. Laya/System-1 não autoriza efeitos.
- Preferir operações tipadas/API/CLI/MCP a mouse. Manter projeto editável, revisão humana, hashes/proveniência e rollback.
- Exigir autorização explícita para instalações, efeitos irreversíveis e terceiros. Version pin + licença + sandbox + env allowlist + no secret leakage.
- Nenhuma promoção sem recibo do owner, testes negativos e verificação real. Não chamar screenshot, exit code ou sucesso de mock de `E2E_PASS`.
- Se bloqueado, reportar o resultado **sem inventar sucesso**, sem enfraquecer gate, sem instalar tudo e sem fazer merge.

## Formato final de cada fase (preencher apenas resultados observados)

```text
FASE / STATUS: CW-xx | PLANNED, BLOCKED, IMPLEMENTED, INTEGRATION_PASS, E2E_PASS, QUALIFIED
BASELINE: downstream SHA / upstream SHA pin / CI / H-079 / upstream drift
OWNERS: caminho::símbolo utilizado; contratos criados ou modificados
LICENÇA/SUPPLY-CHAIN: ref, dependências, consentimento, parecer de uso/distribuição
TESTES: comandos realmente executados, resultados e testes negativos (ou NOT_RUN)
EVIDÊNCIAS: receipts, hashes, revisão do projeto, ffprobe/artefato, E2E se aplicável
BLOQUEIOS / ROLLBACK: impacto e próxima ação mínima
GIT: branch / commit SHA / PR / checks / status de merge
```

**Não amplie o escopo para a suíte inteira na primeira execução. Comece por CW-01 e pare no primeiro gate real que impeça implementação funcional.**
