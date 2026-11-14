# Relatório Técnico Integral — Queda do backend Hermes

## 0. Identificação e cobertura

- **Sessão:** `4b51c82b-8673-4827-b97c-5c4bbf07bc47` | **Projeto:** `C--Github-hermes-agent`.
- **Janela histórica:** 22/10/2026 23:49 a 23/10/2026 00:06 (horário de Brasília; do snapshot).
- **Branch(es) mencionadas:** `feat/hermes-workstation-startup-80-20`. **Snapshot de código inspecionado em separado:** `e9fe6b38a0` (checkout main em 23/10/2026).
- **Base analisada:** JSONL original, 335 registros; tool calls e respectivos resultados; inspeção somente leitura dos caminhos críticos no Git. Histórico das ferramentas pode apontar logs auxiliares não expandidos.
- **Confiança:** alta no vínculo de sessão/código observado; moderada nas conclusões de impacto; baixa quando dependem de E2E não executado ou de logs compactados.

## 1. Sumário executivo

Investigação de suposta queda do backend. A evidência mostrou API `/api/health` respondendo na porta 56723 e commit correspondente, mas timeout de attach/announcement pelo Electron.

**Estado demonstrado:** Diagnóstico histórico, não correção. Backend saudável durante a medição; confiabilidade contínua não comprovada.

## 2. Objetivos, requisitos e evolução do escopo

**Objetivo recuperado:** Parece que o backend do Hermes deu uma caída, investiga o motivo e como fazer com que isso não aconteça de novo. Preciso de um backend confiável para o Hermes Work. Segue os logs: ============================================================ HERMES WORK - ONE-CLICK BOOTSTRAP ===================================…

**Delimitação:** a evolução real do escopo aparece nas fases abaixo; não atribuir resultado de sessões/forks paralelos a esta transcrição.

## 3. Linha do tempo técnica

1. Recebeu logs de falha de porta/timeout 90 s.
2. Inspecionou mecanismo de spawn/attach, ledger e processos Windows.
3. Conferiu health do backend em 127.0.0.1:56723; investigou PID adicional 22824.
4. Concluiu que problema percebido era de ciclo de vida de processos/attach, não necessariamente backend morto.

## 4. Descobertas e conhecimento adquirido

O HTTP 404 de dashboard headless pode ser esperado; `/api/health` retornou ok+commit. Falhas no Electron antes da reconexão ainda degradam usabilidade.

## 5. Decisões técnicas e arquiteturais

**D-01 — Direcionamento observado:** Não alterar código no calor da investigação sem prova da causa de instabilidade; diferenciar erro benigno de 404 de timeout. A decisão só é definitiva quando o usuário a ratificou; alternativas não documentadas não são presumidas.

## 6. Alterações, arquivos e integração

`apps/desktop/electron/host-backend-attach.ts` e `dashboard-token.ts` foram lidos; nenhuma edição ou commit desta sessão.

**Conferência independente do checkout atual:**
- **PRESENTE** `workstation/install.ps1`; símbolos: Invoke-NativeCheck (L16/144) — sem diff local específico.
- **PRESENTE** `workstation/start.ps1`; símbolos: npm run dev (L117/123) — sem diff local específico.
- **PRESENTE** `apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts`; símbolos: hydration.completed (L916), logLine (L885/895) — sem diff local específico.
- **PRESENTE** `workstation/scripts/kill-zombie-electron.ps1` — sem diff local específico.

## 7. Problemas, falhas e causas

Timeout `Timed out waiting for Hermes backend port announcement (90000ms)` e processos órfãos; a atribuição exata à janela reap/respawn é interpretação do assistente.

## 8. Testes e evidência de funcionamento

Health autenticado/não autenticado observado na porta 56723; nenhum teste regressivo implementado.

Não executei teste específico dessa sessão nesta auditoria; testes históricos são indicados separadamente.

**Interpretação:** arquivo presente ≠ função integrada ≠ teste aprovado ≠ comportamento validado no runtime. Resultados relatados sem saída inequívoca permanecem REPORTADOS.

## 9. Estado final e reconciliação histórica

Diagnóstico histórico, não correção. Backend saudável durante a medição; confiabilidade contínua não comprovada.

**Importante:** constatações de 23/10/2026 são posteriores à sessão e não autorizam afirmar que a mesma implementação estava presente naquele momento. Não foram criados commits nem alterado código durante esta auditoria.

## 10. Pendências, riscos e débitos técnicos

A frase 'backend confiável' foi ampla demais: um único health positivo não afasta races de attach.

## 11. Guia de continuidade

Instrumentar e testar lifecycle com reap/respawn, attach a porta antiga e cenários de timeout, com assertions de pronta recuperação.

**Antes de editar:** confirmar branch, claims multiagente e histórico de commits; não duplicar uma entrega existente, nem suprimir teste que falhou no período original.

## 12. Matriz de rastreabilidade

| Questão | Evidência | Situação |
|---|---|---|
| Objetivo da sessão | Solicitação humana do JSONL | **Registrado** |
| Resultado alegado | Mensagens e saídas de ferramentas do JSONL | **Separado em relato/execução** |
| Código no checkout atual | Arquivos e símbolos verificados na seção 6 | **Existência verificada quando presente** |
| Pronto para produção | Testes de aceitação em condições reais | **Não presumido** |

## 13. Avaliação crítica da sessão

Houve prova positiva de saúde do servidor; diagnóstico causal de corrida precisa teste reprodutível.

**Juízo desta auditoria:** a síntese acima resulta de leitura e reconciliação qualitativa do histórico, não de concatenação de turnos. Onde não há evidência operacional suficiente, a avaliação permanece parcial ou indeterminada.

### Referências de origem para auditoria

Os números abaixo indicam linhas do arquivo `4b51c82b-8673-4827-b97c-5c4bbf07bc47.jsonl` preservado em Sessões Claude - BRUTO. Trechos são intencionalmente abreviados; o histórico integral é a fonte primária.

| Tipo de evidência | Linha JSONL | Identificador/trecho |
|---|---:|---|
| Solicitação inicial | 4 | Parece que o backend do Hermes deu uma caída, investiga o motivo e como fazer com que isso não aconteça de novo. Preciso de um backend confi… |
| Síntese/resposta do assistente (REPORTADO) | 321 | Vou ler a implementação de 'resolveServedDashboardToken' em 'dashboard-token.ts' para confirmar como o fallback funciona quando o endpoint root retorn… |
| Síntese/resposta do assistente (REPORTADO) | 330 | A investigação confirmou que o backend **não caiu** — ele está saudável e respondendo na porta '56723' com o commit correto ('04c8b44b'). O erro "Time… |
| Read (SAÍDA ARQUIVADA) | 260 | C:\Github\hermes-agent\apps\desktop\electron\host-backend-attach.ts |
| Bash (SAÍDA ARQUIVADA) | 271 | powershell -Command "try { $p = Get-Process -Id 22824 -ErrorAction Stop; Write-Host ('ALIVE pid=' + $p.Id + ' cpu=' + $p.CPU + ' ws=' + $p.Wor… |
| Bash (ERRO DE FERRAMENTA) | 280 | powershell -NoProfile -Command "$p = Get-Process -Id 22824 -ErrorAction SilentlyContinue; if ($p) { Write-Host ('ALIVE pid=' + $p.Id + ' cpu='… |
| Read (SAÍDA ARQUIVADA) | 322 | C:\Github\hermes-agent\apps\desktop\electron\dashboard-token.ts |

**Origem SHA-256:** `366a745a703cd9134b7ee6db24f029a1e4aec4176ec24c82cd1975d6e31959c7`.

---
