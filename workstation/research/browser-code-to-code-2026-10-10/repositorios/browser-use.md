# Relatório de Auditoria Code-to-Code: Família Browser-Use

**Projetos Auditados:**
1. `browser-use/browser-use` (`c75e8476e2715055b85a36399cebc5ea396a8be4`)
2. `browser-use/desktop` (`f073b7574fcf376a524733355038b30f5ecb8a1c`)
3. `browser-use/browser-harness` (`dbf0e4f3a39e992b4507ee63e7c050a498bfe1b2`)
4. `browser-use/browsercode` (`b200643fe02111d43a60a7e671d1b28751fa0ef2`)

**Licença:** **MIT** em todos os quatro repositórios  
**Stack:** Python (core `browser_use`), TypeScript / Electron / Vite (`desktop`), TypeScript (`browsercode`)  
**Tamanho Auditado:** 3.800+ arquivos TS, 450+ arquivos Python, 950+ testes  
**Classificação de Reuso:** **COPY / ADAPT** (Licença MIT compatível sem restrições)  

---

## 1. Identidade e Arquitetura

O ecossistema `browser-use` é atualmente a referência mais popular de automação de navegadores orientada a agentes em Python e Desktop. Ele divide-se em:
1. **Core Agent (`browser_use`):** Loop de raciocínio, serialização de DOM clicável e barramento de eventos orientado a sentinelas (*watchdogs*).
2. **Desktop (`browser-use/desktop`):** Aplicação Electron que gerencia ciclo de vida de janelas, sobreposição visual de intervenção humana (`takeoverOverlay.ts`) e importação direta de perfis do Google Chrome (`chrome-import`).
3. **Browsercode & Harness:** Ambientes de execução de scripts gerados e harnesses de avaliação programática.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Arquitetura Modular de Sentinelas (Watchdogs)
- **Arquivo:** `browser_use/browser/watchdogs/`
- **Símbolos:**
  - `AboutBlankWatchdog` (`aboutblank_watchdog.py`)
  - `CrashWatchdog` (`crash_watchdog.py`)
  - `PopupsWatchdog` (`popups_watchdog.py`)
  - `CaptchaWatchdog` (`captcha_watchdog.py`)
  - `SecurityWatchdog` (`security_watchdog.py`)
  - `StorageStateWatchdog` (`storage_state_watchdog.py`)
- **Mecanismo:** Cada problema operacional do navegador é isolado em uma classe ouvinte de eventos (`BaseWatchdog`) com declaração explícita de eventos que escuta (`LISTENS_TO`) e que emite (`EMITS`).
- **Resolução de Problemas Conhecidos do Hermes:**
  - O Hermes Work enfrentava o bug `BOR-003: ensure() can foreground about:blank while a task tab is pending`. O `AboutBlankWatchdog` resolve isso garantindo uma transição limpa e nunca permitindo que uma aba vazia tome o foco de uma aba de tarefa ativa.
  - O `CrashWatchdog` detecta travamento do processo de renderização do Chromium e dispara recuperação automática da página antes que o agente receba um erro de timeout.
  - O `StorageStateWatchdog` captura automaticamente cookies e localStorage a cada mutação de estado e sincroniza com o disco.

### 2.2. Importação Segura de Perfis do Usuário (`chrome-import`)
- **Arquivo:** `browser-use/desktop/app/src/main/chrome-import/`
- **Mecanismo:** Lê o banco SQLite local do perfil padrão do Google Chrome no Windows (`%LOCALAPPDATA%\Google\Chrome\User Data\Default`), descriptografa cookies de sessão via API DPAPI do Windows e importa credenciais de sessão para o perfil do Electron.
- **Superioridade sobre Hermes Work:** No Hermes Work, o usuário é forçado a fazer login manualmente em todos os sites (WhatsApp, Trello, Instagram) dentro do navegador do Electron, ou usar a extensão. O `chrome-import` do `browser-use/desktop` permite herdar a sessão autenticada do usuário com um clique.

### 2.3. Overlay de Intervenção Humana (`takeoverOverlay.ts`)
- **Arquivo:** `browser-use/desktop/app/src/main/takeoverOverlay.ts`
- **Mecanismo:** Ao clicar para interagir, uma borda visual iluminada e um badge flutuante ("User in control") são renderizados sobre o WebContentsView, com cancelamento imediato de eventos pendentes do agente.

---

## 3. Mapa de Correspondência com o Hermes Work

| Mecanismo | browser-use | Hermes Work | Veredito |
|---|---|---|---|
| Tratamento de `about:blank` e Crash | `AboutBlankWatchdog` e `CrashWatchdog` | Lógica ad-hoc em `workstation-browser-runtime.ts` | **browser-use superior** (Modular e desacoplado) |
| Importação de Sessão do Chrome | Módulo `chrome-import` completo (DPAPI) | Não existe; usuário loga do zero | **browser-use superior** |
| Visual de Intervenção Humana | `takeoverOverlay.ts` + `pill.ts` | Barra estática no painel de abas | **browser-use superior** |
| Throttling e Performance de Fundo | Básico | `DEFAULT_BACKGROUND_FRAME_RATE = 6` e WebContentsView pooling | **Hermes superior** |
| Verificação Operacional e Aprendizado | Inexistente (agente pensa a cada passo) | `OperationalKernel` e `ExperienceCompiler` | **Hermes exclusivo e superior** |

---

## 4. Análise de Licença e Requisitos de Portabilidade

- **Licença:** **MIT License** em todos os submódulos do `browser-use`.
- **Compatibilidade:** 100% compatível com a licença MIT do Hermes Agent.
- **Portabilidade:** Código Python (`watchdogs`) e código TypeScript (`takeoverOverlay`, `chrome-import`) podem ser adaptados diretamente sem nenhum risco jurídico.

---

## 5. Recomendações Objetivas para o Hermes Work

1. **Adotar a arquitetura de Watchdogs no Python e Electron (`ADAPT`):**
   Refatorar os tratamentos de `about:blank`, crash e persistência de storage do `workstation-browser-runtime.ts` para seguir o padrão `BaseWatchdog` do `browser-use`.
2. **Portar o módulo de importação de sessão `chrome-import` (`COPY`):**
   Adicionar a `apps/desktop/electron/chrome-import/` a rotina de leitura de cookies autenticados do Chrome local, eliminando o atrito de autenticação no Trello e redes sociais.
3. **Adicionar Pill e Takeover Overlay na UI do Electron (`ADAPT`):**
   Melhorar o feedback visual do Hermes Work durante o controle humano através dos componentes de overlay testados do `browser-use/desktop`.
