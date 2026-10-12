# Deep-dive código — n8n e Activepieces
Comparação dirigida aos pontos necessários para Hermes: modelo visual, versionamento, estado de execução e motor canônico.

## n8n
Fonte local n8n-io--n8n, commit 7424f0ca0452.
- packages/core/src/execution-engine/workflow-execute.ts: importação de Workflow, IDataObject, IRunExecutionData, EngineRequest; classe WorkflowExecute contém status, AbortController e suspensionRequested (cerca de linhas 1–125). A implementação traz imports findSubgraph, findStartNodes, recreateNodeExecutionStack, handleCycles, filterDisabledNodes e utilitários de execução parcial.
- packages/core/src/execution-engine/partial-execution-utils.ts: contrato a examinar para seleção de subgrafo, execução parcial e avaliação visual de trechos.
- packages/frontend/editor-ui/src/features/workflows/canvas/components/elements/nodes/render-types/CanvasNodeAgent.vue: interface visual especializada para agentes, localizada por inventário; não significa que canvas possa ser transplantado isoladamente.
- packages/@n8n/workflow-sdk/src/workflow-builder/plugins/types.ts: tipagem de construção do workflow, com dependências de SDK.
O editor e o executor utilizam o modelo de dados do n8n; copiar um componente Vue para o Hermes React/Electron não traz automaticamente persistência, execução ou autorização.

## Activepieces
Fonte em activepieces-main.zip, SHA256 prefixo 0c237aee3b, 30.496 entradas não geradas.
- packages/core/execution/src/lib/flows/flow-version.ts:1–35 exporta FlowVersionState DRAFT/LOCKED; Zod valida flowId, displayName, trigger, schemaVersion, valid, agentIds, state e connectionIds. É uma forma clara de separar edição de versão travada.
- packages/core/execution/src/lib/flow-run/execution/flow-execution.ts:1–90 define FlowRunStatus (PAUSED, RUNNING, SUCCEEDED, FAILED, CANCELED, TIMEOUT...), PauseType DELAY/WEBHOOK/BARRIER e metadados de retomada; isFlowRunStateTerminal diferencia terminais.
- packages/core/execution/src/lib/flows/util/flow-canvas-util.ts:1–105 computa bounding boxes e posições para loops e branches; UI tem layout estruturado derivado do FlowAction/FlowTrigger, não uma segunda engine.
- packages/server/api/src/app/flows/flow-version/flow-version.service.ts e packages/server/engine/src/lib/handler/ (identificados no ZIP): caminhos para estudo adicional de versionamento e execução.
- activepieces-main/LICENSE: MIT Expat para conteúdo geral, mas diretórios packages/ee e packages/server/api/src/app/ee com licença separada.

## Comparação de produto
| Dimensão | n8n | Activepieces | Hermes atual |
|---|---|---|---|
| Work definition | Workflow e nós com conexões | FlowVersion / FlowAction / FlowTrigger | OperationalCapability, implementation.steps e dependencies |
| Lifecycle de edição | definição de workflow e estado de execução | draft/locked declarados | DISCOVERED/VALIDATED/PROMOTED; revisão visual não documentada como produto |
| Execução | WorkflowExecute, parcial e reentrada | servidor engine, estados e pausas tipadas | OperationalKernel, dispatcher, RunLocalAdopter |
| Canvas | editor-ui canvas | flow-canvas-util com branches/loops | UI para capabilities ainda exige adaptador |
| Verificação | resultado do motor/ações | status do flow-run | verifier/owner receipt/authority formal no Hermes |
| Replay/efeitos | avaliar política por nó | avaliar política por fluxo | gate de alcance mais estrito; não submeter a novo engine |

## Decisão
A opção de menor risco é experimentar um PROJETOR READ-ONLY OperationalCapability -> VisualGraph, seguido de editor de parâmetros que produza nova versão candidata, conservando Kernel/Router/Policy como únicos donos de execução. Não importar WorkflowExecute nem engine Activepieces.

Grafo limitado: steps ordenados e dependencies já podem ser projetados como nós/arestas. Branches, loops e triggers arbitrários exigem especificar suporte semântico do Kernel antes de permitir edição; SVG bonito não constitui fluxo executável. Round-trip de editor deve ser lossless nos contratos suportados e rejeitar funções não representáveis.

## Licença
n8n LICENSE.md adota Sustainable Use, arquivos .ee exigem licença enterprise. Não etiquetar indiscriminadamente como permissivo. Activepieces core apresenta MIT Expat com exceções de EE e terceiros. Qualquer cópia requer revisão de proveniência e todas as licenças transitivas.

## Evidência pendente
Não foi executado build de editores nem provas de export/import; não foram lidos todos os arquivos de layout, gateway e schedulers. A conclusão é arquitetural e incremental, não afirma paridade visual com ambos os produtos.