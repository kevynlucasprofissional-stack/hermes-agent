# Experience Compiler e editor visual — estudo de viabilidade
Pergunta: capacidade compilada pode ser visualizada e alterada sem introduzir outro executor ou contornar certificados?

## Estrutura de dados auditada
workstation/operational_capabilities.py define OperationalCapability com id, version, input_schema, output_schema, route, effect, scope, preconditions, postconditions, verifier_contract, dependencies, implementation, lifecycle, provenance e fingerprints. workstation/experience_compiler/compiler.py cria implementação determinística em steps e generaliza parâmetros. hierarchical.py permite dependências entre capacidades. Fonte de persistência é Registry/ArtifactStore, não um arquivo .md.

## Alternativas
| Alternativa | Ganho | Risco | Decisão |
|---|---|---|---|
| A — viewer read-only | Transparência imediata com mínimo acoplamento | Informação incompleta para graph complexo | COMEÇAR |
| B — editor de parâmetros tipados | Controle humano dentro de schema | parâmetros podem mudar efeitos | SEGUNDO, somente revisões não executáveis sem validação |
| C — editor de grafo de capabilities | Composição e depuração | branches/loops e round-trip inválidos | CONDICIONAL à IR real |
| D — construtor n8n completo | Triggers/loops/integrações | cria runtime concorrente | NÃO recomendável agora |
| E — integração externa | reaproveita produto consolidado | credenciais, licenças, dupla autoridade | INVESTIGAR como export/adaptador isolado |

## Hipótese técnica mínima
1. Read API de capabilities e owner receipts: payload sem secrets com source ref, lifecycle e razões de BLOCKED/HELD/DRIFT.
2. Representação somente de steps existentes e dependencies como grafo; nós de verificador e policy read-only. Mostrar UNKNOWN para evidências ausentes.
3. UI integrada às superfícies React/Electron atuais, sem novos dispatchers.
4. Operação Edit gera revision draft com novo ID/version/fingerprint, preserva original e prova de provenance; aplica schema validation e rejeita rotas não representáveis.
5. Validação isolada da revisão pelo owner já existente. Nenhuma revisão herda automaticamente PROMOTED ou authority.
6. Vista run-time de execução real, baseado em Telemetry e readback e não no andamento inferido pelo LLM.
7. Provar round-trip, fallback para semântica ausente e no-op em capability impossível de representar.

## Operações lossless versus não representáveis
- Steps sequenciais com dependências acíclicas, inputs declarados e nós de pre/post/verifier podem ser renderizados sem perda como projeção.
- Ramificações, loops, expressões arbitrárias, trigger/cron e subflows com side effects podem NÃO ser suportados pelo atual Kernel; não converter em sequências aparentes que alterem efeito.
- Quando schema não cobre nó, apresentar raw inspector somente leitura e negar edição.
- Layout canvas pode ser derivado (como Activepieces flow-canvas-util); não adicionar campos de layout à verdade operacional se não são necessários.

## Segurança de edição
Patch em contract, step, effect, scope ou dependency invalida certificado dependente, exige novo fingerprint e revisão; authority só vem do TaskRun atual e owner em dispatch. Replay e negative control devem ser independentes; nenhuma simulação pode ser apresentada como resultado verificado.

## Aceitação falsificável
A: 5 capabilities reais diferentes renderizadas sem exceptions, fingerprints estáveis, vínculos verificáveis e nenhum side effect.
B: export -> import -> canonical hash idêntico para subconjunto suportado; rejeita branch/loop que não é expressável; edição muda fingerprint e retorna DISCOVERED.
C: teste sem browser/authority/tenant correto jamais executa.
D: painel distingue OBSERVED, DISCOVERED, VALIDATED, PROMOTED, reused_verified e UNKNOWN; não fabricar economy%.

## Veredito
Viável como projeção/UI de capacidades atuais; NÃO comprovada viabilidade de um workflow builder completo sem estender semântica do Kernel. Priorizar funil de aprendizagem efetivo e viewer antes de editor completo.