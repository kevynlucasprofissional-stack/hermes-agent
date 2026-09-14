# Hermes Workstation — Inteligência Operacional

> Fonte consolidada de conhecimento duradouro sobre a arquitetura, o funcionamento real e os limites do Hermes Workstation.
> Este documento complementa ARCHITECTURE.md, CURRENT_STATE.md, DECISIONS.md, CONSTRAINTS.md, TESTING.md e ROADMAP.md.
> Em caso de divergência, o código e os testes do main são a fonte da implementação; os documentos de arquitetura são a fonte das invariantes.

## 1. Modelo mental

Hermes Workstation é uma camada de produto integrada ao Hermes Agent. Não é um segundo agente, nem um segundo sistema de sessões, tarefas ou memória.

| Estado/capacidade | Owner canônico |
|---|---|
| Conversas, sessões e continuidade | Hermes SessionDB |
| Cards, estados, eventos, runs e notificações | Kanban Hermes (hermes_cli.kanban_db) |
| Memória persistente | Hermes Memory |
| Página viva e identidade de automação | BrowserTask + runtime escolhido |
| Cookies, localStorage, IndexedDB e cache | Sessão Electron/Chromium persistente |
| Evidências e sequência operacional | Execution Journal |
| Segurança/autonomia | ScopedPolicyEngine |
| Projeções para clientes | Workstation Controller / contratos versionados |

Workstation acrescenta orquestração, projeções e adaptadores; não cria cópias desses owners.

Fluxo canônico:

    chat request
      -> Hermes SessionDB / gateway
      -> detectar trabalho multietapas
      -> criar card no Kanban canônico
      -> vincular session_id, run_id e kanban_card_id
      -> selecionar BrowserRuntime
      -> criar ou recuperar BrowserTask
      -> executar com política e evidência
      -> descobrir follow-ups
      -> completar/bloquear/reabrir o card
      -> reportar no chat de origem

## 2. Limites entre processos

### 2.1 Hermes Agent e Gateway

O Gateway é entrada e entrega. CLI, Telegram, Discord, Slack, WhatsApp, Signal e outros canais podem iniciar ou acompanhar uma sessão, mas não passam a ser donos do estado de trabalho.

WorkstationKanbanBridge.promote_request_if_multistep usa kanban_db.connect(board=...), cria o card no banco canônico, preserva session_id, inicia ExecutionJournal e registra TASK_CREATED. A heurística atual reconhece termos de workflow/multietapas e prompts com múltiplas linhas. É uma heurística de entrada, não prova de planejamento correto.

### 2.2 Workstation Controller

O controlador do navegador é HTTP local, preso ao loopback e protegido por bearer token. O runtime grava um arquivo de controle privado com URL/porta, token e metadados de versão.

Propriedades observadas:

- não expor em LAN por padrão;
- autenticar cada requisição com Authorization: Bearer <token>;
- limitar o corpo da requisição;
- validar session_id, task_id, kanban_card_id e run_id;
- rejeitar strings vazias, caracteres de controle e identidades excessivamente longas;
- remover o arquivo apenas quando ele ainda pertence ao processo/token que o criou;
- responder JSON sem cache.

Payload lógico:

    {
      "action": "…",
      "arguments": {},
      "session_id": "…",
      "task_id": "…",
      "kanban_card_id": "…",
      "run_id": "…"
    }

As projeções read-only /resources e /events são consumidas por Dashboard REST, TUI JSON-RPC, IPC Desktop e clientes futuros. Nenhum cliente deve reconstruir uma versão própria da verdade.

### 2.3 Desktop Electron

O Desktop hospeda Chromium por WebContentsView e sessão Electron dedicada. A janela humana e workers compartilham um pool de páginas, mas não uma página sem ownership explícito.

A runtime implementa navegação, tabs, foco, ocultação, parking, controle humano/agente, downloads, percepção, BrowserTask, restauração estrutural e projeções. Chat Browser View e Browser Hub podem trocar o host visual por transferência de viewport; isso não cria uma nova página ou tarefa.

## 3. Identidade, sessão e lifecycle

BrowserTask é a identidade durável do trabalho web, não um banco de tarefas.

    create -> navigate -> hide/park -> re-expose -> explicit destroy
                                                                             -> process restart -> restore/recover

Invariantes:

1. task vinculado não troca silenciosamente de runtime;
2. esconder/estacionar não destrói a página;
3. reexibir preserva identidade e evita navegação de substituição;
4. destroy explícito remove a página e não cria substituta automática;
5. após restart, a estrutura lógica pode ser restaurada lazy; a instância renderer não é persistida;
6. recuperação cria no máximo uma página por task;
7. task estacionado não rouba a tab ativa de outra tarefa ou do humano.

