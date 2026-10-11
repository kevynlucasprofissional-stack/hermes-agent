# Comparação Cruzada: Stagehand x Browser-Use x Agent Browser x Hermes Work

## 1. Visão Geral Comparativa
Esta comparação confronta os quatro principais motores de execução e automação de agentes de IA para navegadores web:
- **Stagehand:** Foco em operações determinísticas e semânticas (`act`, `observe`, `extract`) com cache em nuvem/local.
- **Browser-Use:** Foco em agentes autônomos em Python com barramento modular de sentinelas (`watchdogs`).
- **Agent Browser:** Foco em velocidade pura via Rust conectando-se diretamente ao WebSocket CDP.
- **Hermes Work:** Foco em ciclo de vida de Desktop integrado com Electron `WebContentsView`, autoridade estrita e compilação de procedimentos operacionais (`OperationalKernel`).

## 2. Comparativo de Dimensões Chave

| Dimensão | Stagehand | Browser-Use | Agent Browser | Hermes Work | Vencedor |
|---|---|---|---|---|---|
| Latência de Snapshot | Média (~250 ms) | Alta (~600 ms) | **Ultra-baixa (< 20 ms)** | Alta (~800 ms) | **Agent Browser** |
| Extração Estruturada | **Excelente (`extract` + cache)** | Básica (Markdown/JSON) | Básico | Improvisado (via console) | **Stagehand** |
| Resiliência a Falhas | Média | **Alta (`watchdogs/`)** | Alta (CDP frame guards) | Média/Alta (`BOR` fixes) | **Browser-Use** |
| Automação em Lote | Média (`batch`) | Baixa (atômico) | Média (CLI chaining) | Inexistente (atômico) | **Stagehand** |
| Aprendizado e Reuso | Cache simples | Inexistente | Inexistente | **Excelente (`ExperienceCompiler`)** | **Hermes Work** |

## 3. A Síntese Ideal para o Hermes Work
A solução perfeita para o Hermes Work é uma **combinação das melhores partes**:
1. O pipeline de percepção via CDP Accessibility Tree do **Agent Browser**.
2. O primitivo de extração com cache (`extract`) do **Stagehand**.
3. O barramento de recuperação de falhas (`CrashWatchdog`, `AboutBlankWatchdog`) do **Browser-Use**.
4. A compilação e verificação de autoridade do **Hermes Work**.
