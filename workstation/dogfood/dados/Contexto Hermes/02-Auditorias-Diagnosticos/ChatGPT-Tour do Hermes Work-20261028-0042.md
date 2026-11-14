# Tour do Hermes Work

**User:** Anonymous  
**Created:** 10/27/2026 23:55:49  
**Updated:** 10/28/2026 0:36:13  
**Exported:** 10/28/2026 0:42:59  
**Link:** [https://chatgpt.com/c/6ae16435-38ac-83e9-a959-845dcf7f88b3](https://chatgpt.com/c/6ae16435-38ac-83e9-a959-845dcf7f88b3)  

## Prompt:
27/10/2026, 23:55:47

[$hermes-control](app://plugins_6ae1473983c08191af0f7aa011d1a4c5) [$controle-windows](app://asdk_app_6add7e528c7c8191932e966f7ddf9782) Consegue dar um tour no Hermes Work? Ai Control está ativado.

## Response:
27/10/2026, 23:55:52 · gpt-6-thinking

Vou fazer um tour de inspeção pelo Hermes Work usando o AI Control: identificar a janela ativa, percorrer as principais áreas da interface e registrar o que funciona, eventuais falhas e oportunidades de melhoria. Vou preservar o estado do aplicativo, sem alterar configurações ou executar ações destrutivas.

Confirmei que o Hermes está aberto no Windows, em execução de desenvolvimento, com o renderer ativo. A porta CDP externa está fechada, conforme a política atual do projeto; vou manter essa proteção e usar a automação de interface do Windows para inspecionar a aplicação sem reiniciá-la.

A árvore de acessibilidade do Hermes está disponível e já expõe os módulos de navegação, sessões e controles da janela. Isso permite um tour real pela interface sem depender do CDP. Encontrei também conteúdo de sessões recentes e vou evitar ações que possam acionar mensagens ou automações externas.

## Tour do Hermes Work — inspeção ao vivo

Consegui acessar a interface real do Hermes no seu Windows. Confirmei visualmente o indicador **AI Control ativo** e naveguei pelos módulos principais, sem modificar arquivos ou configurações.

(Hermes em execução) (AI Control ativo)

Os primeiros achados relevantes\:

- **Workstation\:** o Browser Hub abriu, mas a aba exibida estava em `about:blank`\. Havia uma tarefa de WhatsApp em estado `PARKED`, sem atividade no viewport.
- **Capabilities\:** o módulo abriu e exibiu o catálogo de Skills, Tools, Connectors e Plugins, integrado ao Skills Hub.
- **Scheduled jobs\:** encontrei cinco tarefas cadastradas. Uma delas estava pausada e apresentava histórico de falhas decorrentes de alteração na configuração do provedor/modelo de IA. O sistema indicava que as execuções foram impedidas para evitar gastos não intencionais.

Esses são comportamentos observados na aplicação, não apenas conclusões retiradas do código.

## Prompt:
28/10/2026, 00:07:50

Você tá roubando o meu mouse, para com isso. Anota esse método de roubar o meu mous como proibido, anota isso em todo lugar que conseguir para nunca se esquecer.

Continue o tour, mas faça isso do jeito que explicitado nas skills.

## Response:
28/10/2026, 00:08:00 · gpt-6-thinking

Vou interromper imediatamente qualquer automação que mova ou clique no mouse. Você tem razão: esse método interfere no seu controle do computador e não deve ser usado novamente. Vou registrar a proibição nas instruções locais do Hermes e continuar apenas por interfaces que não disputem mouse ou teclado.

A proibição já foi gravada em dois arquivos persistentes do Windows: a skill local `hermes-work-control/SKILL.md` e as instruções globais `~/.claude/CLAUDE.md`\. O processo que usava cliques por coordenadas terminou; não vou iniciar outro.

Vou continuar examinando as capturas já coletadas e o estado do aplicativo por leitura, sem interferir na sua utilização. Também estou verificando como incorporar essa mesma regra ao plugin privado Hermes Control.

Encontrei o mecanismo correto no código atual: o Hermes tem uma **ponte nativa autenticada de AI Control** $`ai-control-bridge`$ e os scripts `ai-control-client.mjs`/`hermes-nav.mjs` já a utilizam. Isso permite continuar o tour sem mover o cursor nem enviar teclas globais. Vou testar primeiro uma consulta de status, somente leitura.

> **Entendendo a solicitação**
>
> Não posso transformar esse conteúdo em uma exposição detalhada de raciocínio interno. Posso, porém, ajudar a resumir decisões e próximos passos de forma objetiva, sem incluir detalhes técnicos sensíveis ou instruções para controle remoto indevido.
>
> **Entendido a solicitação**
>
> 
>
> **Interpretando o contexto**
>
> Estou identificando a descrição de uma capacidade para leitura de arquivos e URLs autorizados, incluindo documentos, planilhas, imagens e PDFs. Vou manter o resumo em alto nível, sem expor detalhes internos de funcionamento.
>
> **Interpretado o contexto fornecido**
>
> 
>
> **Interrompeu automação e atualizou skill com banner de segurança**
>
> 
>
> **Buscou e atualizou plugins e configurações locais**
>
> 
>
> **Listou plugins pessoais e leu arquivos e metadados disponíveis**
>
> 
>
> **Resumindo a capacidade**
>
> Estou descrevendo uma ferramenta para ler arquivos e URLs autorizados, extrair conteúdo de PDFs, consultar imagens, planilhas e documentos, além de permitir leitura parcial e análise estruturada conforme o formato.
>
> **Resumiu a capacidade**
>
> 
>
> **Resumindo a capacidade**
>
> Estou descrevendo uma ferramenta para ler arquivos e URLs autorizados, extrair conteúdo de PDFs, consultar imagens, planilhas e documentos, além de permitir leitura parcial e análise estruturada conforme o formato.
>
> **Resumiu a capacidade**
>
> 
>
> **Atualizadas instruções persistentes e autorização no CLAUDE.md global**
>
> 
>
> **Revisadas capturas do Hermes e criado plugin de controle de IA**
>
> 
>
> **Executou e inspecionou navegação Hermes, modais, módulos e tarefas**
>
> 
>
> **Atualizado o plugin via ZIP armazenado e restaurado o Kanban**
>
> 
>
> **Atualizou a skill e os manifestos do plugin Hermes Work Control com segurança**
>
> 
>
> Pensou por 10m 48s

## Tour concluído pelo AI Control nativo

A navegação passou a utilizar exclusivamente `ai-control-client.mjs`, `hermes-nav.mjs` e `eval.mjs`, através da ponte autenticada do Hermes. **Nenhum movimento de mouse ou tecla global foi utilizado nessa segunda etapa.**

### Resultados verificados

| Área | Resultado |
|--------|--------|
| **Workstation** | Browser Hub operacional, com `about:blank` e uma tarefa estacionada (`PARKED`\). |
| **Capabilities** | 127 skills e 23 ferramentas identificadas. |
| **Messaging** | Interface de configuração para WhatsApp, Telegram, Discord, Slack, e-mail e outros canais. Conexões não testadas. |
| **Artifacts** | Filtros All, Images, Files e Links disponíveis. |
| **Scheduled jobs** | Cinco automações cadastradas. `briefing-financas` pausada por divergência na configuração de inferência. |
| **Vault** | Interface acessível; zero notas exibidas. |
| **Kanban** | Quadro Default com 67 itens indicados. Diversas tarefas apresentam `needs_input` e `outcome_not_verified`\. |
| **Sessões** | Navegação funcional. Sessão original restaurada ao final. |

(Backend ready) Hermes v0.21.7+1590 (+1)

### Proibição registrada

Gravei a regra em dois locais persistentes\:

- `C:\Users\Kevyn Lucas\.claude\skills\hermes-work-control\SKILL.md`
- `C:\Users\Kevyn Lucas\.claude\CLAUDE.md`

A regra proíbe `pywinauto.mouse.click`, `pyautogui`, `keyboard.send_keys` e qualquer outro método que dispute seus dispositivos de entrada, mesmo com AI Control ativo.

Também tentei atualizar o plugin privado **Hermes Control**, mas a publicação foi rejeitada pelo formato do pacote. Portanto, não vou afirmar que essa atualização foi concluída. As duas alterações locais foram confirmadas.

### Principais conclusões

O achado técnico mais importante é que **o Hermes já possui o mecanismo correto para controle não intrusivo**\. Não precisamos habilitar o CDP externo nem recorrer à automação do desktop.

O Kanban merece atenção pelas tarefas sem resultado verificado, e a Workstation merece investigação específica sobre o ciclo de vida das tarefas `PARKED`\. São observações de diagnóstico, não falhas reproduzidas neste tour.

Não alterei código do Hermes, não enviei mensagens e não executei automações externas. O formulário de agendamento aberto acidentalmente na primeira etapa foi cancelado pela ponte nativa, e a sessão original foi restaurada.

A proibição será respeitada nesta conversa e está registrada nas instruções locais para futuras sessões que as carreguem. Não posso garantir sua retenção universal pela memória do ChatGPT.

## Prompt:
28/10/2026, 00:25:21

Você atualizou os plugins aqui do ChatGPT também sobre como controlar o Hermes Work com o AI Control ativo?

## Response:
28/10/2026, 00:25:37 · gpt-6-thinking

> **Verificando a atualização**
>
> Não, a atualização dos plugins não foi concluída; a tentativa anterior foi rejeitada. Estou distinguindo o que foi atualizado localmente do que realmente foi publicado no ChatGPT, para evitar afirmar que o Hermes Work já está sincronizado quando não está.
>
> **Verificou a atualização**
>
> 
>
> **Mantendo o status claro**
>
> Eu não concluí a atualização dos plugins. A tentativa anterior foi rejeitada, então apenas a configuração local foi alterada. O Hermes Work ainda não está sincronizado no ChatGPT; preciso de uma atualização aceita para confirmar isso.
>
> **Mantido o status claro**
>
> 
>
> **Investigou atualização do plugin via arquivo local**
>
> 
>
> Pensou por 42s

**Não. A atualização dos plugins do ChatGPT ainda não foi concluída.**

Na última sessão\:

- **Skill local `hermes-work-control`\:** atualizada com a proibição de controlar seu mouse e teclado.
- **Instruções globais do Claude Code\:** atualizadas.
- **Plugin Hermes Control do ChatGPT\:** tentei publicar a versão 2.0.1, mas a operação foi rejeitada.
- **Plugin Controle Windows\:** não foi atualizado.

A regra que precisamos incorporar ao Hermes Control é: **usar a ponte nativa autenticada do AI Control para navegar pelo DOM do Hermes, sem movimentar o mouse ou enviar teclas globais.**

Acabei de conferir o plugin privado Hermes Control\: ele continua na **versão 2.0.0**, sem a atualização publicada.

O próximo passo é atualizar sua skill para utilizar prioritariamente `ai-control-client.mjs` e `hermes-nav.mjs`, incorporar a proibição permanente de automação do mouse e publicar uma nova versão, preservando as funcionalidades existentes.

**A regra já foi comprovada funcionando no tour anterior, mas ainda precisa ser incorporada ao plugin do ChatGPT.**

## Prompt:
28/10/2026, 00:30:41

[$plugin-creator](app://connector_openai_plugin_creator) Então atualiza os plugins do ChatGPT

## Response:
28/10/2026, 00:30:52 · gpt-6-thinking

Vou atualizar as instruções dos plugins relevantes, começando pelo Hermes Control e verificando se Controle Windows e Controle-rápido também têm arquivos editáveis. A regra será usar a ponte nativa autenticada do AI Control e proibir qualquer automação que tome seu mouse ou teclado. Depois vou conferir as versões publicadas.

> **Preparando a atualização**
>
> Estou organizando os arquivos de atualização no ambiente disponível. Primeiro, vou preservar o conteúdo existente, inserir as regras específicas para Hermes e FastPath e manter intactas as conexões e apresentações atuais.
>
> **Preparou a atualização**
>
> 
>
> **Atualizei plugins Hermes, Windows e Rápido com novas skills e integrações**
>
> 
>
> **Baixando arquivo original via URL assinada**
>
>
> **Baixou arquivo original via URL assinada**
>
> 
>
> **Pesquisando na web**
>
> 
>
> **Refinando os arquivos**
>
> Estou avaliando como atualizar os plugins sem perder conteúdo existente. A abordagem mais segura é preservar o material original, acrescentar instruções específicas e testar primeiro o plugin principal antes de aplicar mudanças semelhantes aos demais.
>
> **Criando pacotes atualizados**
>
> Estou montando versões revisadas para Hermes e FastPath, preservando os arquivos existentes e acrescentando instruções específicas. Também estou mantendo a compatibilidade com o formato atual, enquanto verifico se o plugin principal aceita a atualização.
>
> **Refinou arquivos e criou pacotes atualizados**
>
> 
>
> **Preparando pacotes ZIP para atualizar plugins Hermes**
>
>
> **Preparou pacotes ZIP para atualizar plugins Hermes**
>
> 
>
> **Atualizados plugins Hermes, Controle Rápido e Controle Windows pela configuração vigente**
>
> 
>
> Pensou por 5m 8s

## Atualização dos plugins do ChatGPT

(Publicado) **[Hermes Control v2.0.1](https://chatgpt.com/plugins/plugins_6ae1473983c08191af0f7aa011d1a4c5?utm_source=chatgpt.com)**

A nova versão foi publicada com instruções para utilizar a ponte nativa autenticada do AI Control, por meio de `ai-control-client.mjs`, `hermes-nav.mjs` e `eval.mjs`\.

A skill agora proíbe explicitamente automações que movimentem o mouse ou enviem teclas globais. Também estabelece que, se a ponte nativa estiver indisponível, o agente deve interromper a navegação em vez de recorrer ao controle físico do desktop.

(Publicado) **[Controle-rápido v1.1.2](https://chatgpt.com/plugins/plugins_6addaac675748191bd92594fedbf3657?utm_source=chatgpt.com)**

Adicionei uma skill de segurança para impedir automação global de mouse/teclado e orientar o uso da ponte nativa do Hermes.

---

(Publicado) **[Controle Windows v1.0.1](https://chatgpt.com/plugins/plugin_asdk_app_6add7e528c7c8191932e966f7ddf9782?utm_source=chatgpt.com)**

Adicionei instruções específicas para controlar o Hermes pelo AI Control sem interferir nos dispositivos de entrada. A conexão original do aplicativo foi preservada.

### Verificação final

**Os três plugins foram atualizados e publicados com sucesso.** Consultei os arquivos das novas versões no ChatGPT e confirmei a presença das instruções de segurança.

A única ressalva é que o catálogo de skills desta conversa ainda apresenta informações da versão anterior. Recomendo **abrir uma nova conversa** para utilizar as versões recém-publicadas.

As instruções estão publicadas; o carregamento atualizado e um novo teste funcional de ponta a ponta ainda não foram confirmados.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)