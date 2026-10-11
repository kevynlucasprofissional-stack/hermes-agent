# Comparação Cruzada: BrowserOS x Browser-Use Desktop x Hermes Work

## 1. Visão Geral Comparativa
Comparação das três abordagens de aplicações desktop para navegação com agentes:
- **BrowserOS:** Compilação própria de Chromium com patches C++ e agente em Side Panel via extensão WXT.
- **Browser-Use Desktop:** Aplicação Electron com múltiplos layouts (Hub, Pill, Logs, Takeover Overlay).
- **Hermes Work:** Aplicação Electron integrada com `WebContentsView`, Browser Hub e Chat Right Rail.

## 2. Pontos Fortes e Fracos

| Mecanismo | BrowserOS | Browser-Use Desktop | Hermes Work |
|---|---|---|---|
| Manutenibilidade do Browser | Baixa (exige compilar Chromium) | **Alta (Electron padrão)** | **Alta (Electron padrão)** |
| Eficiência em Segundo Plano | Normal (Chromium padrão) | Normal | **Excelente (6 fps throttling)** |
| Importação de Sessão do Chrome | Não nativo | **Excelente (`chrome-import` DPAPI)** | Inexistente (login manual) |
| Eficiência de Tokens | **Excelente (`diffSnapshots`)** | Baixa (snapshots repetidos) | Baixa (snapshots repetidos) |
| Feedback de Intervenção Humana | Bom (extensão reativa) | **Excelente (`takeoverOverlay.ts`)** | Bom (`BrowserHumanControlLease`) |

## 3. Decisão Arquitetural
O Hermes Work deve manter seu host Electron, adotando o algoritmo de **`diffSnapshots` do BrowserOS** e os módulos **`chrome-import` e `takeoverOverlay` do Browser-Use Desktop**.
