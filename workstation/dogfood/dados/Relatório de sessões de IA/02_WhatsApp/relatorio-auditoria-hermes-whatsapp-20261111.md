# Auditoria técnica — Hermes Work / “Abrir WhatsApp #6”

**Data:** 11/11/2026  
**Escopo:** sessão exportada em `abrir-whatsapp-6-20261110(2).json` (1.683 mensagens); inspeção somente leitura de arquivos, skills e código do Hermes em `C:\Github\hermes-agent`; consulta SQLite da campanha em modo `ro`.  
**Sessão:** `20261110_150343_2d106b`  
**Estado da intervenção:** somente análise. Nenhum envio realizado nem arquivo local modificado nesta auditoria.

## 1. Resumo executivo

O Hermes não falhou por incapacidade de executar JavaScript. Ele o executou repetidamente pelo `browser_console`, mas **não transformou a campanha em um trabalho determinístico, durável e retomável**. O resultado foi uma sequência extensa de decisões da LLM para ações previsíveis, esperas feitas em chamadas separadas de terminal, recarregamentos de contexto e correções humanas. A primeira prioridade não é reduzir tokens: é corrigir o registro da prova de envio no SQLite, que hoje confia em evidência textual livre.

**Síntese:** abandonar microorquestração pela LLM; reutilizar o banco de campanha e o BrowserTask nativo em um executor de campanha com checkpoints por mensagem, relógio de 60 segundos no executor, comprovantes reais e parada em casos incertos. Um arquivo `.mjs` é uma possível embalagem para esse executor, **não** uma razão técnica para acessar CDP externamente ou contornar permissões do navegador.

## 2. Medições reproduzidas do JSON

| Métrica | Observação |
|---|---:|
| Mensagens exportadas | 1.683 |
| Mensagens da função assistente | 756 |
| Mensagens do assistente com chamadas de ferramentas | 738 |
| Chamadas de ferramentas, extraídas de `assistant.tool_calls` | 796 |
| Mensagens de resultado de ferramentas | 882 — **não** equivalem a 882 chamadas distintas |
| `browser_console` | 444, 55,8% das chamadas |
| `terminal` | 206, 25,9% |
| `browser_file_upload` | 40, 5,0% |
| Outras ferramentas | 106, 13,3% |
| Compactações de contexto presentes no histórico | 26 |
| Comandos do terminal contendo alguma espera `sleep` | 86 |
| Soma dos valores solicitados em `sleep` | 2.509 segundos, aproximadamente 41 min 49 s |
| Comandos com menção a `mark_sent.py` | 49 — inclui execuções e inspeções; não significa 49 destinatários |
| Comandos terminal invocando `node` / `wa_cdp_batch.py` | 0 / 0 |
| Contadores de tokens / custo faturado no JSON | Não disponíveis (`token_count` nulo) |

A sessão abrange 10/11/2026, 15h03–21h21 (UTC-3), mas contém pausas, intervenções humanas e reinicializações. Não atribuir todo esse intervalo a processamento ininterrupto.

O texto serializado das 26 compactações soma aproximadamente **538 mil caracteres**. As respostas das três leituras de skill somam aproximadamente **64 mil caracteres**, e as respostas de ferramentas somam cerca de **1,15 milhão de caracteres** no export. São medidas de volume de contexto, **não** tokens cobrados. O volume do contexto não prova por si só a causa de todas as compactações, mas evidencia repetição e peso.

**Exemplo de um destinatário (faixa ~20h00–20h02):** a sequência inclui registro do anterior + navegação, leitura do cabeçalho, `sleep 8`, nova leitura, scripts JS separados de preparação, upload nativo, scripts separados de confirmação/envio, registro em SQLite e navegação para o próximo. Há pelo menos dez ações distribuídas em chamadas de ferramentas, sem contar todo o tratamento intermediário. É incorreto tratar “seis chamadas por pessoa” como medição exata e universal; o padrão observado é ainda mais fragmentado em algumas etapas.

