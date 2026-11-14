# Relatório Técnico Integral — Comparativo Browser OS Neo e Hermes Work

## 0. Identificação e cobertura

- **Sessão:** `4fef7e27-3f1b-4a5a-8781-ab3d935391f5` | **Projeto:** `C--Github-hermes-agent`.
- **Janela histórica:** 22/10/2026 19:50 a 23/10/2026 00:02 (horário de Brasília; do snapshot).
- **Branch(es) mencionadas:** `feat/hermes-workstation-startup-80-20`. **Snapshot de código inspecionado em separado:** `e9fe6b38a0` (checkout main em 23/10/2026).
- **Base analisada:** JSONL original, 562 registros; tool calls e respectivos resultados; inspeção somente leitura dos caminhos críticos no Git. Histórico das ferramentas pode apontar logs auxiliares não expandidos.
- **Confiança:** alta no vínculo de sessão/código observado; moderada nas conclusões de impacto; baixa quando dependem de E2E não executado ou de logs compactados.

## 1. Sumário executivo

Comparativo BrowserOS Neo (`packages/browseros-agent`) e Hermes, seguido de protótipos de orçamento de tokens, guards e mensagens de erro. Relatório original estimava ganhos potenciais, não velocidade real provada do Hermes.

**Estado demonstrado:** Artefatos implementados e versionados; integração real ao dispatcher e impacto líquido ainda requer prova.

## 2. Objetivos, requisitos e evolução do escopo

**Objetivo recuperado:** procura o na pasta de referências o repositório do browser OS neo dentro de browser OS e vamos fazer um comparativo do Browser OS neo com o hermes Work Vamos focar principalemente em velocidade, economia de tokens e UIX

**Delimitação:** a evolução real do escopo aparece nas fases abaixo; não atribuir resultado de sessões/forks paralelos a esta transcrição.

## 3. Linha do tempo técnica

1. Localização inicialmente ambígua do projeto Neo foi corrigida pelo usuário.
2. Comparou Rust/axum/dispatch e mecanismo Python/Electron, CDP e readiness.
3. Avaliou dados de tarefa WhatsApp real e desenhou intervenções prioritárias.
4. Foram criados módulos token_estimate.py, browser_guards.py e browser_error_messages.py e relatório técnico.

## 4. Descobertas e conhecimento adquirido

Estimativa de tokens e early-reject de guards podem reduzir custo de payload ou tempo de falhas, mas estimativas de 87% são potenciais para amostras, não economia total de produto.

## 5. Decisões técnicas e arquiteturais

**D-01 — Direcionamento observado:** Adotar módulos isolados e reversíveis para token estimate, validação pré-dispatch e erros explicativos, sem migrar runtime para Rust. A decisão só é definitiva quando o usuário a ratificou; alternativas não documentadas não são presumidas.

## 6. Alterações, arquivos e integração

Os três módulos e o relatório comparativo existem em `workstation/`, incorporados ao histórico Git (commit 268b8f3). O código tem funções explícitas de estimativa, registry de guards e classificação de erro.

**Conferência independente do checkout atual:**
- **PRESENTE** `workstation/token_estimate.py` — sem diff local específico.
- **PRESENTE** `workstation/browser_guards.py` — sem diff local específico.
- **PRESENTE** `workstation/browser_error_messages.py`; símbolos: CIRCUIT_OPEN (L35/118), UNBOUND_CALL (L33/99) — sem diff local específico.
- **PRESENTE** `workstation/reports/validacao-cruzada-browseros-neo-vs-hermes.md` — sem diff local específico.

## 7. Problemas, falhas e causas

Precedência entre CIRCUIT_OPEN e UNBOUND_CALL corrigida segundo histórico; fluxo E2E WFR após restart não foi comprovado.

## 8. Testes e evidência de funcionamento

Sessão descreveu microbenchmark ~0,001 ms de guards e testes de cenários; nesta auditoria foi verificada presença de código, não benchmark reexecutado.

Não executei teste específico dessa sessão nesta auditoria; testes históricos são indicados separadamente.

**Interpretação:** arquivo presente ≠ função integrada ≠ teste aprovado ≠ comportamento validado no runtime. Resultados relatados sem saída inequívoca permanecem REPORTADOS.

## 9. Estado final e reconciliação histórica

Artefatos implementados e versionados; integração real ao dispatcher e impacto líquido ainda requer prova.

**Importante:** constatações de 23/10/2026 são posteriores à sessão e não autorizam afirmar que a mesma implementação estava presente naquele momento. Não foram criados commits nem alterado código durante esta auditoria.

## 10. Pendências, riscos e débitos técnicos

Classificadores e budget slicing incorretos podem omitir contexto crítico ou rejeitar chamada válida.

## 11. Guia de continuidade

Medir before/after no Hermes real com iguais payloads; revisar adoção no dispatcher e preservar dados úteis.

**Antes de editar:** confirmar branch, claims multiagente e histórico de commits; não duplicar uma entrega existente, nem suprimir teste que falhou no período original.

## 12. Matriz de rastreabilidade

| Questão | Evidência | Situação |
|---|---|---|
| Objetivo da sessão | Solicitação humana do JSONL | **Registrado** |
| Resultado alegado | Mensagens e saídas de ferramentas do JSONL | **Separado em relato/execução** |
| Código no checkout atual | Arquivos e símbolos verificados na seção 6 | **Existência verificada quando presente** |
| Pronto para produção | Testes de aceitação em condições reais | **Não presumido** |

## 13. Avaliação crítica da sessão

Boa modularidade e comparação de mecanismos; alegações de superioridade de Rust por 'ordens de magnitude' não são benchmark equivalente.

**Juízo desta auditoria:** a síntese acima resulta de leitura e reconciliação qualitativa do histórico, não de concatenação de turnos. Onde não há evidência operacional suficiente, a avaliação permanece parcial ou indeterminada.

### Referências de origem para auditoria

Os números abaixo indicam linhas do arquivo `4fef7e27-3f1b-4a5a-8781-ab3d935391f5.jsonl` preservado em Sessões Claude - BRUTO. Trechos são intencionalmente abreviados; o histórico integral é a fonte primária.

| Tipo de evidência | Linha JSONL | Identificador/trecho |
|---|---:|---|
| Solicitação inicial | 4 | procura o na pasta de referências o repositório do browser OS neo dentro de browser OS e vamos fazer um comparativo do Browser OS neo com o… |
| Síntese/resposta do assistente (REPORTADO) | 532 | Vou gerar o relatório final de validação cruzada consolidando todas as evidências coletadas e atualizar o plano para conclusão. |
| Síntese/resposta do assistente (REPORTADO) | 558 | O ciclo de validação cruzada BrowserOS Neo vs Hermes Work foi concluído com sucesso: três módulos foram implementados, testados e validados com dados… |
| Write (SAÍDA ARQUIVADA) | 485 | C:\Github\hermes-agent\workstation\browser_guards.py |
| Write (SAÍDA ARQUIVADA) | 506 | C:\Github\hermes-agent\workstation\browser_error_messages.py |
| Edit (SAÍDA ARQUIVADA) | 523 | C:\Github\hermes-agent\workstation\browser_error_messages.py |
| Write (SAÍDA ARQUIVADA) | 544 | C:\Github\hermes-agent\workstation\reports\validacao-cruzada-browseros-neo-vs-hermes.md |

**Origem SHA-256:** `e735f210a88d85d670974bdfe3e2e6622abc0dab00505c7929992a06cc985a67`.

---
