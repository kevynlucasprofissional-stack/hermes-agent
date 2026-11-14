# Auditoria aprofundada do WhatsApp Web nativo do Hermes

**Data da auditoria:** 12/11/2026  
**Escopo:** sessões reais do Hermes, auditorias técnicas históricas, banco SQLite da campanha de 10/11, skill de campanhas e código atual de browser/WhatsApp.  
**Método:** leitura somente; nenhuma mensagem enviada, nenhuma alteração no repositório, banco ou navegador; nenhum teste funcional de disparo executado nesta auditoria.

## 1. Decisão técnica

O gargalo dominante é a **microorquestração de uma campanha repetitiva pela LLM**, não a pausa exigida de 60 segundos. Isso torna a tarefa vulnerável a limites do modelo, compactações de contexto, disponibilidade de ferramentas, mudança de foco, troca involuntária de conversa, reinicialização e recuperações demoradas.

O problema de maior risco é distinto do desempenho: **o histórico da campanha contém registros `sent` sem prova estruturada e individual de envio**. Não é correto afirmar que as mensagens não foram enviadas; tampouco é correto afirmar, apenas com a base, que cada envio foi verificado.

**Menor solução viável:** concluir um executor **multietapa com anexos** sobre o BrowserTask Electron e o SQLite já existentes, com aprovação humana de *manifesto completo* emitida pelo host, verificação de identidade e recibos por etapa, pausa durável e parada segura em incerteza. A LLM prepara, recebe o resumo e administra exceções; não executa cada microação.

**Estado atual:** a arquitetura já contém boa parte das primitivas. O envio individual tem fluxo de aprovação humana implementado no código e regressões relatadas, mas falta prova real de um envio a terceiro na sessão atual. O batch existente é **text-only**, a autorização de campanha ainda está em HOLD e o fluxo de quatro etapas com imagem/legenda não está homologado.

## 2. Cobertura, amostra e limitações

Foram inventariados e analisados automaticamente **88 JSON de sessões do Hermes** em `C:\Github\hermes-agent\workstation\dogfood\dados\Sessões Hermes`, com **22.804 mensagens** e **10.528 chamadas de ferramentas**. O aprofundamento concentrou-se nos **19 exports da pasta `01-WhatsApp-e-Campanhas`**: **18 IDs de sessão distintos** (dois arquivos compartilham o mesmo ID), **6.533 mensagens** e **2.854 chamadas de ferramentas**. Também foram lidos/examinados **10 relatórios em `Relatório de sessões de IA\02_WhatsApp`**, a documentação relacionada de browser/integrações e os componentes atuais do runtime, wrappers, batch, skill e SQLite. Os demais 69 exports, não classificados como WhatsApp, entraram na varredura estrutural, não em uma revisão manual de cada mensagem.

Os números de chamadas vêm de `assistant.tool_calls`. As mensagens de resultado `role=tool` não são chamadas distintas. Ocorrências textuais de erros nas respostas das ferramentas são **indicadores**, não uma contagem auditada de incidentes independentes. Os exports não contêm faturamento confiável de tokens ou um log completo de eventuais limitações de provedor exibidas fora da sessão.

**Nenhuma nova campanha foi executada; portanto nenhuma melhoria de performance foi comprovada nesta auditoria.** Os resultados de testes citados nos arquivos de projeto são registros históricos, não uma nova execução independente dos testes.

## 3. Campanha de 40 destinatários: reconstrução factual

**Fonte primária:** `Sessões Hermes\01-WhatsApp-e-Campanhas\abrir-whatsapp-6-20261110.json` (sessão `20261110_150343_2d106b`, 1.683 mensagens). **Fonte secundária:** `Relatório de sessões de IA\02_WhatsApp\relatorio-auditoria-hermes-whatsapp-20261111.md`.

| Medida | Valor comprovado | Interpretação |
|---|---:|---|
| Duração do arquivo da sessão | cerca de **377 min (6h17)** | Inclui abertura do WhatsApp e intervalos anteriores ao pedido da campanha |
| Primeiro pedido explícito de campanha | **16:12:54, 10/11** | Pedido de 60 segundos entre alvos |
| Fim da sessão | aproximadamente **21:21, 10/11** | A campanha percorreu cerca de 5h08 de relógio, com interferências e paradas |
| Chamadas de ferramentas | **796** | Custo de orquestração elevado |
| `browser_console` | **444** | **55,8%** das chamadas |
| `terminal` | **206** | **25,9%** das chamadas |
| `browser_file_upload` | **40** | 40 operações de upload não equivalem a 40 mídias com entrega verificada |
| Outras chamadas | **106** | Navegação, snapshots, arquivos etc. |
| Compactações de contexto | **26** | Reconstituição de contexto durante a execução |
| Comandos de terminal com `sleep` | **86** | Esperas fragmentadas |
| Soma das durações pedidas em `sleep` | **2.509 s (41min49s)** | Soma de durações programadas, não medida independente de tempo efetivamente aguardado |