## 3. Auditoria do banco: o maior risco

Consulta em modo somente leitura a `whatsapp_control.db`, campanha `2026-11-10-assembleia-agradecimento` (ID 6):

- 43 inscrições: 40 com status `contacted`, três `pending`.
- Quatro etapas oficiais (`wa_01` a `wa_04`).
- 160 registros `sent` (40 em cada etapa) e três `failed` em `wa_01`.
- Nenhuma das 163 linhas possui `bubble_id` ou `header_text` estruturados na evidência.
- As 160 linhas `sent` possuem um JSON com chave `verified` cujo valor é texto livre; três falhas possuem chave `src`.

`Controle WhatsApp/scripts/mark_sent.py` foi criado na operação. Seu funcionamento atual:

1. Lê um índice de um plano JSON.
2. Recebe a evidência como argumento de terminal — texto livre, inclusive com default.
3. Seleciona as quatro etapas do banco e, por padrão, marca **todas** como `sent`.
4. Caso haja linha anterior, pode atualizá-la para `sent` e sobrescrever a evidência; escreve `sent_at` do momento da marcação.
5. Não consulta a conversa nem exige `data-id` real da bolha ou cabeçalho extraído do browser.

A skill exigia explicitamente `bubble_id` e `header_text` após observar a mensagem no DOM. O script não aplica esse contrato. É erro de integridade de evidência. **Não significa que os envios não ocorreram.** Significa que a base não possui prova estruturada que os confirme independentemente da descrição da LLM.

**Correção:** impedir transição para `sent` sem comprovante estruturado obtido pelo controlador nativo para a combinação exata de campanha, contato, etapa, operação e conversa; evidência de preview/seleção de arquivo não é prova de envio. Manter estados `pending`, `attempted`, `uncertain`, `confirmed`, `failed_invalid` (ou os equivalentes já disponíveis) e não reexecutar efeitos incertos sem reconciliação. Auditar o legado sem reescrever retroativamente as provas.

## 4. Fricções concretas da sessão

| Severidade | Fricção constatada | Efeito ou risco | Correção objetiva |
|---|---|---|---|
| Crítica | Mensagens foram relatadas como enviadas à conversa errada; o usuário precisou identificar duplicidade/identidade incorreta | Dano real de destinatário errado | Resolver a identidade pelo destino completo e confirmar número da conversa **antes** de cada mensagem; não confiar somente no nome exibido ou nos últimos quatro dígitos |
| Crítica | `mark_sent.py` marca múltiplas etapas com evidência livre | Banco transmite certeza maior que a prova disponível | Persistência por etapa, com receipt independente e estado `uncertain` após efeito não confirmado |
| Alta | 444 `browser_console` e 206 `terminal` em um trabalho repetitivo | Custo de interação com modelo, maior chance de erro humano e context churn | Executor único com estado durável; LLM só configura e resolve exceções |
| Alta | Foto foi percebida como figurinha no período de uso do clipboard | Composição errada e necessidade de refazer | `browser_file_upload` nativo para selecionar a imagem e validação de preview de **foto** e legenda antes de clicar em Enviar |
| Alta | Scripts PowerShell de foco/clipboard e tentativas de `computer_use` | Fragilidade com janela em segundo plano; conflito com regra de não controlar mouse/teclado do usuário | Proibir automação global e remover fallback de foco das skills |
| Alta | 26 compactações; skill principal muito longa | Perda de estado local e reinterpretação da missão, além de volume de contexto | Skill curta e executável, dados de progresso somente no banco e recibos resumidos |
| Média-alta | `location.assign` e navegação por deeplink expuseram header antigo/página em transição | Risco de enviar para destinatário anterior | Wait por condição de identidade, com confirmação de destino exato antes do envio |
| Média | 86 `sleep` de shell totalizando 41min49s programados | 86 oportunidades de retornar à LLM para continuar um cronômetro | Timer durável no executor, sem chamadas ao modelo; tempo desde **último destinatário**, não um `sleep` fixo solto |
| Média | `browser_click` retorna snapshots de aproximadamente 18–25 KB em várias chamadas finais | Respostas grandes reintroduzidas no contexto do agente | Por padrão retornos compactos (`status`, `receipt`, `message_id`, `next_action`), snapshots completos apenas sob diagnóstico |
| Média | Template passou de três para quatro blocos no meio da campanha | Necessidade de reconciliação e correções parciais | Versionar/hash de template por campanha; ao alterar, executar diff por etapa e reavaliar destinatários |
| Média | Ferramenta de upload inicialmente ausente, depois descoberta e utilizada | Investigações, reinícios e fallback inadequado | Diagnóstico de capacidades no preflight; sem capacidade nativa autorizada, HOLD explícito |

