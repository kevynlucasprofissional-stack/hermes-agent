# Creative Workstation — orientações para agentes

<!-- creative-D043-overlay -->
## Contrato D-043 vigente (2026-10-10)
Leia a [arquitetura engine-neutral](ENGINE_NEUTRAL_ARCHITECTURE_2026-10-10.md) e o [handoff CWN-00→09](ENGINE_NEUTRAL_IMPLEMENTER_HANDOFF_2026-10-10.md) após os arquivos obrigatórios do Workstation. HyperFrames-first D-041/PR #62 está supersedida como escolha de motor, não como evidência; D-042/PR #63, H-079 e D-038/D-039 seguem. Não classificar drafts #57–#61 como merged/qualified. Não criar outro owner do Browser/TaskRun/artefatos ou priorizar UI tradicional sobre o documento compartilhado.

<!-- /creative-D043-overlay -->


Este diretório é **especificação de iniciativa**, não um novo runtime. Aplicam-se `../../AGENTS.md`, `../AGENTS.md`, `../context/README.md` e as políticas de qualificação e journal canônicos.

- Para trabalho documental, mantenha fatos comprovados separados de propostas e investigue o estado atual antes de mudar classificações.
- Para qualquer alteração funcional, execute primeiro o gate H-079 (upstream-first, SHA pinado e baseline aprovado), leia o contexto na ordem canônica e obedeça bloqueios de confiabilidade existentes.
- Não trate esta pasta como autorização de instalação, execução de código externo, abertura de portas ou adição de uma autoridade de estado.
- Não proclame "pronto" sem demonstração real, prova negativa, runtime Electron quando aplicável e CI no HEAD exato.
- Decisões canônicas vão para `../context/DECISIONS.md` quando efetivamente aceitas; estudos vão para `../SOURCE_MATRIX.md`; andamento para `../ROADMAP.md`; resultados de experimentos para `../context/engineering-journal/CURRENT.md`.

## Protocolo curto de entrada

- Comece por [EXECUTION_BRIEF.md](EXECUTION_BRIEF.md) **depois** das leituras obrigatórias previstas em `../context/README.md`.
- Execute apenas a fase atual em [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md); use [PHASE_PROMPTS.md](PHASE_PROMPTS.md) para um handoff compacto.
- Toda mudança funcional exige a evidência e os testes negativos em [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).
- [research/2026-10-08-full-analysis.md](research/2026-10-08-full-analysis.md) e [research/2026-10-08-full-documentation-proposal.md](research/2026-10-08-full-documentation-proposal.md) preservam o contexto histórico e **não** substituem o código e as decisões atuais.
