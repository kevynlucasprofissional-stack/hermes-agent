# HANDOFF PROMPT 01 — Browser upload: análise de implementação e bloqueios (26/10/2026)

STATUS: BLOCKED_FOR_INTEGRATION / NOT_RELEASE_QUALIFIED.
Checkout: C:\Github\hermes-agent ; branch main ; HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e.
Agent cooperativo: chatgpt-hermes-upload-prep-20261026 ; integrador Git não identificado.
Claim: somente HANDOFF_PROMPT_01_20261026.md, HANDOFF_DOCS_20261026.md e teste isolado Windows junction.
Código produtivo, docs canônicos e Git index: NÃO ALTERADOS por este agente.

## Bloqueios reproduzidos

1. apps/desktop/electron/workstation-browser-runtime.ts está dirty (M): 38 linhas adicionadas e 6 removidas. O bloco de upload completo é parte do diff NÃO COMMITADO. O PROMPT 01 proíbe editar path sujo, mesmo sem claim.
2. tools/browser_workstation.py está dirty e claimed por chatgpt-whatsapp-m3 (ACTIVE); não alterar WhatsApp M3.
3. ROADMAP, Intelligence, CURRENT journal, Decisions e Known Issues estão dirty e claimed pelo mesmo owner ACTIVE. Ver HANDOFF_DOCS_20261026.md.
4. H-079 em workstation/context/DEVELOPMENT_GATES.md exige Stage A qualificado ou waiver específico. O Git ref local upstream/main não é ancestral do HEAD (merge-base --is-ancestor exit 1); não se verificou fetch/CI atual.
5. Não foi identificado escopo confiável de allowedRoots de upload; aceitar raízes do payload de IA seria inseguro.

## Código e problemas exatos

- apps/desktop/electron/workstation-browser-runtime.ts: executeControlRequest(), conjunto mutating (~2891), omite browser_file_upload. Isso deixa de invocar assertAgentControl e preflight para essa ação.
- Mesmo método: guardedControllerActions (~3236) também omite browser_file_upload. Isso deixa de invocar admitDurableControllerEffect().
- case browser_file_upload (~3406): path.resolve + existsSync; HTML document.querySelector() seleciona primeiro match sem validar input file único; DOM.setFileInputFiles; retorna files_uploaded com caminhos locais ABSOLUTOS. Não escreve receipt específico, nem LastReceipts/persistBrowserSessionState nessa ação.
- tools/browser_workstation.py: _WORKSTATION_SCHEMA_TOOLS já expõe browser_file_upload; whatsapp_send_attachment consome callback interno _upload. Preservar API e não modificar WhatsApp M3.
- Reference: reference-code/safe_upload_paths.mjs implementa realpath, arquivo regular, tamanho, limite de segmento; NÃO é código integrado, não contém autorização por TaskRun.

## Implementação recomendada quando autorizada

PASSO 1 — TDD RED em novo apps/desktop/electron/workstation-browser-runtime-upload.test.ts, reutilizando fixtures de workstation-browser-runtime-admission.test.ts e -recovery.test.ts.
* assertAgentControl negado, takeover humano, session mismatch, operação anterior incerta -> antes de qualquer CDP setFileInputFiles.
* replay do mesmo operation_id depois de ação ambígua/restart -> nenhum segundo CDP, state uncertain/reconciliation_required.
* inexistente, diretório, fora de allowlist, prefixo semelhante, Windows junction e Linux symlink fora de root, tamanho excedido, selector inválido ou múltiplo, iframe/shadow sem suporte -> falha fechada.
* retorno nunca expõe caminho local absoluto, tokens ou detalhes de filesystem.
* Electron/Chromium real, arquivo de teste offline, input file e evento change observados. Nunca abrir WhatsApp ou postar conteúdo real.

