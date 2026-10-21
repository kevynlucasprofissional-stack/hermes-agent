# RELATÓRIO TÉCNICO INTEGRAL DE SESSÃO — HERMES WORK DOGFOODING CONTÍNUO

## 0. Identificação e Cobertura da Sessão

|Campo|Valor|
|---|---|
|**Tema principal**|Implementação de ciclo contínuo de dogfooding automatizado para Hermes Work (Electron Desktop)|
|**Repositório**|`C:\Github\hermes-agent`|
|**Sub-projeto**|`apps/desktop` (Electron + Vite + Python backend via `hermes serve`)|
|**Objetivo geral**|Permitir desenvolvimento com duas telas simultâneas (Hermes aberto + Claude Code), com HMR, controle CDP da UI e coordenação IA/Humano|
|**Período**|Outubro 2026 (sessão única com múltiplos ciclos de planejamento + implementação)|
|**Ambiente**|Windows (paths `C:\Github\...` e `C:\Users\Kevyn Lucas\...`), Node 22, Vitest 4.1.10|
|**Fontes examinadas**|Histórico completo da conversa (incluindo `contexto-anterior.txt` anexado), outputs de ferramentas (shell, fs_open_file, fs_write_file, fs_edit_file)|
|**Limitações**|Não houve inspeção em tempo real do runtime (Hermes rodando); testes E2E não foram executados — apenas unitários do badge. Não há evidência de commit/push.|
|**Grau de confiança**|**ALTO** para artefatos criados/editados (evidência direta das ferramentas). **MÉDIO** para comportamento runtime (não verificado em sessão).|

---

## 1. Sumário Executivo

O usuário propôs transformar o fluxo de desenvolvimento do Hermes Work em um ciclo contínuo de dogfooding com duas telas: Hermes Desktop à esquerda (produto em execução) e Claude Code à direita (modificando/testando). Após três ciclos de planejamento que mapearam a arquitetura real do projeto (HMR limitado ao renderer, CDP ativo em dev na porta 9222, `BrowserControlLeaseManager` restrito a abas internas), foi implementado o MVP do Ciclo 1 com sucesso: badge de controle IA, documentação, testes unitários (4/4 passando) e integração no shell principal. Posteriormente, três ajustes finais foram feitos: (1) o launcher `START-HERMES-WORKSTATION.bat` foi ajustado via `workstation/start.ps1` para habilitar CDP por padrão (anteriormente desativava); (2) a skill `/hermes-work-control` foi criada no diretório do usuário; (3) o `CLAUDE.md` foi atualizado para referenciar a skill. **Falta executar os testes E2E reais** (o usuário pediu um prompt de continuação para isso, mas a sessão foi interrompida para auditoria).

---

## 2. Objetivos, Requisitos e Evolução do Escopo

### 2.1 Objetivo original (Request 1)

- Estabelecer duas telas simultâneas: Hermes aberto (esquerda) + IA modificando código (direita).
- Permitir alterações sem fechar o app (HMR quando possível).
- Permitir que a IA **controle diretamente a UI do Hermes** via automação.
- Separar claramente ações IA vs humano para evitar conflitos.
- Princípio 80/20: evitar infraestrutura desnecessária.

### 2.2 Requisitos derivados dos Ciclos de Planejamento (Request 2)

- **CA-11 a CA-15** (Ciclo 3): reconexão pós-restart validada, contrato wrapper CDP, protocolo coordenação, observabilidade, especificação pronta.
- **Incremento A**: validar ambiente dev (Vite 5174, CDP 9222, eval.mjs, HMR, reconexão).
- **Incremento B**: `AiControlBadge.tsx` com flag `window.__hermesAiControlActive`, toggle `Ctrl+Shift+A`, polling 500ms.
- **Incremento C**: `AI-CONTROL-GUIDE.md` com exemplos de leitura/escrita e limitações.

### 2.3 Escopo final (Requests 3-5)

- Confirmar se o launcher `.bat` habilita CDP automaticamente.
- Confirmar instrução explícita no `CLAUDE.md` local.
- Transformar o guia em skill carregável automaticamente.

### 2.4 Mudanças de escopo