### Cronologia de incidentes observáveis

- **16:12:** pedido inicial de campanha, com 60 segundos entre destinatários.
- **16:41:** o usuário acrescenta a terceira mensagem e pede recuperar destinatários que já haviam recebido o template anterior. O template foi alterado no meio da execução, exigindo um diff individual por etapa.
- **17:02:** o usuário questiona a perda de foco do navegador; a operação precisou ser retomada.
- **18:13–18:20:** reinício e retomada. O usuário identifica uma imagem enviada como **figurinha**, não como foto com texto; a seleção de tipo de mídia estava incorreta.
- **18:48:** o usuário relata mensagens de dois alvos direcionadas a uma conversa diferente, causando duplicidade. A falha tem impacto real superior a qualquer ganho de latência.
- **19:49–20:48:** novos pedidos para continuar/reabrir o WhatsApp, evidenciando perda de continuidade.
- **21:12:** correção humana de identidade/contato salvo com nome diferente.

Não é tecnicamente correto subtrair a soma dos `sleep` da duração da sessão e classificar o resto como tempo desperdiçado: há lacunas, esperas de ferramentas, pausas humanas, atualização de template e reinícios. Por exemplo, há um intervalo de cerca de **69 min antes do pedido da campanha** e outro de cerca de **56 min entre mensagens próximas de 17:04 e 18:00**. O tempo de execução da campanha não é igual ao tempo total do JSON.

### Estado persistido da campanha (consultado diretamente, somente leitura)

Banco: `C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle redes sociais\Whatsapp\Controle WhatsApp\whatsapp_control.db` (campanha `2026-11-10-assembleia-agradecimento`, ID 6).

| Situação | Quantidade |
|---|---:|
| Inscrições | **43** |
| `contacted` | **40** |
| `pending` | **3** |
| Etapas oficiais | **4** (`wa_01`–`wa_04`) |
| Linhas `sent` | **160** (40 por etapa) |
| Linhas `failed` | **3** na `wa_01` |
| Linhas com `bubble_id`/`message_data_id` estruturado | **0 de 163** |
| Evidência dos `sent` | **160 JSON com chave `verified` em texto livre** |

**Leitura correta:** o banco registra 40 contatos como abordados, mas não oferece identificador de bolha por etapa para auditoria independente desses 160 registros. Corrigir o algoritmo não legitima retroativamente a prova antiga. O antigo `scripts/mark_sent.py` foi **desativado em 11/11**, mediante `raise SystemExit`, preservando o legado em arquivo separado. Assim, a vulnerabilidade de escrita livre já recebeu uma contenção; falta garantir que as novas vias de persistência jamais repitam o problema.

## 4. Falhas recorrentes na amostra WhatsApp

Nos 19 exports da categoria WhatsApp (18 sessões distintas), **14** usaram `browser_console`, **12** usaram `terminal`, **14** carregaram alguma skill. A amostra registra **1.029 chamadas ao console** e **910 ao terminal**. Esses números agregam também uma sessão longa de desenvolvimento de banco e não devem ser interpretados como custo exclusivamente de envio.

Na varredura dos resultados de ferramentas relacionadas ao browser, houve **34 menções a `reconciliation_required` em 6 exports** e **24 menções a `timed out` em 8 exports**. São contagens lexicais sujeitas a repetição e contexto; não são 34 deadlocks nem 24 timeouts distintos comprovados.

### F1 — Microdecisões da LLM e reconstrução de estado (prioridade P0 de performance)

**Evidência:** 444 `browser_console`, 206 `terminal`, 26 compactações e 86 sleeps no caso de 40 contatos. O agente reexecutou uma receita previsível e emitiu comandos do relógio por vários turnos. O problema já aparecia em sessões anteriores (por exemplo, 142 chamadas na sessão de agradecimento de 21/10, 287 na solicitação de Raphael de 24/09).

**Correção:** executor nativo persistente por contato/etapa; LLM apenas em configuração, autorização e exceções. Payloads compactos de status, sem devolver snapshots completos a cada passo.

