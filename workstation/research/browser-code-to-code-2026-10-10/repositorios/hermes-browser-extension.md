# Relatório de Auditoria Code-to-Code: Hermes Browser Extension

**Projeto:** Hermes Browser Extension (`abundantbeing/hermes-browser-extension`)  
**Commit SHA:** `ba4d30e609ca0e1074e502dc8feef42a5ea9c3d4`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/abundantbeing--hermes-browser-extension`  
**Licença:** **MIT** (`LICENSE`)  
**Stack:** TypeScript, Chrome Extension Manifest V3, Python (`tests/pytools/`)  
**Tamanho Auditado:** 12 arquivos TS, 26 arquivos Python, 236 testes  
**Classificação de Reuso:** **KEEP / INTEGRATE EXTERNAL** (Componente oficial de extensão do Hermes, já alinhado aos contratos do gateway)  

---

## 1. Identidade e Arquitetura

A `hermes-browser-extension` é a extensão de navegador oficial para conectar um Google Chrome, Microsoft Edge ou Brave já instalado no computador do usuário ao gateway do Hermes Agent.

Ela implementa o lado do cliente do protocolo definido em `gateway/browser_control_broker.py`, utilizando canais seguros de WebSocket ou HTTP loopback com tickets descartáveis.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Handshake Criptográfico e Tickets Descartáveis
- A extensão solicita um ticket efêmero ao gateway local (`POST /v1/browser-control/ticket`), que expira em 30 segundos (`DEFAULT_TICKET_TTL = 30.0`).
- Ao registrar a conexão, o broker consome o ticket e estabelece um túnel de controle restrito àquele `session_id` e `principal_id`.

### 2.2. Execução sobre o Perfil Real do Usuário
- Como a extensão roda dentro do Chrome do usuário, o agente ganha acesso instantâneo a todos os logins, extensões de senha (1Password, Bitwarden) e certificados corporativos já existentes na máquina, sem necessidade de transferir credenciais para o Electron.

---

## 3. Mapa de Correspondência com o Hermes Work

| Dimensão | Extensão Chrome | Browser Nativo Workstation |
|---|---|---|
| Autenticação | Zero atrito (usa o Chrome real do usuário) | Requer login no Electron ou importação de cookies |
| Isolamento | Compartilha a janela do usuário (risco de interferência visual) | `WebContentsView` dedicada com abas e background throttling |
| Velocidade | Depende de IPC da extensão Manifest V3 | Acesso direto ao Chromium via processo Electron |

---

## 4. Recomendações Objetivas

1. **Manter como Rota de Extensão Oficial:**
   A extensão é a solução perfeita para sites com autenticação complexa (bancos, SSO corporativo com chave de segurança física).
2. **Harmonizar os Schemas de Ações:**
   Garantir que as ferramentas adicionadas ao Browser nativo (ex: `browser_batch_actions` e `browser_extract`) também sejam declaradas no `BROWSER_CONTROL_CAPABILITIES` do broker para paridade completa.