## 5. Skills realmente usadas e influência causal

A exportação contém somente **três chamadas `skill_view`**:

1. `whatsapp-email-campaign-control` — corpo principal, aproximadamente 40 mil caracteres retornados.
2. `whatsapp-email-campaign-control` → `references/whatsapp-web-dom.md` — aproximadamente 16,8 mil caracteres retornados.
3. `whatsapp-email-campaign-control` → `scripts/set_clipboard_image.py` — aproximadamente 3 mil caracteres retornados.

A skill `browser-console-ui-automation` consta como relacionada à primeira, mas **não há chamada `skill_view` para ela no JSON**. Portanto, não há base para afirmar que seu corpo completo foi explicitamente carregado nessa sessão, embora o comportamento mostre uso de técnicas semelhantes. Também não há evidência suficiente no export para excluir injeções automáticas de instruções feitas fora de `skill_view`.

Arquivos locais inspecionados:

- `%LOCALAPPDATA%\hermes\skills\productivity\whatsapp-email-campaign-control\SKILL.md` — 46.941 bytes.
- `%LOCALAPPDATA%\hermes\skills\productivity\whatsapp-email-campaign-control\references\whatsapp-web-dom.md` — 21.302 bytes.
- `%LOCALAPPDATA%\hermes\skills\productivity\whatsapp-email-campaign-control\scripts\wa_cdp_batch.py` — 10.456 bytes, mas **não invocado no histórico**.
- `%LOCALAPPDATA%\hermes\skills\software-development\browser-console-ui-automation\SKILL.md` — 52.934 bytes, não explicitamente carregada na exportação.
- Referência `browser-console-ui-automation/references/whatsapp-web-batch-send.md` — 20.515 bytes, também não explicitamente carregada.

**Contradições importantes:**

- A skill de campanha recomenda `set_clipboard_image.py` + `Ctrl+V` e afirma que anexação não tem caminho de input. Isso foi superado pela ferramenta `browser_file_upload` implementada no runtime Electron.
- Ela apresenta CDP externo/porta 9222 como plano B. Isso entra em conflito com o roteamento atual: sessões Desktop ficam restritas ao BrowserTask nativo, com `browser_exec` externo bloqueado em `tools/browser_use_cli.py` e `model_tools.py`.
- A skill principal lembra corretamente a necessidade de provas, mas tolera na prática um mecanismo de `mark_sent.py` que grava texto declarativo. A implementação descumpre a instrução.
- A skill `browser-console-ui-automation` **já diz** que ações homogêneas não devem usar N ciclos de modelo e recomenda compilar loops na segunda repetição. O agente não a carregou explicitamente e não aplicou esse conselho de forma persistente. Parte do problema foi **não reutilizar a orientação correta que já existia**.
- Ambas trazem observações históricas extensas, receitas legadas e exceções como se fossem caminhos prioritários. Deve haver separação entre **padrão canônico atual** e **fallback histórico descontinuado**.