### F2 — Destinatário incorreto/duplicado (prioridade P0 de integridade)

**Evidência:** relato humano explícito às 18:48 de 10/11; o uso de deeplinks e a troca de conversa exibiram estados antigos durante a navegação. Outro caso de 23/10 mostrou dificuldade com telefone E.164 mascarado na saída do modelo, apesar de os dados completos existirem na fonte.

**Correção:** resolver identidade completa no host via `recipient_ref` e fonte confiável, comparar com identidade real da conversa após cada navegação e antes de cada clique, vincular o recibo à conversa/etapa e bloquear qualquer ambiguidade. Não entregar telefone completo à LLM nem reconstruí-lo de dígitos mascarados.

### F3 — Foto enviada como figurinha; anexo sem certificado (P0 quando há mídia)

**Evidência:** intervenção de 10/11 às 18:20; uso posterior de `browser_file_upload` nativo. Seleção de arquivo e preview são estados intermediários, não prova de publicação.

**Correção:** escolher explicitamente input de foto/documento, conferir tipo do preview e legenda e só depois enviar. Confirmar bolha nova de mídia com ID único e vínculo correto; não usar clipboard, `Ctrl+V`, `SendKeys` ou foco global.

### F4 — Reconciliação e referências DOM efêmeras (P1 residual; P0 se reproduzir)

**Evidência histórica:** auditoria do evento de 19/10 constatou `stale_or_unknown_ref` seguido de `reconciliation_required` por admissão de mutação pré-dispatch não encerrada, bloqueando inventário em 17/52 conversas. O WhatsApp virtualiza a lista; `@eN` não sobrevive necessariamente a scroll, atualização ou navegação. Houve tentativas de fallback `browser_exec` incompatíveis com o perfil Electron.

**Estado atual verificado:** `workstation-browser-runtime.ts` já normaliza `stale_or_unknown_ref` e contém lógica de `NOT_DISPATCHED`/reconciliação. `browser_inventory_unread` já consta de documentação de implementação. Não tratar a correção histórica como ausente sem regressão nova. Validar efeitos e recuperação no Chromium real, não apenas fixtures.

### F5 — Autoridade de TaskRun e ciclos interrompidos (P1)

**Evidência:** sessão de 24/09 encerrou com `stale_task_run`, e a ferramenta perdeu autorização após limite de iterações; outros exports terminaram com operação interrompida/sem confirmação. Mudanças de foco e histórico reaberto também produziram transições frágeis.

**Correção:** o executor precisa operar com TaskRun/BrowserTask/operation_id estáveis, apresentar estado verificável ao reiniciar e não tentar um segundo envio quando não se sabe o resultado do primeiro. Um worker durável evita que cada pausa de 60 s consuma uma interação da IA.

### F6 — Skills e caminhos conflitantes (P1)

**Evidência histórica:** skills extensas recomendavam clipboard/Chrome 9222 mesmo depois da existência do upload nativo. Na campanha de 10/11 somente três chamadas `skill_view` carregaram conteúdo, sem prova de que a skill alternativa de batching tenha sido consultada.

**Estado atual:** skill `whatsapp-email-campaign-control` v1.13.0 já foi reduzida a 48 linhas e explicitamente proíbe CDP externo, `browser_exec`, clipboard e bypass. Não há justificativa para reescrevê-la novamente. Falta demonstrar que o Hermes efetivamente a carrega e usa as ferramentas nativas em um TaskRun real.

### F7 — Preparação de campanha mutável (P1)

**Evidência:** inclusão de `wa_03` no meio da execução em 10/11; contatos anteriores precisavam apenas da nova etapa enquanto os seguintes precisavam das quatro. Fluxos sem versionamento e ledger por etapa exigiram correção humana e são propensos a repetição.

**Correção:** manifesto versionado/hash de conteúdo; comparação por contato e `step_code`; aprovação renovada somente para o diff de destino/template; retomada por etapa pendente, nunca reenvio global.

### F8 — Limites/quotas apresentados ao usuário (diagnóstico pendente)

Os exports sustentam compactações e interrupções, mas **não permitem confirmar quantas vezes o provedor do modelo ou o WhatsApp dispararam um limite real**, nem sua contribuição em minutos. Referências textuais a "rate limit" em código, instruções e payloads não são prova de `429` operacional. É imprescindível separar `MODEL_RATE_LIMIT`, `MODEL_CONTEXT_COMPACTION`, `BROWSER_TIMEOUT`, `WHATSAPP_THROTTLE`, `AUTHORITY_HOLD`, `USER_PAUSE` e `NETWORK_ERROR`, com timestamps de início e fim. Não contornar controles da plataforma; em throttling, aplicar backoff e suspender/reconciliar quando exigido.