BrowserSessionState persiste somente metadados estruturais seguros: tabs lógicas, ordem, tab ativa, estado de recuperação, IDs e vínculos. Não substitui o perfil Chromium. Cookies, localStorage, IndexedDB, cache e autenticação compatível permanecem no perfil Electron isolado.

O perfil é dedicado ao Workstation e fica fora do checkout. Não reutilizar perfil pessoal do Chrome/Edge. Isso reduz vazamento de cookies, interferência de extensões e ambiguidades de recuperação.

## 4. Política e segurança

Toda ação privilegiada é avaliada pelo ScopedPolicyEngine, com decisões ALLOW, SANDBOX, REQUIRE_APPROVAL ou DENY. A decisão deve ser auditável e carregar capability, ação, alvo, tarefa/sessão e resultado. Ausência do controller, identidade incompatível, capability não resolvida ou política indisponível deve falhar fechado.

Limites observados:

- navegação de alto nível aceita http, https e about:blank;
- URLs de metadata/cloud-internal e endereços sensíveis são bloqueados;
- comandos destrutivos, credenciais, cookies, arquivos sensíveis e ações irreversíveis exigem avaliação;
- aprovação humana não pode ser simulada pelo agente;
- fallback de browser não pode ocorrer depois de vincular BrowserTask;
- logs e projeções não devem conter tokens, cookies ou segredos do renderer.

## 5. Extensões Chrome

### 5.1 Implementação existente

workstation/extensions.py contém ChromeExtensionManager, que fornece:

- diretório ~/.hermes/workstation/extensions (ou home configurado);
- validação de IDs de 32 caracteres;
- download pelo endpoint oficial clients2.google.com/service/update2/crx;
- localização do payload ZIP de CRX2/CRX3 pela assinatura Cr24;
- unpack e leitura de manifest.json;
- registry extensions.json;
- instalação por bytes para fixtures offline;
- instalação por ID/URL;
- listagem, remoção e resolução da página de opções.

No Electron, loadInstalledExtensions percorre diretórios, verifica manifest.json e chama browserSession.loadExtension(extPath, { allowFileAccess: true }) na inicialização.

### 5.2 Limite real

Esse caminho não prova autonomia completa. Ainda é necessário demonstrar o pipeline:

    agent intent
      -> extension requirement resolver
      -> policy/approval
      -> install
      -> load na sessão correta
      -> verify
      -> use
      -> journal

Antes de classificar a feature como completa, devem existir capability/tool explícita, inspeção de manifest, decisão ScopedPolicyEngine, aprovação humana para permissões sensíveis, lineage de session/task/run, confirmação positiva de load, persistência após restart e journal de required/policy/download/install/load/verify/use/failure.

Diretório extraído não é capability carregada.

A triagem inicial de risco pode usar:

| Sinal no manifest | Risco esperado |
|---|---|
| storage, activeTab | baixo, condicionado ao alvo |
| tabs, downloads, clipboard | médio |
| cookies, webRequest, <all_urls>, nativeMessaging | alto/crítico |

Essa tabela é triagem, não autorização. Host permissions, páginas autenticadas, credenciais e combinações de permissões podem elevar o risco. Em dúvida, exigir approval ou negar.

## 6. Kanban e tarefas descobertas

O Kanban oficial continua sendo a única fonte de verdade. WorkstationKanbanBridge apenas orquestra a API existente.

DiscoveredTask exige title, parent_task_id, discovered_by, reason e origin_session_id; pode carregar evidence, task_id após persistência e required_for_parent.

record_discovered_followup:

1. valida a estrutura;
2. cria o filho com parents=[parent_task_id];
3. mantém a sessão de origem;
4. inclui razão e agente descobridor no corpo;
5. bloqueia o pai quando o filho é obrigatório;
6. preenche followup.task_id;
7. registra FOLLOWUP_CREATED com evidência e metadados no journal.

A evidência deve explicar a descoberta. Exemplo: durante OAuth, verificar que refresh tokens não são persistidos deve originar uma tarefa filha específica.

Estados visuais como backlog, ready, active, waiting-for-human, blocked, background, done e failed devem ser projeções dos estados/transições existentes em kanban_db, não uma nova tabela. O scheduler mantém one-live-host, leases, heartbeats e reap de órfãos. Tarefas independentes podem continuar enquanto outra aguarda humano.

complete_task_with_report transforma BrowserTaskReport em metadata canônica, chama kanban_db.complete_task e registra TASK_COMPLETED com resultado, evidência e sites. O chat de origem é resolvido por session/run/card lineage, não por título.

## 7. Execution Journal

O journal é append-only, por tarefa, em JSONL. ExecutionJournal.record aceita tipo, mensagem, URL, RiskLevel, evidências, metadata e browser_tab_id.

Eventos existentes incluem TASK_CREATED, TASK_STARTED, BROWSER_ATTACHED, NAVIGATION, ACTION, APPROVAL_REQUESTED, APPROVAL_RESOLVED, FOLLOWUP_CREATED, ERROR, TASK_COMPLETED, RECOVERY e LIFECYCLE.

