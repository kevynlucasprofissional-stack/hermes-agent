# HWH-001 — plano de execução enxuto (2026-10-13)

## Orçamento de execução
**4 etapas totais**, das quais a primeira (0) é o trabalho atual de coordenação; **meta de 3 prompts de implementação adicionais**. Esta é uma estimativa de planejamento, não uma promessa de número exato de sessões. Um prompt pode concluir mais de uma etapa quando há condições e testes verdes.

**Etapa 0 — Concluída somente com commit/push:** branch única, protocolo e ferramenta local de claims, AGENTS/context, quadro, contratos de HWH e handoff. Nenhuma expansão de produto.
**Etapa 1 — Prompt 1: abrir Creative + Hub** (HWH-01 e HWH-02 juntas): ferramenta inequívoca do Agent para abrir/focar a UI Creative interna; rota/UI workbench, label Workstation, botão, provider React já existente, alternância Chromium/Creative preservando a aba web. TDD RED→GREEN e prova de navegação/switch. Não abrir outra branch/worktree.
**Etapa 2 — Prompt 2: Levar para sessão** (HWH-03): somente novo chat real via Gateway canônico; adotar mesma WebContentsView sem loadURL; BrowserTask vinculada à sessão/perfil/TaskRun correto; human 409→explicit release→agent; testes de identidade, stale, foreign, clique duplo e falha. Não criar seletor de sessões antigas.
**Etapa 3 — Prompt 3: qualificação e entrega**: três percursos E2E nativos A/B/C, regressões de segurança e tipagem, CI no HEAD exato, correções comprovadas necessárias, PR único pronto para revisão, sem merge automático.

## Critérios de stop/advance 20/80
- Cada etapa visa **uma experiência utilizável**, não perfeição de arquitetura. Limite leituras aos owners e testes relacionados; já existem logs, plano e contratos.
- Se o baseline H-079 ou CI bloquear, registrar diagnóstico **uma única vez no ciclo**, executar trabalho permitido e deixar explícito o gate; não refazer a mesma auditoria a cada prompt. Não contornar gate obrigatório.
- HWH-01 aceita quando pedido real abre/foca UI correta sem searches, e falha se Desktop indisponível; HWH-02 quando UI e native view alternam sem perda. Pular edições redundantes do CreativeProvider se já corrigido.
- HWH-03 aceita somente com prova de identidade original da WebContentsView, preservação JS/DOM durante transferência, sessão real, lease humano e retomada.
- Qualificação final exige testes direcionados, 3 E2Es Electron reais (NOT_VERIFIED_NATIVE se indisponível), avaliação de riscos e integração. Não confundir contagem unitária com produto real.
- Em caso de bloqueio técnico material, permitir **no máximo um ciclo causal direcionado por bloqueio** antes de classificar e comunicar o impeditivo; não fabricar sucesso. A regra não autoriza ignorar vulnerabilidades nem falsificar testes.

## Divisão de trabalho simultânea
Agentes A e B podem avançar em arquivos disjuntos, combinando uma única interface para a abertura; agente C pode preparar contrato/testes enquanto A/B implementam, mas não edita arquivos de A/B até transferência de ownership. Agente D acompanha progresso, sincroniza Git e qualifica.
Um integrador publica as mudanças uma vez por marco. Não permitir que os 4 façam `git commit` ou `git pull` ao mesmo tempo.

## Handoff obrigatório
Todo agente que encerrar antes do fim cria prompt contendo branch/checkout/HEAD atuais, estado `status` local, files claimed, exatamente um próximo teste RED ou gate, evidências realmente executadas, PR, próximos passos e esta mesma obrigação recursiva. O prompt completo canônico está em `NEXT_PROMPT.md`. Se a realidade divergir, corrigir primeiro o documento e nunca presumir status de outro agente.