## 5. O que já existe e o que ainda falta em 12/11

| Componente | Estado inspecionado | Lacuna material |
|---|---|---|
| Browser Electron nativo | Existe e dispõe de navegação, snapshot, inspect e upload. Normalização de stale ref/`NOT_DISPATCHED` presente | Homologar recuperação real sob WhatsApp virtualizado |
| `browser_wait_for_ready` | Já implementado em `tools/browser_workstation.py`; auditoria anterior mediu overhead de apenas ~60 ms em caso controlado | Não é o principal gargalo; não reimplementá-lo |
| `whatsapp_find_contacts` | Tool Desktop read-only, retorna referências sem telefone | Exige resolução unívoca e fonte confiável |
| `whatsapp_send_message` | Tool Desktop para texto individual, exige TaskRun e aprovação humana `once` do host | Aprovação e envio a contato terceiro **ainda sem homologação real**; `OBSERVED` não equivale a confirmação independente do servidor |
| `whatsapp_batch_preview` | Tool Desktop read-only | Não autoriza nem inicia lote |
| `whatsapp_batch_executor.py` | Checkpoints, `next_allowed_at` durável, estados `uncertain`, validação de recibo; opera **um texto por item** | Não executa quatro blocos + foto/legenda; batch sem autorização de host |
| `whatsapp_batch_approve` | Retorna intencionalmente `HUMAN_APPROVAL_ATTESTATION_REQUIRED` | Emissor de aprovação humana por manifesto ainda não integrado |
| `whatsapp_send_attachment` | Helper de anexo existe | Não integrado ao lote com recibos por etapa e autorização forte |
| `mark_sent.py` legado | Desativado em 11/11 | 160 `sent` históricos continuam sem prova estruturada |
| Skill de campanha | Atualizada para v1.13.0, curta e alinhada ao BrowserTask | Provar uso real na sessão sem fallback antigo |

**Defeito pontual encontrado no código atual:** `tools/browser_workstation.py::whatsapp_batch_control` passa `persist=persist` no ramo `resume`, mas não declara variável/parâmetro `persist` nesse escopo. Isso deve produzir `NameError` se o ramo for alcançado. É um defeito específico de retomada; não é o maior bloqueio, porque a liberação operacional de campanha está atualmente em HOLD. Corrigir antes de validar restart/resume.

O relatório de projeto `workstation/context/WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md` e o plano `WA_OPC011_HERMES_REAL_TEST_20261112.md` registram testes sintéticos **218 PASS / 0 FAIL** e um caminho de aprovação individual. Não executei novamente esses testes nesta auditoria. A documentação também afirma explicitamente que não houve novo envio a terceiros homologado e que a campanha completa permanece em HOLD.

## 6. Arquitetura mínima recomendada

```text
LLM/Hermes — intenção e configuração
    │
    ▼
Leitura e prévia da campanha [fonte trusted, sem mutation]
    │
    ▼
Manifesto imutável: destinatários + 4 steps + hash + anexos
    │
    ▼
Aprovação humana REAL do manifesto no host Desktop
    │
    ▼
Executor do BrowserTask nativo, com owner TaskRun
    ├─ retoma SQLite: pending/uncertain/confirmed por etapa
    ├─ aguarda next_allowed_at sem chamar a LLM
    ├─ navega para contato / verifica identidade completa
    ├─ executa texto e/ou foto+legenda por step autorizado
    ├─ observa o efeito e persiste recibo causal por step
    ├─ se incerto → HOLD + reconciliação; nunca reenvio cego
    └─ define next_allowed_at para o próximo destinatário
    │
    ▼
Resumo de progresso e exceções para Hermes/usuário
```

**Reaproveitar, não duplicar:** `whatsapp_control.db`, `workstation/integrations/hermes/whatsapp_batch_executor.py`, `whatsapp_browser_executor.py`, `whatsapp_native_send_bridge.py`, `whatsapp_human_approval.py`, `tools/browser_workstation.py`, `tools/browser_tool.py`, o BrowserTask e o mecanismo de `OperationalCapability`/Prefabs. Não criar daemon externo que use CDP 9222, segundo perfil Chrome, novas bases divergentes ou scripts de clique global.