**Mudanças recomendadas nas skills:** inserir no início da skill de campanha um procedimento resumido: preflight/roster → autorização → canário → executor determinístico → receipts persistidos → relatório; substituir toda recomendação de clipboard/PowerShell/CDP externo por upload nativo e HOLD; exigir que o runner seja o responsável por pausas e por registros, jamais por um texto de LLM. Mover casos históricos longos para referências, não carregá-los integralmente em toda campanha. Referenciar diretamente o protocolo determinístico da skill `browser-console-ui-automation` quando aplicável, mas sem usar JavaScript arbitrário para transpor admission/review.

## 6. Por que a LLM não usou um `.mjs` via CDP?

**Fatos:** houve muitas injeções JavaScript — 444 chamadas `browser_console`. O que não houve foi um *executor persistente de campanha*. O histórico registra scripts Python para setup, plano e `mark_sent.py` e scripts PowerShell de foco, mas nenhuma chamada de terminal `node ...`, nenhum `wa_cdp_batch.py` e nenhum `.mjs` operacional criado.

**Interpretação mais provável:**

1. A orientação carregada induziu um roteiro operacional por contato e um fallback de clipboard.
2. O modelo passou a executar a próxima microetapa assim que obteve uma resposta, em vez de compilar a rotina já validada.
3. O runtime não oferecia ao modelo uma ferramenta de alto nível pronta para esta campanha de quatro blocos + imagem + checkpoint. Há helpers de lote (`whatsapp_batch_send`) em `tools/browser_workstation.py`, mas não estavam expostos no catálogo usado; o wrapper observado ainda contém uma referência a `persist=persist` que não aparece na assinatura do método, indicando defeito potencial a testar antes de reutilizá-lo. **Não foi invocado, para evitar qualquer envio acidental.**
4. O modelo gerou código para **cadastrar e marcar**, mas não para **executar** a máquina de estados por destinatário.

**Limites reais de uma única injeção JS:** o `browser_console` chama `webContents.executeJavaScript(expression, true)` dentro da página; uma navegação que substitua o documento pode encerrar a execução; promessas longas têm timeout no controlador; a página não deve ter acesso ao SQLite, às credenciais do host ou à autorização de anexos. `DOM.setFileInputFiles` é uma capacidade do Electron controlada por grant, não um direito de uma página arbitrária. Executar 40 contatos por uma única expressão JS também reduziria a capacidade de interromper e reconciliar uma falha no contato intermediário.

**Distinção essencial:** `.mjs` é um formato de módulo JavaScript do Node.js, **não** um formato especial de injeção CDP. Um `.mjs` confiável **fora da página** pode orquestrar a fila usando o controlador nativo autorizado, o banco de dados e um timer, respeitando cada admission/receipt. Já um CDP externo/Chrome 9222 ou `browser_exec` seria outra autoridade de navegador e não deve ser ativado para contornar o BrowserTask.

## 7. Solução mínima de arquitetura (MVP)

**Não construir outro navegador, outro banco ou uma camada de agentes.** Reutilizar `whatsapp_control.db`, `campaign_control.py`, o BrowserTask Electron e `browser_file_upload`.

1. **Corrigir a persistência:** gravar `attempted`, `selected`, `observed`, `confirmed` ou `uncertain` por destinatário e por bloco; exigir prova de bolha associada à conversa exata; remover a capacidade de `mark_sent.py` marcar `all` com texto livre não verificado. Não reescrever provas antigas como se tivessem sido recuperadas.
2. **Criar uma única operação de execução de campanha** — pode ser uma rotina Python no produto ou um `.mjs` supervisor se houver motivo de integração Node. Ela recebe apenas referências aprovadas ao roster, template versionado e TaskRun. O agente configura **uma vez** e supervisiona exceções.
3. **Para cada destinatário**, o executor lê estado do banco, abre o deeplink usando o controlador interno, verifica o número/cabeçalho do destino, executa quatro passos autorizados (incluindo seleção da imagem pelo upload nativo), obtém evidência independente da ação e grava a etapa. No caso de erro inconclusivo, bloqueia o destinatário sem repetição cega.
4. **Pausa sem LLM:** armazenar `next_allowed_at` na fila e só iniciar outro destinatário quando 60 s tiverem transcorrido a partir do ponto definido no contrato. O timer sobrevive a reinicialização e não chama o modelo.
5. **Relatório compacto:** emitir atualizações com números agregados, estados e `operation_id`, sem transmitir snapshots enormes ou PII repetidamente à LLM.

