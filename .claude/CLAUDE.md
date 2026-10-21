@../AGENTS.md

<!-- hermes-work-engineering-focus-20261020 -->
# Hermes Work: disciplina de engenharia e dogfooding

Estas instrucoes sao especificas deste repositorio e complementam o AGENTS.md importado acima e o contrato global do usuario.

- O usuario traz uma visao de arquitetura e produto ampla; a IA deve complementar essa visao com critica de engenharia baseada no codigo REAL. Antes de propor reescrita de Chromium, Electron, Browser Use, Playwright ou quaisquer outros componentes, analise implementacao atual, testes, gargalos e custo de regressao. Apresente alternativas com trade-offs e evidencia. Uma hipotese do usuario nao e decisao tecnica.
- Trabalhe com um subescopo operacional por ciclo, orientado a resultado ponta a ponta. A automacao de WhatsApp pelo Browser interno foi um foco de uma sessao especifica; NAO a imponha a toda nova tarefa: identifique a prioridade atual explicitamente solicitada. Registre futuras ideias sem abrir escopo paralelo.
- Para automacao de browser no Hermes Work, preserve o requisito de produto de uma experiencia de navegador integrada AO PROPRIO Hermes (e nao simplesmente um Chrome externo). O motor subjacente pode ser reavaliado com dados e testes; nao troque tecnologia sem demonstrar ganho concreto.
- Ao estudar projetos de referencia (Browser Use, Playwright, etc.), primeiro identifique o problema exato no Hermes e as partes aproveitaveis; prefira adaptacao de interfaces existentes ou solucoes testadas ao transplante indiscriminado de codigo.
- Aperfeicoe o dogfooding em dois monitores: Hermes aberto e disponivel para testes enquanto IAs trabalham no codigo, com ciclos curtos de observacao, diagnostico e correcao. Examine hot reload, reload seletivo e supervisao de processos antes de propor alteracoes. Quando reinicio for necessario, privilegie preservar estado/sessao e isolar funcionalidades em desenvolvimento. Nao garanta hot reload onde a arquitetura nao permite.
- Alteracoes em paralelo exigem coordenacao de arquivos, controle de versao e integracao nao destrutiva. Verifique branch, working tree e protocolo de colaboracao VIGENTES antes de editar; nunca sobrescreva trabalho de agentes concorrentes nem assuma branch antiga como estado atual.
- Para concluir um ajuste, produza evidencia em runtime, criterios de aceite de comportamento, testes de regressao e lista explicita do que foi ou nao validado. Aplique as tres passagens minimas de planejamento e as tres de implementacao para etapas importantes, conforme a regra global.
<!-- end-hermes-work-engineering-focus-20261020 -->