**Estados:** `pending`, `sending`, `observed`, `confirmed` (somente com nível de evidência comprovado), `uncertain`, `failed_invalid`, `skipped`/`opted_out`; preservar estados existentes com mapeamento explícito. Cada operação deve ter `campaign_id`, `contact_id`, `step_code`, `template_hash`, `run_id`, `operation_id`, evidência de chat e tempo. `OBSERVED` na interface não pode ser relatado como `CONFIRMED` pelo servidor.

**Aprovação:** não exigir 160 cliques humanos de aprovação por etapa. O usuário pode aprovar **uma única vez o manifesto exato** com 40 destinatários e conteúdo integral, desde que o host certifique o grant, aceite scope/validade e permita auditoria/cancelamento. Alteração de nome, telefone, template, etapa ou anexo após a aprovação invalida ou suspende a parcela afetada. Uma aprovação no prompt não é emissão de autorização técnica.

## 7. Meta de duração: o que pode e o que não pode ser garantido

Para 40 destinatários e uma pausa **entre** destinatários, há **39 intervalos**. Só o tempo mínimo de espera corresponde a `39 × 60 s = 2.340 s = 39 min`. O restante é a soma da latência dos 40 contatos, prévia/abertura, verificação, quatro etapas e anexo.

**Modelo de capacidade:**

`T_total ≈ 39 min + Σ(tempo_de_envio_e_verificação_por_contato) + overhead_de_preparo + recuperação_externa`

- Média de **10 segundos por contato** → aproximadamente **45min40s**, antes do preparo.
- Média de **15 segundos por contato** → aproximadamente **49min**, antes do preparo.
- Média de **25 segundos por contato** → aproximadamente **55min40s**, antes do preparo.

Portanto, a meta de **~45–50 minutos**, num cenário normal de conexão e contatos válidos, é um **objetivo mensurável**, não um SLA comprovado. A exigência de 60 segundos pode significar a pausa após concluir A e antes de iniciar B (interpretação mais segura); não alterá-la silenciosamente para um mero intervalo entre inícios de contato. Não é possível garantir limite absoluto perante indisponibilidade do WhatsApp, mudanças de DOM, revogação de autorização, problemas de rede, limites legítimos do serviço ou necessidade de reconciliação de efeitos incertos. Em erro relevante, a prioridade é não enviar à pessoa errada nem duplicar, mesmo que o prazo seja ultrapassado.

A principal economia vem de **eliminar chamadas à LLM no caminho feliz** e reutilizar o mesmo navegador, não de reduzir os 60 segundos solicitados.

## 8. Backlog enxuto, em ordem de impacto

| Ordem | Mudança mínima | Risco resolvido | Aceite necessário |
|---|---|---|---|
| **0** | Concluir o teste individual WA-OPC-011 no Hermes real, com aprovação host `once` e contato consentido | Prova que o caminho nativo de envio e receipt funciona fora dos mocks | Um envio controlado, identidade correta, no máximo 1 clique, log estruturado; `OBSERVED` relatado sem inflar certeza |
| **1** | Integrar autorização humana de **manifesto** e executor multietapa/mídia sobre o batch existente | Remove centenas de microações, preserva identidade e conteúdo | Dois destinatários reais autorizados; quatro etapas/foto corretas por contato; prova por etapa; zero loops da LLM entre passos |
| **2** | Cooldown persistente configurado em 60s e recuperação de processo/TaskRun com política de incerteza | Evita sleeps da LLM, repetição e perda de estado | 60s reais entre A e B; restart seguro; nenhum reenvio de estado `sending/uncertain`; corrigir `persist` indefinido |
| **3** | Executar lote-canário de 5 e, depois, 40 consentidos com telemetria enxuta | Comprova throughput e estabilidade de ponta a ponta | Medir duração total, por contato/step, ferramenta/modelo, erros, HOLDs e custo; confirmar que nenhuma identidade errada ou mídia incorreta foi enviada |

**Não priorizar agora:** reescrever `browser_wait_for_ready`, criar novo browser, migrar banco, usar CDP externo, implementar mais agentes, redesenhar toda a UI ou refatorar componentes sem falha comprovada.

## 9. Critérios de aceite para 40 contatos

