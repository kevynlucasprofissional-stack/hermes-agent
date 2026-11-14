# Browser: verificação semântica após reconstrução do DOM — 2026-11-07

## Escopo e estado
MVP local implementado em `main@f1d5ab2f03` sobre working tree preexistente com alterações de outros ciclos. **Não houve commit, push, reset, stash, reinício do Hermes, reexecução de operações incertas nem alteração do ledger real.** O coordenador histórico de claims está aposentado; foram inspecionados Git status, autores e datas de escrita antes da edição.

## Causa comprovada
`hasVerifiedBatchEffect` rejeitava `selected` depois que o elemento DOM era substituído, mesmo se a seleção esperada já constava no novo elemento. RED isolado: `stale_or_replaced_target` quando se espera `semantic_selection_rebound_readback`. A proteção antiga contra falsos ACKs e replay não deve ser removida.

## Implementação
- `apps/desktop/electron/workstation-browser-batch-proof.ts`: `batchObservationScript(ref, anchor?)` captura somente leitura de alvo único com anchor explícito `testid`, `name` ou `label`; exige mesma identidade semântica não vazia, tag, role, e transição `aria-selected=false -> true`. Anchors genéricas (`role` ou implícitas), ausência, ambiguidade e mudança de documento continuam incertas. Dados do alvo são efêmeros, sem persistência em recibos.
- `apps/desktop/electron/workstation-browser-runtime.ts`: somente `click` com `postcondition.selected` fornece anchor aos readbacks antes/depois, inclusive no bounded recheck. Outras ações, envios e controle de autoridade permanecem inalterados.
- `apps/desktop/electron/workstation-browser-batch-proof.test.ts`: regressões positivas/negativas e execução real do readback em DOM JSDOM, sem alterar referências de runtime.

## Evidência
- Baseline anterior aos patches: 31/31 Vitest direcionados.
- RED da nova regressão antes do patch: 1 falha esperada (`stale_or_replaced_target`).
- GREEN: 86/86 Vitest, 8 suites Electron (batch proof, batch, runtime batch/admission/recovery, session state/resilience, human review).
- `tsc -p apps/desktop/tsconfig.electron.json --noEmit`: exit 0.
- Chromium headless real com DOM `data:` isolado: elemento substituído selecionado => `verified:true`; duplicata de anchor => `verified:false`. Sem rede ou UI do usuário.
- `git diff --check` nos 3 arquivos de código/teste: exit 0 (avisos de CRLF existentes).

## Limites
**Não houve validação E2E do Browser runtime ativo no Electron real.** A sessão do usuário foi preservada: o runtime em memória pode continuar com a versão anterior até reinicialização/rebuild controlados. Não considerar essa execução qualificação de release, nem usar os testes para reconciliar admissões históricas. Seguimento único recomendado: com autorização para ciclo isolado, testar uma seleção `click + selected + anchor` em Electron/Chromium nativo com fixture local, verificar ACK causal e nenhuma liberação sob ambiguidade, depois conferir funcionamento na instância de uso sem afetar sessões humanas.

## Homologação nativa Electron — 2026-11-07, ciclo posterior (QUALIFICADO_LOCALMENTE)
O limite acima, que dizia que o E2E nativo não havia sido executado, foi superado nesta etapa. Foram criados dois arquivos novos:
- `apps/desktop/e2e/workstation-native-semantic-rebind.ts`: cria Hermes Browser Runtime real em Electron isolado, com owner offscreen, controle autenticado local, duas TaskRuns independentes e página HTML servida em localhost; usa o fluxo real `browser_snapshot -> browser_batch_actions -> durable admission/receipt -> next navigation`.
- `apps/desktop/e2e/workstation-native-semantic-rebind-runner.cjs`: empacota o entry com esbuild, inicia um processo Electron separado com `HERMES_HOME`, `HERMES_WORKSTATION_HOME`, browser profile, control descriptor, session ledger e Electron userData exclusivos em diretório temporário; remove os arquivos temporários na saída.

**Comando:** `cd C:\Github\hermes-agent && node apps/desktop/e2e/workstation-native-semantic-rebind-runner.cjs`

**Resultado real:** exit 0, sem timeout, sem stderr. Caso `unique`: `status=verified`, `verifiedSteps=1`, `completedSteps=1`, DOM reconstruído com um único candidato selecionado, `clickCount=1`, `acknowledged=true` persistido, `parentReceipt=true` com `action=browser_batch_actions` e IDs TaskRun corretos, navegação posterior autorizada. Caso `ambiguous`: `status=uncertain`, `reason=stale_or_replaced_target`, `completedSteps=1`, `verifiedSteps=0`, dois candidatos selecionados, `clickCount=1`, `acknowledged=false`, `parentReceipt=false`, diagnóstico persistido e navegação subsequente bloqueada. Nos dois casos `hostFocus=false`. Não houve clique repetido nem efeito externo.

**Verificação adicional:** `node --check` do runner exit 0; `git diff --check` exit 0. Processo Electron de produção PID 8940 permaneceu ativo desde 06/11 19:14; ledger real em `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json` manteve `LastWriteTime=2026-11-06T19:16:03.1133060-03:00`. Nenhuma reconciliação, reload ou reinício da sessão ativa.

**Estado final:** correção e integração Browser nativa qualificadas localmente para os cenários de seleção única e âncora ambígua. Não qualifica release/CI nem prova comportamento de Instagram/WhatsApp/ChatGPT em produção, e não faz mudanças no processo em memória do Hermes já aberto. Não é necessário abrir nova missão para esta qualificação; próximo passo apenas se o usuário quiser distribuição/restart controlado ou cenário de site específico.
