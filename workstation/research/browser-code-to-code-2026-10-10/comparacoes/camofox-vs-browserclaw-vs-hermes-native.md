# Comparação Cruzada: Camofox x BrowserClaw x Browser Nativo Hermes

## 1. Visão Geral Comparativa
- **Camofox:** Servidor REST especializado em evasão de anti-bot avançado via motor Camoufox (Firefox stealth).
- **BrowserClaw:** Biblioteca TypeScript de alta produtividade focada em ações em lote e snapshots amigáveis para IA.
- **Browser Nativo Hermes:** Chromium embutido no Electron com controle loopback local.

## 2. Estratégia de Coexistência
- O **Browser Nativo Hermes** permanece como o motor primário para 95% do trabalho cotidiano do usuário.
- O **BrowserClaw** fornece a biblioteca de ações em lote (`executeBatch`) para ser incorporada no motor nativo do Hermes.
- O **Camofox** permanece como um backend alternativo via rede/REST para tarefas em sites com proteção Cloudflare agressiva.