1. **Segurança e identidade:** 40 contatos exclusivamente de uma lista aprovada, sem destinatário errado, sem duplicata e com opt-out respeitado. Toda mudança de destino/template após aprovação exige nova decisão, não inferência.
2. **Integridade:** cada uma das quatro etapas e da mídia tem prova por operação e destinatário; nenhum `sent` baseado em texto livre da LLM. Falha ambígua produz `uncertain` e bloqueia repetição até reconciliação.
3. **Autonomia real:** após um preflight e aprovação do lote, o executor conduz a sequência com `next_allowed_at` no banco; a LLM não executa `sleep` nem 5–10 microações por contato. O controle funciona com a janela em segundo plano sem teclado/mouse global.
4. **Performance:** medir 39 pausas efetivas de 60s e tempo total do lote. Objetivo operacional **45–50 min** sob condições normais; exceções legítimas são classificadas com duração e causa, não escondidas. Não chamar `40/40` confirmado se qualquer etapa estiver apenas `OBSERVED`/`UNCERTAIN`.

## 10. Evidências e trilha de revisão

**Dados operacionais:**

- `C:\Github\hermes-agent\workstation\dogfood\dados\Sessões Hermes\01-WhatsApp-e-Campanhas\abrir-whatsapp-6-20261110.json` — sessão completa de 10/11.
- `...\01-WhatsApp-e-Campanhas\enviar-5-mensagens-whatsapp-para-leads-20261109.json` — fallback para `browser_exec`/Chrome externo, apesar do pedido de navegador interno.
- `...\01-WhatsApp-e-Campanhas\enviar-mensagem-de-agradecimento-pelo-whatsapp-20261021.json` — execução anterior fragmentada.
- `...\01-WhatsApp-e-Campanhas\atender-pedido-de-raphael-valongo-no-whatsapp-20260924.json` — `stale_task_run` após excesso de iterações.
- `...\01-WhatsApp-e-Campanhas\criar-banco-de-dados-para-controle-do-whatsapp-20261022.json` — operações longas e hit-testing problemático.
- `C:\Github\hermes-agent\workstation\dogfood\dados\Relatório de sessões de IA\02_WhatsApp\relatorio-auditoria-hermes-whatsapp-20261111.md` — auditoria quantitativa anterior.
- `...\02_WhatsApp\Auditoria Forense da Falha na Automação do WhatsApp (Hermes Work).md` — deadlock histórico, virtualização DOM.
- Demais **8 relatórios** em `...\02_WhatsApp`, além de documentos selecionados em `...\01_Browser` e `Contexto Hermes\07-WhatsApp-Integracoes`.

**Código e estado atual:**

- `C:\Github\hermes-agent\tools\browser_tool.py` (registro do catálogo Desktop, linhas ~1766–1936).
- `C:\Github\hermes-agent\tools\browser_workstation.py` (sender/batch/controle, ~1847–2418).
- `C:\Github\hermes-agent\workstation\integrations\hermes\whatsapp_batch_executor.py` (~69–1075).
- `C:\Github\hermes-agent\workstation\integrations\hermes\whatsapp_browser_executor.py` (~556–762 e ~1193–1460).
- `C:\Github\hermes-agent\apps\desktop\electron\workstation-browser-runtime.ts` (~370 e ~3117–3216).
- `%LOCALAPPDATA%\hermes\skills\productivity\whatsapp-email-campaign-control\SKILL.md` (versão 1.13.0).
- `C:\Github\hermes-agent\workstation\context\WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md`.
- `C:\Github\hermes-agent\workstation\context\WA_OPC011_HERMES_REAL_TEST_20261112.md` — canário individual já preparado, ainda não executado por esta auditoria.
- `C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle redes sociais\Whatsapp\Controle WhatsApp\whatsapp_control.db` — consulta SQL read-only em 12/11.
- `...\Controle WhatsApp\scripts\mark_sent.py` — execução legada bloqueada.

**Repositório:** `C:\Github\hermes-agent` em `main`, HEAD `f1d5ab2f03` no momento da inspeção, com centenas de alterações locais pré-existentes. Nenhuma foi alterada por esta auditoria.

## Conclusão

A campanha de 40 contatos não falhou por exigir um minuto de pausa: falhou em **separar decisão de IA de execução determinística** e em **assegurar destinatário, efeito e prova por etapa**. O histórico já motivou correções reais (skill, desativação de script, recuperação de admissão e primitivas de envio). A melhor relação entre risco e ganho agora é **homologar um único envio individual**, ligar **aprovação de lote + quatro etapas/mídia ao executor persistente já criado** e medir o fluxo completo com 2, 5 e 40 destinatários reais consentidos. Até essas provas, desempenho de 45–50 minutos permanece uma meta, não uma entrega validada.
