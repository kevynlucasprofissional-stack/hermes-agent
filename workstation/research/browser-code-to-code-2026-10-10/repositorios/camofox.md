# Relatório de Auditoria Code-to-Code: Camofox Browser Server

**Projeto:** Camofox Browser Server (`camofox-browser`)  
**Commit SHA:** `N/A (unversioned snapshot local)`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/camofox-browser-main`  
**Licença:** **MIT** (`LICENSE`)  
**Stack:** TypeScript / Node.js 20+, Camoufox (Firefox stealth engine), Docker  
**Tamanho Auditado:** 155 arquivos TS, 88 testes  
**Classificação de Reuso:** **INTEGRATE EXTERNAL / ADAPT** (Manter como backend externo especializado em stealth)  

---

## 1. Identidade e Arquitetura

O Camofox é um servidor REST autônomo projetado para fornecer um navegador indetectável (*anti-detection*) para agentes de IA. Ele empacota o motor Camoufox (uma versão modificada do Firefox com mascaramento de hardware, áudio, WebGL e canvas) sob uma API REST limpa em TypeScript.

O repositório do Hermes Agent já possui código preliminar de integração em `tools/browser_camofox.py`, ativado quando `CAMOFOX_URL` está configurado no ambiente.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Pool de Contextos e Isolamento de Perfis
- **Arquivo:** `src/services/context-pool.ts` e `src/services/session.ts`
- **Mecanismo:** Mantém pools de instâncias de navegador pré-aquecidas com perfis isolados em disco, rotação de User-Agent, spoofing de resolução de tela e spoofing de aceleração gráfica por hardware.

### 2.2. Recuperação de Navegação e Detecção de Bloqueio
- **Arquivo:** `src/services/nav-recovery.ts`
- **Mecanismo:** Detecta desafios Cloudflare, captchas Turnstile e bloqueios HTTP 403/429. Emite sinalização para que o agente possa decidir entre rotacionar o proxy, pausar ou alertar o operador humano.

### 2.3. Streaming Visual via VNC
- **Arquivo:** `src/services/vnc.ts`
- **Mecanismo:** Oferece visualização em tempo real da sessão do navegador via WebSocket VNC, permitindo que interfaces remotas ou sem tela mostrem a execução ao vivo.

---

## 3. Mapa de Correspondência com o Hermes Work

| Mecanismo | Camofox | Hermes Work | Veredito |
|---|---|---|---|
| Evasão de Anti-Bot / Cloudflare | Máxima (Camoufox C++ patches + fingerprints reais) | Média (Chromium padrão do Electron com flags) | **Camofox superior para alvos protegidos** |
| Integração Desktop | Servidor REST externo em container/processo separado | Nativo e embutido no processo Electron Desktop | **Hermes superior para uso diário local** |
| Latência IPC | Chamadas REST HTTP locais/remotas | IPC direto de processo no Electron | **Hermes mais rápido** |

---

## 4. Análise de Licença e Requisitos de Portabilidade

- **Licença:** **MIT License**. Totalmente compatível.
- **Estratégia:** Não há necessidade de reimplementar o Camofox dentro do Hermes Desktop. A decisão correta é consolidar o cliente `tools/browser_camofox.py` como um backend de escape (fail-over para alvos com bloqueio estrito).
