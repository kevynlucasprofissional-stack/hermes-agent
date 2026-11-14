# Missão: homologar System 1 Browser com mensagem humana real

Você está executando uma qualificação local do Hermes Work em
`C:\Github\hermes-agent`, sem alterar sessões ou dados produtivos.

Leia primeiro:
`workstation/benchmarks/SYSTEM1_BROWSER_LAYA_QUALIFICACAO_20261107.md`
e os guardrails `AGENTS.md` e `workstation/AGENTS.md`.

**Página de prova já preparada:** `http://127.0.0.1:18791/unique`.
Confira `http://127.0.0.1:18791/health` antes de navegar. Variações:
`/unique` (um botão Relatórios), `/partial` (Abrir relatórios),
`/duplicate` (dois botões Relatórios) e `/missing` (sem Relatórios).

Faça o menor teste real e auditável, nesta ordem:

1. Confira branch/HEAD e alterações existentes. Identifique se a sessão atual tem
   BrowserTask e TaskRun legítimos; verifique estado do Browser e a disponibilidade
   do AI Control. Não assuma que este Hermes está com o fast path habilitado:
   a flag `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED` é **off por padrão**,
   e o Python ativo anteriormente não possuía Laya.
2. Usando SOMENTE o Browser nativo e o escopo desta sessão de teste, abra
   `http://127.0.0.1:18791/unique`, leia um snapshot real e confirme URL,
   identidade da tarefa, rótulos e referências observadas. Não clique em botões.
   Se aparecer `reconciliation_required`, lease humano ou operação UNCERTAIN,
   pare sem repetição de mutação.
3. Registre baseline somente se puder medir de verdade: duração até a resposta,
   chamadas ao System 2, resultado e readback. Não use mocks nem valores
   estimados como evidência. Não modifique o processo do Hermes em uso.
4. Para testar a rota System 1, prepare **apenas se viável sem interferência**
   um runtime de teste independente com seu próprio perfil, backend, sessão,
   armazenamento, e ambiente PM `%LOCALAPPDATA%\HermesWorkstation\qualification\system1-laya-project`.
   Esse runtime deve herdar `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED=1`
   e ter o provedor Laya realmente registrado. Nunca instale dependências na
   `.venv` ativa, nunca altere variável global, permissões, ledger, lease,
   sessões nem reinicie o Hermes atual. Se não puder ligar UI e backend
   isolados de forma segura, **registre o bloqueio e não finja o teste**.
5. Quando a página estiver aberta e o runtime de cada variante estiver pronto,
   responda **PRONTO PARA FRASE EXATA** com qual variante está operacional.
   Então pedirei a localização por mensagem humana SEPARADA, literalmente:
   `Localize o botão Relatórios na página atual`.
   Não inclua essa instrução em uma mensagem combinada e não simule origem humana.
6. Após a resposta ao comando exato, verifique a fonte de cada prova:
   `origin=human`, task/session/run, snapshot inicial e fresco, ref selecionada,
   motivo exato/system1/fallback, provedor Laya quando aplicável e recibo final.
   Repita em `/partial` para exigir modelo real, `/duplicate` para exigir
   recusa de ambiguidade e `/missing` para ausência. Cada URL deve ser aberta
   antes da frase exata enviada como novo turno.
7. Compare baseline vs System 1 apenas com tarefas equivalentes, custo/chamadas
   efetivamente instrumentados, latência e acerto. Não promova a flag ao Hermes
   produtivo sem ganho medido e preservação dos guards.
   Registre evidências em arquivo novo sob
   `workstation/benchmarks/system1_live_session/` e produza um resumo objetivo
   com PASS/FAIL/BLOQUEADO. Não faça commit/push/merge.

**Limites:** não reiniciar o aplicativo ativo, não usar mouse/teclado global,
não mudar a política do Browser, não tocar em outras sessões, não repetir
operações incertas. Se algum pré-requisito essencial faltar, reporte exatamente
qual é, como verificou e a menor ação segura necessária.
