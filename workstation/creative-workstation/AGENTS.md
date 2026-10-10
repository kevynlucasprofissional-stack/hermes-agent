# Creative Workstation — orientações para agentes

## Contexto vigente da iniciativa — D-041 (2026-10-09)

O **ponto de entrada criativo atual** é [HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md](HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md), com a decisão/arquitetura em [HYPERFRAMES_ADOPTION_2026-10-09.md](HYPERFRAMES_ADOPTION_2026-10-09.md). HyperFrames Studio auto-hospedado é o editor-base do Hermes Workstation. A antiga sequência Remotion/Penpot/Three CW-01→07 foi substituída apenas para seleção e ordem de produto; **root AGENTS, workstation AGENTS, leituras canônicas e gate H-079 continuam obrigatórios**. Não chamar nenhum runtime de instalado, funcional ou qualificado sem prova. Desenvolvimento isolado segue a exceção registrada; sem merge automático.


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
