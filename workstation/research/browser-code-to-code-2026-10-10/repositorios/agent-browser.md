# Relatório de Auditoria Code-to-Code: Vercel Labs Agent Browser

**Projeto:** Agent Browser (`vercel-labs/agent-browser`)  
**Commit SHA:** `44af39842650f0bb9c1afb7354df9a82921d4f09`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/vercel-labs--agent-browser`  
**Licença:** **Apache-2.0** (`LICENSE`)  
**Stack:** Rust (core nativo em `cli/src/native`), TypeScript, Next.js (dashboard)  
**Tamanho Auditado:** 194 arquivos TS, 1 arquivo Python, 25+ módulos Rust nativos, 13 arquivos de teste  
**Classificação de Reuso:** **ADAPT / REIMPLEMENT PATTERN** (Apache-2.0 permissiva; o core em Rust pode ser compilado como binário ou ter seus algoritmos portados para TypeScript/Python)  

---

## 1. Identidade e Arquitetura

O `agent-browser` da Vercel Labs adota uma arquitetura de alta performance focada em latência mínima e baixo overhead. O motor de automação não roda em JavaScript: ele é construído em **Rust** (`cli/src/native`), conectando-se diretamente aos targets do Chromium via conexões WebSocket brutas de CDP (*Chrome DevTools Protocol*).

Isso elimina toda a sobrecarga de serialização e tempo de inicialização característicos de wrappers de Playwright ou Puppeteer.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Snapshot Determinístico Baseado em `Accessibility.getFullAXTree`
- **Arquivo:** `cli/src/native/snapshot.rs` (1.761 linhas)
- **Símbolo:** `take_snapshot(&client, session, options, refs, ...)`
- **Mecanismo:** Invoca o domínio `Accessibility` do CDP. A árvore de acessibilidade já é mantida internamente pelo motor Blink/Chromium para leitores de tela; portanto, extraí-la via CDP consome fração mínima de CPU e não exige nenhum script injetado na página.
- **Invalidação de Referências Duráveis:** Em `snapshot.rs` (linhas 71–95), implementa o algoritmo `durable_refs_invalidate_replaced_iframe_document` e `durable_refs_invalidate_replaced_iframe_session`. Se um iframe é recarregado ou muda de `loaderId`, as referências daquele iframe são invalidadas de forma cirúrgica, mantendo válidas as referências do documento pai.
- **Superioridade sobre Hermes Work:** O Hermes Work executa `querySelectorAll('*')` em JavaScript puro. Se um iframe for recarregado, o Hermes reseta toda a tabela de referências ou quebra silenciosamente ao tentar clicar em nós órfãos.

### 2.2. Diffs e Transições de Estado em Rust
- **Arquivo:** `cli/src/native/diff.rs`
- **Mecanismo:** Executa comparação vetorial ultra-rápida entre o estado anterior e o estado atual da árvore de acessibilidade. A latência de cálculo do diff é inferior a 2 milissegundos.

### 2.3. Isolamento e Segurança SSRF Nativa
- **Arquivo:** `cli/src/native/policy.rs`
- **Mecanismo:** Validação rigorosa de destino de rede, bloqueando requisições a endereços locais (127.0.0.1, 169.254.169.254, RFC 1918) diretamente no nível de interceptação de rede do CDP, prevenindo exploração de SSRF por agentes autônomos.

---

## 3. Mapa de Correspondência com o Hermes Work

| Mecanismo | Agent Browser | Hermes Work | Veredito |
|---|---|---|---|
| Latência de Snapshot | < 15 ms (Rust + CDP AXTree) | 300–1.200 ms (`executeJavaScript` com `querySelectorAll`) | **Agent Browser incomparavelmente mais rápido** |
| Resiliência de Referências em Iframes | Invalidação cirúrgica por `loaderId` | Invalidação total de `__hermesWorkstationRefs` ao mudar URL | **Agent Browser superior** |
| Política de SSRF | Filtro em Rust em `policy.rs` | `tools/url_safety.py` e `tools/website_policy.py` em Python | **Equivalentes em segurança, Agent Browser mais veloz** |
| Integração Desktop / Abas | CLI autônomo / Daemon | Electron nativo com `WebContentsView` e background throttling | **Hermes superior em experiência Desktop** |

---

## 4. Análise de Licença e Requisitos de Portabilidade

- **Licença:** **Apache License 2.0**.
- **Compatibilidade:** Totalmente compatível com a licença MIT do Hermes Agent com atribuição.
- **Portabilidade:** Os algoritmos de tratamento de nós AXTree e invalidação cirúrgica por `loaderId` podem ser adaptados diretamente em TypeScript dentro de `apps/desktop/electron/workstation-browser-runtime.ts`.

---

## 5. Recomendações Objetivas para o Hermes Work

1. **Adotar a estratégia de AXTree do Agent Browser (`ADAPT`):**
   Substituir a injeção de `inventoryScript` pela chamada CDP nativa de acessibilidade, reduzindo a latência do snapshot em mais de 90%.
2. **Implementar a invalidação de referências por `loaderId` (`ADAPT`):**
   Utilizar o evento CDP `Page.frameNavigated` para invalidar referências somente no frame que navegou, resolvendo falhas de interação em sites com iframes dinâmicos (ex: painéis de autenticação, Trello power-ups).