PASSO 2 — PRÉ-VALIDAR escopo confiável por TaskRun/owner: grant autorizado fora dos argumentos do modelo, com taskId, sessionHost, effectiveRunId, raízes, TTL e origem, ou falhar com upload_scope_required. Não inventar pasta padrão nem usar allowedRoots enviado pelo LLM.
* lista não vazia e limitada; path absoluto, realpath, fs.stat regular, tamanho definido e path.relative segment-aware; revalidar junto à chamada CDP.
* erros estruturados SEM paths locais; se o grant expirou/foi revogado, negar antes de CDP.
* refatorar/adaptar safe_upload_paths.mjs somente depois de testes RED em TS, mantendo helpers pequenos e localizados.

PASSO 3 — ADMISSION correta:
* incluir browser_file_upload em mutating E guardedControllerActions; somente uma lista não basta.
* usar controllerOperationId e effectiveRunId da sessão canônica para admission, efeito, receipt e persistência. Nunca marcar sucesso remoto a partir de ACK local.
* todas validações determinísticas possíveis devem anteceder admission. Depois de admission e ANTES do CDP, registrar terminal NOT_DISPATCHED somente quando comprovadamente nenhum efeito ocorreu; após início de CDP com efeito incerto, preservar UNCERTAIN e bloquear retry automático.
* rejeitar CSS selector com múltiplos matches ou alvo diferente de HTMLInputElement[type=file]; query DOM com expression controlada e selector serializado, sem JS arbitrário do modelo.
* revalidar owner/lease após awaits. Iframe e shadow somente com implementação específica testada, caso contrário erro explícito. Manter DOM.setFileInputFiles no WebContents do BrowserTask.

PASSO 4 — RECEIPT e projeção:
* após seleção verificada, construir BrowserOwnerReceipt com operationId=controllerOperationId, taskId, runId=effectiveRunId, browserTaskId, tabId, revision, action, safeUrl, executedAt.
* chamar this.taskLifecycle().recordReceipt(taskId, receipt), atualizar this.lastReceipts e this.persistBrowserSessionState().
* resposta segura sugerida: success true, status selected, file_count, operation_id, receipt sanitizado. Não retornar ...snapshot nem files_uploaded contendo resolvedFiles.
* seleção não prova recebimento no site nem envio de mensagem; nunca traduzir "selected" em "sent".

PASSO 5 — Verificação:
* RED -> GREEN no Vitest Electron focado (usar runner correto de apps/desktop).
* suites Browser admission/recovery/resilience, npm run typecheck em apps/desktop.
* E2E Electron/Chromium com fixture offline real e observação de input.files + change; testes de falha com confirmação de nenhum CDP mutável quando não autorizado.
* git diff --check, diff path-a-path, status claims, registro do baseline. Commit somente pelo integrador autorizado. Documentação canônica somente pelo owner após liberação da claim.

## Evidência realmente executada neste turno

- node --test reference-tests/test_safe_upload_paths.mjs: 4 PASS, 1 FAIL, exit 1. Falha EPERM NA CRIAÇÃO do symlink de arquivo no Windows, anterior à asserção: não comprova vulnerabilidade nem proteção nesse caso.
- Novo reference-tests/test_safe_upload_paths_windows_junction.mjs: 1 PASS, exit 0 no Windows real. Uma directory junction externa foi criada e a validação bloqueou com upload_scope_denied.
- python apply_docs_preview.py --repo C:\Github\hermes-agent: cinco targets BLOCKED existing WIP; NENHUMA ESCRITA.
- npm --prefix apps/desktop run typecheck: exit 0 no checkout atual. Esta é uma prova de baseline (sem patch de upload), NÃO um GREEN da implementação solicitada.
- git diff --check (global): exit 2 por linha em branco extra no fim de workstation/dogfood/Prompts.md, arquivo preexistente fora do escopo; não corrigido nem atribuído a esta tarefa.
- Não houve RED/GREEN do Browser runtime, typecheck APÓS patch, integração nem E2E Electron. NÃO DECLARAR DONE.

## Retomada segura

Exigir integrador atual designado e liberação do owner WhatsApp M3; preservar ou integrar primeiro alterações sujas no runtime; resolver Stage A ou registrar waiver específico; definir grant/roots com autoridade fora do payload do agente. Só então rodar a implementação do Prompt 01 no checkout.

Known Issues que permanecem: HW-UPLOAD-01, WA-M3-01 e HLM replay M3 HOLD.