Pseudofluxo do supervisor (não é implementação):

```text
load approved_campaign_manifest()
assert browser_task_is_authorized() and template_version_is_current()
for recipient in database.pending_recipients():
    await wait_until(recipient.next_allowed_at)
    if has_uncertain_effect(recipient): STOP_AND_RECONCILE
    await native_browser.navigate_to_authorized_recipient(recipient.ref)
    assert await native_browser.verify_exact_identity(recipient.ref)
    for step in pending_steps(recipient):
        receipt = await native_browser.execute_authorized_step(step)
        evidence = await native_browser.observe_new_outbound_bubble(step, receipt)
        database.commit_step(recipient, step, evidence)
    database.set_next_allowed_at(now() + 60 seconds)
```

A implementação precisa distinguir ACK de clique, seleção de arquivo, bolha exibida e confirmação de envio. Se não houver prova suficiente, `uncertain` e decisão humana; nunca `sent` por padrão.

## 8. Validação e prioridades

**P0 — integridade e segurança, antes de qualquer novo lote:** eliminar prova livre e marcação automática de todas as etapas; conferir que identidade, upload e estados incertos interrompem o executor sem ação duplicada. Esse é o maior risco identificado.

**P1 — custo e continuidade:** demonstrar em ambiente autorizado um canário, depois dois destinatários em sequência com intervalo medido de >=60 s, a mesma sessão BrowserTask e o Hermes em segundo plano; provar que não houve LLM entre as microetapas normais.

**P2 — skills e telemetria:** reduzir e atualizar as duas skills principais e suas referências, medir `llm_turns_per_recipient`, número de ferramentas por contato, bytes de resposta, tempo de bloqueio e taxa de reconciliação. Confirmar que a skill efetivamente carregada é a correta; não inferir uso pelo simples fato de estar instalada.

**Meta técnica, não resultado medido:** um operador LLM para preparar/aprovar a campanha e outro para exceções; zero decisões da LLM por destinatário durante o caminho feliz. A economia monetária depende de medições de tokens, modelo e cache que **não aparecem no JSON**.

## 9. Evidência, limites e conclusão

**Evidência direta:** export de 1.683 mensagens, invocações de ferramentas, três `skill_view`, usuário denunciando imagem como figurinha e mensagens no contato errado, scripts locais de controle, SQLite aberto em `mode=ro`, código atual do BrowserTask e das skills locais. Nenhum dado pessoal de contato foi replicado neste relatório.

**Incertezas:** custo exato em tokens/dinheiro; intenção interna da LLM; cadeia de instruções possivelmente injetada sem `skill_view`; comprovação retrospectiva de cada bolha das 160 linhas legadas; qual parcela dos intervalos de 6h18m foi consumida em usuário/infraestrutura/reinicialização. O relatório não presume que mais automação teria evitado todos os erros sem validação.

**Conclusão:** houve desperdício de modelo por ausência de um executor de campanha persistente, agravado por skill desatualizada, descoberta tardia do upload nativo, pausas orquestradas pelo modelo e contexto excessivo. O maior defeito, porém, foi a **confiança indevida do registro de envio**. Resolver ambos com o menor escopo possível: um motor determinístico sobre o BrowserTask existente, evidência por etapa, relógio durável e skills curtas coerentes com o runtime atual.