Para extensões, reutilizar a taxonomia existente ou adicionar eventos compatíveis: EXTENSION_REQUIRED, EXTENSION_POLICY_CHECK, EXTENSION_APPROVED/DENIED, EXTENSION_DOWNLOAD_STARTED, EXTENSION_INSTALLED, EXTENSION_LOADED, EXTENSION_VERIFIED, EXTENSION_USED e EXTENSION_FAILED.

Journal explica decisões e evidências; não é task database.

## 8. Percepção e navegação

O inventário é compacto e limitado por orçamento: URL, título, texto truncado e elementos interativos com refs, tags, roles, labels, valores e disabled. A implementação percorre shadow roots e tenta iframes acessíveis.

Um clique emitido não prova conclusão. A regra é:

    hypothesis -> action -> verify final state -> report evidence

Não usar Preview, navegador externo ou página paralela para declarar sucesso de operação exigida no Workstation Browser. URLs são normalizadas e destinos não permitidos devem ser rejeitados.

## 9. Persistência e recovery

Há três classes de persistência:

1. canonical state: SessionDB, Kanban, Memory e Journal;
2. browser-managed state: perfil Electron/Chromium;
3. structural runtime state: BrowserSessionState, BrowserTask e metadata do controller.

Após restart, o novo processo rejeita identidade/control file de outro processo; sessões e cards permanecem canônicos; tabs lógicas e tasks recuperáveis são restaurados; páginas são recriadas lazy; a primeira exposição cria exatamente uma página por task; falhas de escrita convergem; destroy explícito não gera recuperação fantasma.

Arquivos são escritos atomicamente e privados quando possível. No Windows, EPERM/EBUSY têm fallback controlado para cópia, sem tomar posse de arquivos de outro processo.

## 10. Evidência de testes

Não confundir classes de evidência:

- unitários Python provam CRX, manifest, Kanban, journal, policy e contratos;
- runtime/mock prova lifecycle, controller e failure paths;
- typecheck/build prova compilação;
- smoke nativo Electron prova janela real, WebContentsView, ownership e renderer;
- restart de dois processos prova isolamento, persistência e recovery;
- E2E prova Desktop/Chat/Hub/IPC;
- soak prova reconnect, workers, heartbeat, scheduler e limites.

Evidências já observadas:

- H004: identidade BrowserTask, hide/park, destroy explícito e recovery real;
- H010: restart abrupto em dois processos, separação de perfil, recovery lazy e convergência de escrita;
- H011: episódios do runtime nativo, navegação e persistência composta;
- H012: reconnect/heartbeat do backend headless, sem provar qualidade de provider;
- H013: Desktop/Browser, IPC/controller, viewport, eventos/recursos e cleanup;
- estado documentado registra 175/175 testes Python e typecheck Desktop limpo no working tree correspondente.

Mock nunca deve ser apresentado como prova de restart nativo, load real de extensão ou identidade de página.

## 11. Anti-patterns

Não criar segundo SessionDB, Kanban, Memory, page store ou browser control plane. Não armazenar tarefa no BrowserTask nem evidência no Kanban. Não sincronizar duas páginas por URL. Não tratar toggle UI como capability persistida. Não instalar extensão sem policy, approval e manifest inspection. Não tratar unpack como load/verification. Não fazer fallback silencioso após binding. Não usar perfil pessoal. Não revelar tokens, cookies ou secrets. Não declarar conclusão sem verificar estado final. Não substituir Workstation Browser por Preview. Não confundir close-tab com destroyTask. Não apagar testes para acomodar documentação. Não promover Completed sem evidência executável.

## 12. Checklist de mudança

Antes: identificar owner, ler regras/contexto/journal, localizar código e testes e registrar hipótese quando houver incerteza.

Durante: menor mudança vertical completa, fail-closed, lineage session/task/run/card, evidências e nenhuma persistência duplicada.

Depois: testes focados, typecheck, smoke adequado à alegação, revisão de diff/secrets, atualização de CURRENT_STATE/ROADMAP/journal e classificação rigorosa como Completed, Partial, Experimental ou Hardening remaining.

## 13. Estado conhecido

No main observado, BrowserSessionState, BrowserTask, Browser Hub/Chat Browser View, controller loopback, scheduler, journal, follow-ups, policy e projeções existem em diferentes níveis de maturidade. Instalação local e restore de extensões no boot existem. Autonomia completa de extensões — resolver, policy/approval, load confirmado, verify, use e journal — deve permanecer Partial / hardening remaining até ser demonstrada por código e testes. Release, soak e clean-machine continuam gates de evidência.

Este documento é memória técnica, não autorização para ampliar escopo. Toda promoção de capacidade deve obedecer aos owners canônicos e às evidências do SHA exato.