- **Rejeitado**: reutilizar `BrowserControlLeaseManager` (Ciclo 2 refutou — escopo é browser interno, não UI do app).
- **Rejeitado**: criar MCP server / HTTP wrapper para CDP no MVP (80/20 favoreceu `eval.mjs` direto via shell).
- **Rejeitado**: screenshot nativo via CDP (postergado; `preview_screenshot` do Browser pane supre necessidade visual).
- **Adiado**: hot-reload para main/preload/backend (não existe no projeto; requer restart).

---

## 3. Linha do Tempo Técnica da Sessão

### Fase 1 — Planejamento Ciclos 1-3 (anterior ao recorte visível)

- **Contexto**: Usuário pediu investigação de viabilidade.
- **Operações**: Múltiplas leituras de `main.ts`, `dev-cdp.ts`, `backend-*.ts`, `browser_session.py`, `tools/browser_cdp_tool.py`, `vite.config.ts`, `bundle-electron-main.mjs`, `gateway-reconnect.ts`, `use-gateway-boot.ts`.
- **Descobertas principais**:
    - HMR só cobre renderer (`src/`); main/preload via esbuild bundle sem watch.
    - CDP ativo em dev via `--remote-debugging-port=9222` (`dev-cdp.ts`).
    - `BrowserControlLeaseManager` é exclusivo para `workstation/browser_session.py` (DESTRUCTIVE_ACTIONS não cobre UI do app).
    - Reconexão automática implementada em `gateway-reconnect.ts` (handler `restart-followthrough`) e orquestrada por `use-gateway-boot.ts`.
    - `eval.mjs` já é funcional e conecta ao CDP.
- **Estado**: Prompt de transição para implementação gerado.

### Fase 2 — Implementação do Ciclo 1

- **Contexto**: Usuário colou o prompt de implementação com 3 incrementos.
- **Operações**:
    1. Mapeamento da estrutura do shell (tentativa de glob timeout, fallback para `ls` + `find`).
    2. Localização do root layout: `apps/desktop/src/app/contrib/controller.tsx` (não `app-shell.tsx` como no prompt original).
    3. Criação de 4 arquivos + 1 teste.
    4. Execução do vitest: **4/4 testes passando**.
- **Estado**: Incremento B e C completos; Incremento A requer validação manual interativa.

### Fase 3 — Ajustes finais (Request 4)

