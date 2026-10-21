# Segunda auditoria — Hermes Workstation Browser

Verificação direta no computador Windows, confrontando o PDF de 183 páginas, o plano anterior e o código local.

## 1. Primeira descoberta: o plano anterior já está desatualizado

Consegui acessar `C:\Github\hermes-agent` pelo Desktop Commander. O repositório local está em um estado significativamente diferente daquele examinado pelo GitHub na auditoria anterior.

|Informação|Estado local encontrado|
|---|---|
|Branch|`feat/d049-browser-80-20-impl-20261018`|
|HEAD|`fd80408ab29c9cc701dacf1fbe4ceb7899c1a836`|
|Último commit|D-049 B1.2: sanitização de segredos e B1.3: validação de schema|
|Working tree|Contém alterações não commitadas e numerosos arquivos novos|

Também encontrei novos arquivos relacionados à observação compacta e a testes de segurança. Isso significa que não seria correto simplesmente entregar os quatro prompts de implementação que sugeri anteriormente: parte das mudanças já avançou, e é necessário verificar sua integração antes de pedir mais código.

A árvore de trabalho contém alterações que podem pertencer a outras sessões ou agentes. Não vou modificá-las.

## 2. Duas correções relevantes na avaliação anterior

### A correção de caminhos já está em andamento

A alteração não commitada em `workstation/browser_bridge.py` substitui a comparação textual insegura por `Path.is_relative_to()` e utiliza o caminho resolvido na gravação. Há também uma suíte nova, `test_browser_bridge_security.py`, cobrindo diretórios irmãos, symlinks e destinos legítimos.

Portanto, esse item não deve continuar no roadmap como uma implementação inteiramente nova. A tarefa restante é validar os testes, revisar os limites de segurança e consolidar a alteração existente.

Há uma ressalva técnica: utilizar o caminho resolvido elimina a divergência entre o caminho inicialmente validado e aquele utilizado para gravação, mas não elimina uma troca concorrente de symlink entre a validação e a abertura do arquivo. Esse risco precisa ser descrito corretamente, sem exigir uma arquitetura mais complexa antes de demonstrar que ela é necessária.

### As observações compactas também já estão implementadas parcialmente

Encontrei `workstation-browser-snapshot-views.ts`, com quatro projeções: `summary`, `action_map`, `focus` e `content`.

A lógica já está conectada à operação `browser_snapshot` no runtime Electron, preservando internamente o snapshot canônico. Os novos testes, entretanto, ainda não comprovam uso efetivo pelo agente nem redução de tokens em tarefas completas.

Isso altera a recomendação de prioridade: antes de criar outra camada de otimização, é preciso garantir que a IA consiga solicitar e receber essas projeções de forma econômica pelo contrato real de ferramentas.

## 3. Achado mais importante: duas otimizações ainda não fecham o ciclo com a IA

Encontrei um problema de integração que considero mais relevante para o ganho imediato do que adicionar novas técnicas de observação.

A. As views compactas não aparecem no contrato atual de `browser_snapshot` exposto ao agente. O runtime aceita `view`, `focus_ref`, `focus_neighbors` e `max_chars`, mas o schema em `tools/browser_tool.py` apresenta somente `full`. Além disso, a projeção Python que elimina elementos duplicados foi construída para o formato de snapshot tradicional; não está demonstrado que ela reduza corretamente a resposta das novas views.

Consequência: o código pode gerar observações econômicas sem que o agente consiga escolhê-las normalmente ou receba todo o benefício da compactação.

B. A validação de schema não é uma garantia ponta a ponta. O Electron agora retorna `schema_valid`, mas mantém `success: true` mesmo para itens não conformes. No fluxo durável, `workstation/browser_projection.py` continua usando uma validação própria, baseada em `title`, e seu resumo não incorpora explicitamente o novo `schema_valid`.

Isso abre a possibilidade de uma extração rejeitada pelo schema solicitado ser registrada e apresentada como válida por outra camada. É um problema de integração e semântica do resultado, não uma razão para criar um segundo validador.

Também confirmei que `BrowserReadinessContract` é acionado em preflights declarados do `TaskCompiler`, mas não funciona como gate universal do navegador. Torná-lo obrigatório em toda leitura, como propõem algumas análises do PDF, não seria necessariamente uma melhoria: poderia introduzir novas esperas e falsos bloqueios.