- **Contexto**: Usuário pediu 3 verificações específicas.
- **Operações**:
    1. Leitura de `START-HERMES-WORKSTATION.bat` → chama `workstation/scripts/oneclick_bootstrap.ps1` → chama `workstation/start.ps1`.
    2. Leitura de `start.ps1` → identificou que por padrão definia `HERMES_DESKTOP_CDP_PORT = "off"` (bloqueio).
    3. Inspeção da estrutura de skills em `C:\Users\Kevyn Lucas\.claude\skills\`.
    4. Criação da skill `hermes-work-control`.
    5. Edição de `start.ps1` para habilitar CDP=9222 por padrão.
    6. Edição de `CLAUDE.md` para listar `/hermes-work-control` nas skills permanentes.
- **Estado**: 3/3 pedidos atendidos com evidência de ferramenta.

### Fase 4 — Pedido de prompt de continuação (Request 5) e Auditoria

- **Contexto**: Usuário pediu prompt para testes E2E, depois invocou `/anthropic-skills:sr`.
- **Operações**: Relatório de auditoria gerado e entregue.
- **Estado**: Pedido de prompt E2E permaneceu aberto quando a auditoria foi invocada.

---

## 4. Descobertas Técnicas e Conhecimento Adquirido

### D-01 — Arquitetura de camadas do Hermes Desktop

- **Contexto**: Validar limites de hot-reload.
- **Evidência**: `bundle-electron-main.mjs:66-88` mostra build one-shot via esbuild sem watch; `dev-cdp.ts` habilita CDP só em dev.
- **Explicação**: Renderer via Vite (HMR funcional) / Main+Preload via esbuild bundle (restart obrigatório) / Backend Python via `hermes serve` (recycle só em code-skew 503).
- **Consequência**: MVP não pode prometer hot-reload total; apenas renderer.
- **Confiança**: **Confirmado**.

### D-02 — `BrowserControlLeaseManager` não serve para UI do app

- **Contexto**: Ciclo 2 tentou reutilizar o lease existente.
- **Evidência**: `workstation/browser_session.py:112-198` mostra que o lease protege `DESTRUCTIVE_ACTIONS` de browser tasks internas, não UI do app.
- **Explicação**: Escopos distintos: workstation browser = abas de navegação de sites; UI app = renderer Electron próprio.
- **Consequência**: Necessária coordenação leve própria (flag global + atalho).
- **Confiança**: **Confirmado**.

### D-03 — Reconexão automática robusta

- **Contexto**: CA-11 — validar recuperação pós-restart.
- **Evidência**: `gateway-reconnect.ts` com handler `restart-followthrough` + `use-gateway-boot.ts:1202` registrando via `registerGatewayReconnect`.
- **Explicação**: Socket frequentemente sobrevive ao restart do messaging gateway; handler sonda antes de fechar.
- **Consequência**: MVP pode confiar em reconexão automática sem intervenção.
- **Confiança**: **Confirmado em código; não validado em runtime**.

### D-04 — Launcher workstation desabilitava CDP por padrão

- **Contexto**: Request 4, item 1.
- **Evidência**: `workstation/start.ps1` tinha bloco `if (-not $env:HERMES_DESKTOP_CDP_PORT) { $env:HERMES_DESKTOP_CDP_PORT = "off" }`.
- **Explicação**: Motivo original documentado: evitar colisão com Chrome/Browser tooling/stale process.
- **Consequência**: Sem ajuste, `eval.mjs` falharia silenciosamente em `START-HERMES-WORKSTATION.bat`.
- **Confiança**: **Confirmado e corrigido**.

### D-05 — Root layout não é `app-shell.tsx`

- **Contexto**: Prompt original indicava `apps/desktop/src/app/shell/app-shell.tsx`.
- **Evidência**: `ls` + `find` mostraram que esse arquivo não existe; `apps/desktop/src/app/index.tsx` exporta `ContribController` de `./contrib`.
- **Explicação**: Arquitetura baseada em contribuições (`apps/desktop/src/app/contrib/controller.tsx`).
- **Consequência**: Badge montado em `controller.tsx` após `<Butterbar />` e `<TermsButterbar />`.
- **Confiança**: **Confirmado**.

### D-06 — `CLAUDE.md` não existia na raiz

- **Contexto**: Verificação pré-implementação.
- **Evidência**: `test -f C:/Github/hermes-agent/CLAUDE.md` retornou `CLAUDE_MD_NOT_FOUND`.
- **Consequência**: Arquivo criado do zero com seção "AI Control & Dogfooding" + lista de skills permanentes.
- **Confiança**: **Confirmado**.

---

## 5. Decisões Técnicas e Arquiteturais

### D-01 — Rejeitar `BrowserControlLeaseManager` para UI do app

- **Problema**: Coordenação IA/Humano na UI.
- **Solução**: Flag global `window.__hermesAiControlActive` + atalho `Ctrl+Shift+A` + badge.
- **Justificativa**: LeaseManager é thread-safe Python com fence tokens — overkill para flag booleana cooperativa.
- **Alternativas rejeitadas**: Reutilizar lease (escopo errado), criar novo lease manager (over-engineering).
- **Estado**: **Definitiva**.

### D-02 — Usar `eval.mjs` direto via shell (sem wrapper MCP/HTTP)

- **Problema**: Contrato do wrapper CDP.
- **Solução**: Claude Code invoca `node apps/desktop/scripts/eval.mjs "<expr>"` via `Bash`.
- **Justificativa**: 80/20 — `eval.mjs` já é funcional, conecta ao CDP, retorna JSON.
- **Trade-off**: Sem screenshot nativo, sem wait-for-selector, sem error handling estruturado — postergados.
- **Estado**: **Definitiva para MVP; revisitável em Ciclo 2**.

### D-03 — Polling de 500ms no badge (simplicidade > reatividade)

- **Problema**: Como o badge detecta mudanças na flag.
- **Solução**: `setInterval` a cada 500ms lendo `window.__hermesAiControlActive`.
- **Justificativa**: Evita criar observable store / IPC para uma flag cooperativa.
- **Estado**: **Definitiva**.

### D-04 — Habilitar CDP por padrão no launcher workstation

- **Problema**: `start.ps1` desativava CDP (`= "off"`).
- **Solução**: Editar para `$env:HERMES_DESKTOP_CDP_PORT = "9222"` quando não definido.
- **Justificativa**: Sem isso, todo o fluxo de dogfooding falharia silenciosamente no launcher oficial.
- **Risco**: Colisão com outro processo em 9222. Mitigação: usuário pode exportar `=off` explicitamente.
- **Estado**: **Definitiva**.

### D-05 — Skill em diretório do usuário, não do repositório

- **Problema**: Onde criar `hermes-work-control`.
- **Solução**: `C:\Users\Kevyn Lucas\.claude\skills\hermes-work-control\SKILL.md`.
- **Justificativa**: `.claude/skills/` não existe no repositório; skills do usuário já vivem em `~/.claude/skills/`.
- **Estado**: **Definitiva**.

---

## 6. Inventário de Alterações no Código, Configuração e Infraestrutura

### 6.1 Arquivos criados

|Caminho|Operação|Descrição|Evidência|
|---|---|---|---|
|`apps/desktop/src/app/shell/AiControlBadge.tsx`|Criado|Componente React com polling 500ms + listener `Ctrl+Shift+A` + badge "🤖 AI Control"|`File created successfully` (toolu_1792552030356_1)|
|`apps/desktop/src/app/shell/AiControlBadge.test.tsx`|Criado|4 testes Vitest (render oculto, render visível, toggle, partial shortcut)|`File created successfully` (toolu_1792552073676_3)|
|`apps/desktop/docs/AI-CONTROL-GUIDE.md`|Criado|Documentação com base command, exemplos leitura/escrita, regra coordenação, limitações|`File created successfully` (toolu_1792552047021_2)|
|`CLAUDE.md` (raiz)|Criado|Seção "AI Control & Dogfooding" + referência ao guia|`File created successfully` (toolu_1792552067064_2)|
|`C:\Users\Kevyn Lucas\.claude\skills\hermes-work-control\SKILL.md`|Criado|Skill completa com frontmatter, when-to-use, prereqs, exemplos, limitações|`File created successfully` (toolu_1792552966153_1)|

### 6.2 Arquivos modificados

|Caminho|Operação|Antes|Depois|Evidência|
|---|---|---|---|---|
|`apps/desktop/src/app/contrib/controller.tsx`|Edit (import)|`import { SessionDraftTitle } from '@/app/chat/session-draft-title'`|Adicionado `import { AiControlBadge } from '@/app/shell/AiControlBadge'` antes|`updated successfully` (toolu_1792552060295_1)|
|`apps/desktop/src/app/contrib/controller.tsx`|Edit (render)|`<Butterbar /><TermsButterbar />{statusbarVisible && <WiredPane part="statusbar" />}`|Adicionado `<AiControlBadge />` após|`updated successfully` (toolu_1792552048591_3)|
|`workstation/start.ps1`|Edit|`$env:HERMES_DESKTOP_CDP_PORT = "off"`|`$env:HERMES_DESKTOP_CDP_PORT = "9222"` + lógica invertida de `$WorkstationDisabledRendererCdp`|`updated successfully` (toolu_1792553011626_1)|
|`CLAUDE.md`|Edit|Lista de skills permanentes sem `/hermes-work-control`|Adicionada linha `- /hermes-work-control (controle CDP da UI do Hermes Desktop em dev; leia apps/desktop/docs/AI-CONTROL-GUIDE.md para detalhes)`|`updated successfully` (toolu_1792553034160_1)|

### 6.3 Alterações apenas propostas (NÃO implementadas)

- MCP server para CDP (postergado).
- Screenshot nativo via CDP (postergado).
- Cursor virtual / highlight de elementos (postergado).
- Hot-reload para main/preload/backend (limitação conhecida, postergado).
- Integração com `BrowserControlLeaseManager` (rejeitada).

### 6.4 Impacto em seams do sistema

- **Runtime**: Sem alteração em `main.ts` ou `preload.ts` — zero impacto no ciclo de vida do Electron.
- **Bridge IPC**: Nenhuma nova chamada IPC adicionada.
- **Processos**: Sem alteração no spawn do backend Python (`hermes serve`).
- **Persistência**: Nenhuma nova store ou arquivo de estado.
- **Contratos**: Adição de `window.__hermesAiControlActive` como convenção global (cooperativa, não enforcement).

---

## 7. Problemas, Bugs e Análise de Causa Raiz

### B-01 — Launcher workstation desabilitava CDP por padrão

- **Sintoma**: `eval.mjs` falharia ao conectar em 9222 quando iniciado via `START-HERMES-WORKSTATION.bat`.
- **Contexto**: Descoberto durante validação do Request 4 item 1.
- **Impacto**: Todo o fluxo de dogfooding via launcher oficial estaria quebrado silenciosamente.
- **Causa raiz**: Bloco em `workstation/start.ps1` que definia `$env:HERMES_DESKTOP_CDP_PORT = "off"` quando não especificado, com justificativa histórica de evitar colisões.
- **Solução**: Editar para default `9222`, preservando opt-out explícito via `=off`.
- **Estado**: **Corrigido**.

### B-02 — `glob` timeout ao listar arquivos do shell

- **Sintoma**: `fs_glob` com `apps/desktop/src/app/shell/*.tsx` retornou timeout após 20s.
- **Contexto**: Mapeamento inicial do ponto de montagem do badge.
- **Solução**: Fallback para `shell_run` com `ls` direto.
- **Estado**: **Contornado**.

### B-03 — Prompt original indicava arquivo inexistente (`app-shell.tsx`)

- **Sintoma**: `ls` e `find` não encontraram `apps/desktop/src/app/shell/app-shell.tsx`.
- **Causa raiz**: Arquitetura contrib-driven não usa esse nome; o root é `apps/desktop/src/app/contrib/controller.tsx`.
- **Solução**: Badge montado em `controller.tsx` após inspeção do `return` JSX.
- **Estado**: **Corrigido por adaptação**.

### B-04 — `CLAUDE.md` inexistente na raiz

- **Sintoma**: `test -f` retornou `CLAUDE_MD_NOT_FOUND`.
- **Solução**: Criar do zero com conteúdo apropriado.
- **Estado**: **Corrigido**.

---

## 8. Testes, Verificações e Evidências de Funcionamento

### 8.1 Testes unitários Vitest — `AiControlBadge.test.tsx`

**Comando executado**:

```bash
cd C:/Github/hermes-agent/apps/desktop && npx vitest run src/app/shell/AiControlBadge.test.tsx --reporter=verbose
```

**Resultado (output real)**:

```
✓ |ui| src/app/shell/AiControlBadge.test.tsx > AiControlBadge > renders nothing when flag is false 18ms
✓ |ui| src/app/shell/AiControlBadge.test.tsx > AiControlBadge > renders badge when flag is true 47ms
✓ |ui| src/app/shell/AiControlBadge.test.tsx > AiControlBadge > toggles flag and badge visibility on Ctrl+Shift+A 45ms
✓ |ui| src/app/shell/AiControlBadge.test.tsx > AiControlBadge > does not toggle on partial shortcut 4ms
Test Files  1 passed (1)
Tests  4 passed (4)
```

- **Estado**: ✅ **APROVADO**.
- **Limitação**: Testa apenas lógica do componente; não valida montagem em `controller.tsx` nem comportamento no runtime real.

### 8.2 Testes E2E (Incremento A do Ciclo 1)

- **Estado**: ❌ **NÃO EXECUTADOS**.
- **Escopo pendente**:
    1. `npm run dev` em `apps/desktop`.
    2. Confirmar Vite em `http://127.0.0.1:5174`.
    3. `curl http://127.0.0.1:9222/json` retornando targets.
    4. `node apps/desktop/scripts/eval.mjs "document.title"` retornando título.
    5. Alterar texto em `gateway-menu-panel.tsx` e confirmar HMR.
    6. `taskkill /F /PID <pid>` do backend e observar toast "Reconnect gateway".
- **Evidência**: Não há registro de execução no histórico.

### 8.3 Validação da skill `hermes-work-control`

- **Evidência indireta**: System message após criação mostra `hermes-work-control` aparecendo na lista de skills disponíveis.
- **Estado**: ✅ **CONFIRMADO como registrada**.
- **Limitação**: Não houve invocação real da skill via `/hermes-work-control` durante a sessão.

### 8.4 Validação do launcher `.bat`

- **Evidência**: Leitura de `start.ps1` confirma que agora define `HERMES_DESKTOP_CDP_PORT = "9222"` quando não especificado.
- **Estado**: ✅ **CONFIRMADO em código; NÃO VALIDADO em runtime** (não houve execução do `.bat`).

---

## 9. Estado Final dos Artefatos e do Repositório

|Item|Estado|
|---|---|
|Repositório|`C:\Github\hermes-agent`|
|Branch atual|**Não verificado** (nenhum comando git executado)|
|Commits|**Nenhum commit produzido durante a sessão**|
|Arquivos criados|5 (badge, teste, guia, CLAUDE.md, skill)|
|Arquivos modificados|4 (controller.tsx x2, start.ps1, CLAUDE.md)|
|Pushes|Nenhum|
|PRs|Nenhum|
|Dependências instaladas|Nenhuma alteração em `package.json`|
|Variáveis de ambiente|`HERMES_DESKTOP_CDP_PORT` agora default `9222` via `start.ps1`|
|Skills registradas|`hermes-work-control` ativa em `C:\Users\Kevyn Lucas\.claude\skills\`|
|Serviços/processos|Hermes Desktop **não foi executado** durante a sessão|

**Observação crítica**: Todas as alterações permanecem como working directory changes não commitados. Se a sessão terminar sem commit, as mudanças sobrevivem apenas localmente.

---

## 10. Pendências, Riscos e Débitos Técnicos

|ID|Descrição|Origem|Impacto|Prioridade|Condição de resolução|
|---|---|---|---|---|---|
|**P-01**|Executar testes E2E do Incremento A (6 passos de validação de ambiente dev)|Ciclo 1, Request 2|Alto — MVP não está validado em runtime|**P0**|Todos os 6 passos passam com Hermes rodando|
|**P-02**|Gerar PROMPT DO CICLO 2 DE IMPLEMENTAÇÃO com lições aprendidas|Request 5 interrompida|Médio — bloqueia continuidade do trabalho|**P1**|Prompt colável em nova sessão com instruções E2E|
|**P-03**|Commit das alterações produzidas|Prática padrão de engenharia|Médio — alterações em working tree sem preservação|**P1**|`git add` + `git commit` das 9 mudanças|
|**P-04**|Implementar screenshot nativo via CDP (`Page.captureScreenshot`)|Postergado no MVP|Baixo — `preview_screenshot` supre visualmente|**P2**|Estender `eval.mjs` ou criar ferramenta dedicada|
|**P-05**|Implementar wait-for-selector estruturado|Postergado no MVP|Baixo — polling manual funciona|**P2**|Loop com timeout em `eval.mjs`|
|**P-06**|Adicionar error handling estruturado ao wrapper CDP|Postergado|Baixo — stderr do node basta para MVP|**P3**|Schema de erro JSON|
|**P-07**|Validar se CDP=9222 conflita com outros processos comuns|Risco do ajuste em `start.ps1`|Médio|**P2**|Teste com Chrome/outra instância Hermes rodando|
|**P-08**|Investigar hot-reload para main/preload (atualmente restart-only)|Limitação conhecida|Baixo (aceito no MVP)|**P3**|Estudo de viabilidade com `electron-vite` ou similar|

---

## 11. Guia de Continuidade para o Próximo Agente

### 11.1 O que já está estabelecido

- **Arquitetura**: Renderer=HMR, Main/Preload=restart, Backend=`hermes serve` (recycle em 503).
- **Coordenação IA/Humano**: flag global `window.__hermesAiControlActive` + atalho `Ctrl+Shift+A` + badge.
- **Wrapper CDP MVP**: `node apps/desktop/scripts/eval.mjs "<expression>"` via `Bash`.
- **Launcher**: `START-HERMES-WORKSTATION.bat` agora habilita CDP=9222 por padrão.
- **Skill**: `/hermes-work-control` disponível no diretório do usuário.
- **Documentação**: `apps/desktop/docs/AI-CONTROL-GUIDE.md` é a referência canônica.

### 11.2 O que NÃO deve ser repetido

- **Não reutilizar `BrowserControlLeaseManager`** para UI do app (escopo é browser interno).
- **Não criar MCP server / HTTP wrapper** para CDP no MVP — `eval.mjs` basta.
- **Não procurar `app-shell.tsx`** — root é `apps/desktop/src/app/contrib/controller.tsx`.
- **Não presumir que CDP está ativo em packaged builds** — gate em `dev-cdp.ts:58`.
- **Não re-investigar hot-reload de main/preload** — é restart por design (esbuild bundle one-shot).

### 11.3 O que NÃO deve ser quebrado

- **Contrato de reconexão**: `gateway-reconnect.ts` com `restart-followthrough` — qualquer mudança deve preservar sonda antes de fechar socket.
- **LeaseManager da workstation**: deve continuar protegendo apenas browser tasks (`DESTRUCTIVE_ACTIONS`).
- **Loopback binding do CDP**: porta 9222 deve permanecer em `127.0.0.1` — nunca expor off-host.
- **Gate `IS_PACKAGED`** em `dev-cdp.ts`: packaged builds devem ter CDP desabilitado incondicionalmente.

### 11.4 Pontos de atenção no ambiente

- **Caminhos críticos**:
    - `apps/desktop/scripts/eval.mjs` — wrapper CDP CLI.
    - `apps/desktop/electron/dev-cdp.ts` — gate do CDP em dev.
    - `apps/desktop/src/app/contrib/controller.tsx` — montagem do badge.
    - `apps/desktop/src/app/shell/AiControlBadge.tsx` — implementação do badge.
    - `workstation/start.ps1` — launcher que habilita CDP.
    - `CLAUDE.md` (raiz) — referência à skill.
- **Comandos de teste**:
    
    ```bash
    cd C:/Github/hermes-agent/apps/desktopnpx vitest run src/app/shell/AiControlBadge.test.tsx
    ```
    
- **Variáveis de ambiente**:
    - `HERMES_DESKTOP_CDP_PORT` (default agora `9222`; pode ser `off`).

### 11.5 Próximas ações recomendadas (sequência priorizada)

1. **[OBRIGATÓRIO] Executar testes E2E do Incremento A**:
    
    - **Objetivo**: Validar runtime real.
    - **Justificativa**: Única pendência P0; sem isso, MVP não está comprovado.
    - **Critério**: Todos os 6 passos do Incremento A passam.
2. **[OBRIGATÓRIO] Gerar PROMPT DO CICLO 2 DE IMPLEMENTAÇÃO**:
    
    - **Objetivo**: Desbloquear continuidade (Request 5 original).
    - **Justificativa**: Usuário pediu explicitamente.
    - **Critério**: Prompt colável em nova sessão com instruções E2E claras.
3. **[RECOMENDADO] Commit das alterações**:
    
    - **Objetivo**: Preservar o trabalho.
    - **Justificativa**: 9 arquivos alterados sem commit.
    - **Critério**: Working tree limpo após commit.
4. **[OPCIONAL] Validar ausência de colisão em 9222**:
    
    - **Objetivo**: Mitigar risco do ajuste em `start.ps1`.
    - **Justificativa**: Chrome/outra instância Hermes podem conflitar.
    - **Critério**: Teste com múltiplos processos rodando.

---

## 12. Matriz Final de Rastreabilidade

|Requisito / Objetivo|Ação realizada|Evidência|Estado final|Pendência|
|---|---|---|---|---|
|Duas telas simultâneas (Hermes + IA)|Infraestrutura CDP validada em código|`eval.mjs`, `dev-cdp.ts`|✅ Pronto para teste|Validação E2E (P-01)|
|HMR sem restart|Confirmado apenas para renderer|`vite.config.ts`|✅ Limitação documentada|Nenhuma (aceito)|
|Controle CDP da UI|Criado `AiControlBadge` + guia + skill|5 arquivos criados|✅ Implementado|Validação E2E (P-01)|
|Coordenação IA/Humano|Flag global + atalho + badge|`AiControlBadge.tsx`|✅ Implementado|Validação E2E (P-01)|
|Incremento A: validar ambiente dev|Especificado mas não executado|N/A|❌ Pendente|**P-01**|
|Incremento B: badge de controle IA|Implementado + testado|4/4 vitest passando|✅ Completo|Nenhuma|
|Incremento C: documentação CDP|`AI-CONTROL-GUIDE.md` criado|toolu_1792552047021_2|✅ Completo|Nenhuma|
|Launcher habilita CDP automaticamente|`start.ps1` editado para default 9222|toolu_1792553011626_1|✅ Completo|Validação runtime (P-07)|
|`CLAUDE.md` instrui leitura do guia|Adicionado + skill listada|toolu_1792553034160_1|✅ Completo|Nenhuma|
|Skill `hermes-work-control` criada|SKILL.md em `~/.claude/skills/`|toolu_1792552966153_1|✅ Registrada|Nenhuma|
|Prompt de continuação (Ciclo 2)|Solicitado mas não gerado|Request 5 interrompida|❌ Pendente|**P-02**|
|Commit das alterações|Não executado|N/A|❌ Pendente|**P-03**|

---

## 13. Avaliação Crítica da Sessão

### 13.1 Maior valor produzido

- **Arquitetura refinada**: Ciclos 2-3 evitaram decisões prematuras (reuso do LeaseManager, criação de MCP server) que teriam gerado débito técnico.
- **MVP honesto**: Documentação de limitações explícita (sem screenshot nativo, sem wait-for-selector, sem enforcement adversarial).
- **Descoberta do bloqueio no launcher**: Sem o ajuste em `start.ps1`, todo o fluxo de dogfooding estaria silenciosamente quebrado no launcher oficial — descoberta de alto impacto.

### 13.2 Esforço desproporcional

- **Mapeamento do root layout**: 4 chamadas de ferramenta (`fs_glob` timeout + 3 `ls`/`find`) para descobrir que o prompt original citava arquivo inexistente (`app-shell.tsx`). Poderia ter sido resolvido com leitura direta de `apps/desktop/src/app/index.tsx`.
- **Múltiplas leituras do `start.ps1`**: 3 tentativas com offsets diferentes devido a "leitura anterior omitida" — custo de contexto alto.

### 13.3 Decisões bem fundamentadas

- **Rejeição do LeaseManager**: Baseada em evidência direta do código (`workstation/browser_session.py:112-198`).
- **Uso direto de `eval.mjs`**: Alinhado com princípio 80/20 do usuário.
- **Flag global cooperativa**: Adequada ao escopo de dogfooding local (não é boundary de segurança).

### 13.4 Insuficiências

- **Validação runtime ausente**: Nenhuma das 3 camadas (HMR, CDP, reconexão) foi validada com Hermes realmente rodando. Todo o trabalho é baseado em análise estática de código.
- **Falta de commit**: 9 alterações em working tree sem preservação.
- **Prompt E2E não entregue**: Usuário pediu explicitamente, sessão foi interrompida para auditoria antes da geração.

### 13.5 Conclusões dependentes de comprovação

- "Reconexão automática funciona em 3-15s" — inferido de `use-gateway-boot.ts:147` (`BOOT_RETRY_MAX_ATTEMPTS = 5`, `BOOT_RETRY_BASE_DELAY_MS = 2_000`) mas não cronometrado.
- "CDP=9222 não conflita no ambiente do usuário" — presumido, não testado.
- "Badge é visível no canto superior direito" — CSS implementado (`fixed right-4 top-4 z-50`), mas não renderizado em runtime durante a sessão.

### 13.6 Recomendações de melhoria de abordagem

1. **Sempre validar em runtime antes de declarar pronto**: testes unitários + análise estática não substituem E2E.
2. **Commit incremental**: após cada incremento funcional, commitar para preservar trabalho.
3. **Começar pelo arquivo raiz citado no prompt** antes de expandir busca — o prompt original citava `app-shell.tsx` que não existia, mas a descoberta poderia ter sido mais direta.
4. **Gerar o prompt de continuação antes de encerrar** sessões de implementação — o ciclo de trabalho do usuário depende dele.

---

**Fim do Relatório Técnico Integral de Sessão.**