## 4. Verificação com testes locais

Executei testes focados no computador, utilizando as dependências já instaladas, sem instalar pacotes nem editar o código.

|Verificação|Resultado|
|---|---|
|Segurança de caminhos — Python|7 passaram, 1 pulado|
|Views compactas — Vitest|11 passaram|
|Validação de schema — Vitest|9 passaram|
|Escopo de Learning B0.2 — Vitest|1 passou, 36 testes não selecionados|

O defeito B0.2 também já recebeu uma correção no runtime local. `startLearning` agora rejeita uma aba sem `ownerTaskId` antes de tentar assumir controle. O teste focado passou. Isso não equivale a um teste com toda a interface Electron e usuário real, mas comprova o comportamento exercitado pelo contrato de teste.

Encontrei ainda um bloqueador de integração objetivo: o commit atual importa `workstation-browser-snapshot-views.ts`, mas esse arquivo existe somente como não rastreado no Git. Confirmei consultando o conteúdo do próprio HEAD, não apenas o diretório local.

Consequência: um checkout limpo desse commit não contém um módulo necessário ao runtime. Consolidar esse arquivo e suas provas deve vir antes de desenvolver outra funcionalidade.

## 5. Novo ranking 80/20

Minha recomendação mudou após a investigação local. A prioridade agora deve ser concluir e integrar corretamente o que já foi desenvolvido, antes de ampliar a arquitetura.

|Ordem|Trabalho recomendado|Esforço residual|Decisão|
|---|---|---|---|
|1|Consolidar arquivos e garantir build a partir de checkout limpo|Baixo|Fazer agora|
|2|Propagar corretamente a validação de schema até os resultados duráveis|Baixo–médio|Fazer agora|
|3|Expor views compactas no contrato de ferramentas da IA e eliminar redundância|Baixo–médio|Fazer agora|
|4|Otimizar snapshot delta mediante benchmark real|Médio|Medir primeiro|
|5|Recuperação semântica de elementos antes de ações|Médio–alto|Fazer se DOM drift for frequente|
|6|Comparação forense, WebMCP e mecanismos mais avançados|Variável|Adiar|

O pacote de maior retorno provável é integridade dos resultados + observações realmente econômicas + integração completa com o agente.

Isso é diferente de implementar simplesmente mais recursos. O código existente precisa produzir benefícios verificáveis no percurso inteiro:

Agente / TaskRun

Schema da ferramenta

Controller Electron / Chromium

Observação ou ação autorizada

Validação e resultado durável

Resposta compacta e confiável à IA

Cadeia proposta sem duplicar responsabilidades existentes.

## 6. Plano de execução corrigido

Recomendo três sessões de implementação, com uma quarta apenas se os benchmarks ou os logs justificarem:

1. Fechamento da implementação atual: consolidar módulos não rastreados, revisar os patches de segurança e Learning e garantir checkout reproduzível.
    
2. Integridade das extrações: corrigir a passagem do resultado de schema para WorkItems e resumos, com testes negativos e prevenção de falsos sucessos.
    
3. Economia efetiva de contexto: permitir que o agente solicite `action_map` e `focus`, corrigir a duplicação de campos e medir tokens e tempo até conclusão.
    

A sessão condicional seria dedicada à reaquisição semântica de alvos em páginas dinâmicas, mantendo proteção contra ações duplicadas.

## 7. Relatório completo da segunda investigação

Baixar segunda auditoria local e roadmap revisado

Documento técnico com evidências e caminhos locais, matriz comparativa do PDF, classificação das hipóteses, resultados dos testes, critérios de aceite, ordem de implementação e instruções para a próxima IA.

Conclusão: mantenho a arquitetura central proposta anteriormente, mas rejeito a antiga ordem de implementação como a mais econômica para o estado atual do código. Ela desperdiçaria esforço repetindo trabalho parcialmente concluído. O melhor próximo passo é resolver os pontos em que capacidades existentes ainda não se traduzem em resultados corretos, acessíveis e baratos para a IA.

A auditoria não executou um fluxo E2E autenticado com comprovação de efeito externo. Portanto, ainda não há fundamento para afirmar uma porcentagem real de ganho de desempenho ou aumento da taxa de conclusão. Nenhum arquivo ou branch do repositório local foi alterado deliberadamente nesta investigação.