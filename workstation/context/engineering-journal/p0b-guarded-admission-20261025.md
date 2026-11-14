# P0-B — Identidade de sessão, guardas de escrita e integração Git (2026-10-25)

**Estado:** IMPLEMENTADO LOCALMENTE, GUARDA ESTRITA OPT-IN / 42 PASS / 1 SKIP / NÃO É ENFORCEMENT UNIVERSAL. Sem commit, push, merge, troca de branch ou qualificação de release.

## Checkout e claims
- Diretório: C:\Github\hermes-agent; branch observada: main; HEAD na entrada: f1d5ab2f030e940ed4571371b0de45a21a009c9e.
- Checkout compartilhado com alterações sujas e numerosas reservas; a lane p0a-coordinator-20261025 continua READY_FOR_INTEGRATION e seus três arquivos NÃO foram editados.
- Claim desta missão: chatgpt-p0b-controls-20261025 / p0b-controls-20261025. Arquivos reclamados: workstation/scripts/collab_admission.py, workstation/scripts/collab_git.py, workstation/tests/test_collab_admission.py, workstation/tests/test_collab_git.py, .claude/hooks/check-claim-edit.sh, .claude/hooks/check-claim-bash.sh e este journal.
- .claude/hooks/check-branch.sh estava dirty antes deste trabalho e foi preservado. .claude/settings.local.json já aponta para os hooks; não foi alterado. Não houve claim de ROADMAP/Intelligence/CURRENT, reservados pelo M3.

## Implementação
1. workstation/scripts/collab_admission.py:
   - new-session cria claim disjunta via multi_agent_coordination.claim() existente e emite credencial aleatória de 36 bytes convertida para token URL-safe, com identificador UUID. Armazena apenas SHA-256 da credencial sob .hermes-collab/.session-leases (ignorado pelo Git); não reaproveita claims legados de outro agent. Falha após reclamar paths exige reconciliação manual (não libera claim silenciosamente).
   - verified_session confere token com compare_digest, identidade agent/lane associada a claim ainda existente e branch observada; proíbe assumir que --agent livre prove propriedade.
   - relative_write_target resolve paths e pais symlink/junction, nega destino externo e .git/.hermes-collab; check-write exige sessão/token, branch e claim estrita, nega freeze de integração e falhas de registro.
   - check-command autoriza apenas gramática estrita de consultas Git; demais comandos Bash, incluindo Git mutante, Python/test runners e shell desconhecido, são negados em modo opt-in. Isso é propositalmente conservador e exige fluxo dedicado para execuções de teste dos agentes migrados.
   - CLI new-session, check-write e check-command. Testes não registram credenciais no checkout real.

2. .claude/hooks/check-claim-edit.sh e check-claim-bash.sh:
   - Inserido preflight estrito apenas se HERMES_COLLAB_SESSION ou HERMES_COLLAB_TOKEN estiverem presentes. Os dois dados são obrigatórios para passar.
   - Hooks antigos continuam ativos (incluindo seu fail-open legado) para sessões sem credencial; NÃO declarar proteção global ou migração concluída.
   - Nenhum ajuste em check-branch.sh nem no settings.local.json, preservando personalizações e trabalhos sujos de outras sessões.

3. workstation/scripts/collab_git.py:
   - Verifica assinatura HMAC de autorização em arquivo JSON externo, usando HERMES_COLLAB_OPERATOR_KEY não configurada pelo código, com duração, identidade de sessão, branch, HEAD, paths exatos e operação stage-and-commit; sem chave/permissão => DENY.
   - Dry-run por padrão, --execute explícito requer permit autenticado e branch/HEAD inalterados. Ao executar, cria diretório .hermes-collab/.integration-freeze via mkdir atômico, repete preflight, exige índice sem alterações staged prévias, executa Git add somente de paths autorizados, inspeciona staged paths e então Git commit. Sem push, pull, rebase ou switch automáticos.
   - A janela de freeze bloqueia admit_write de outros clientes gerenciados. Ferramentas fora dessa superfície podem ignorá-la; não existe lock no binário Git nem isolamento OS.
   - Aprovação humana precisa ser produzida externamente; este trabalho NÃO emitiu operador-key, permit de produção ou execução de Git no checkout.

## Testes e qualificação
- Rodada inicial focada: 23 PASS, 1 FAIL, 1 SKIP. Falha test_invalid_signature_denied: GitGuardError derivava de ValueError e era convertido no except genérico para PERMIT_INVALID; causa identificada, base GitGuardError movida para Exception; reexecução verde.
- Canonical: & 'C:\Program Files\Git\bin\bash.exe' scripts/run_tests.sh workstation/tests/test_collab_admission.py workstation/tests/test_collab_git.py workstation/tests/test_multi_agent_coordination.py -q --tb=short, com HERMES_PYTHON obtido pelo Python do Windows. **42 passed, 0 failed, 1 skipped** (symlink sem permissão no Windows; subtests aprovados). Os 18 testes P0-A passaram novamente sem tocar seus arquivos.
- Ruff check nos 4 arquivos Python P0-B: All checks passed. Bash -n dos 2 hooks: PASS. git diff --check dos 2 hooks: PASS.
- Testes usam Git init/checkout/add/commit APENAS em diretórios temporários e cópias temporárias de hooks. Nenhum commit/stage/branch/merge/push no Hermes Work.
- Casos: mesmo dono versus dono diferente, arquivos sem claim, token falso, ausência de identidade, branch drift, paths fora do root/metadados .git, casefold Windows, freeze, registry corrompido, permissões HMAC inválidas/expiradas, recusa Git stage prévio, revalidação em segundo integrador, commit autorizado em repo temp, Bash somente leitura, Bash mutante bloqueado, preservação do modo legado.
- git diff --check e Ruff comprovam checks focados; não houve CI, full suite, nativo Claude real conectado nem verificação ChatGPT/Controle Windows pelo MCP da P2.

## Limitações e próximas ações
- Token de sessão mantém proteção operacional entre clientes gerenciados, mas um processo arbitrário sob a MESMA conta Windows pode acessar os arquivos locais/variáveis; não constitui sandbox, ACL por agente ou autenticação adversarial. Nunca expor tokens em prompts, commits ou logs.
- O protocolo strict é opt-in. Para ativá-lo numa sessão nova, executar new-session num arquivo livre e exportar as variáveis HERMES_COLLAB_SESSION e HERMES_COLLAB_TOKEN apenas para o processo cliente gerenciado; não ativar globalmente nem reutilizar uma claim antiga.
- A superfície Bash inscrita restringe qualquer operação não certificada como leitura; isso inclui rodar testes via Bash. Para workflow confortável e seguro de teste/geração, criar futuro executor isolado e claim de outputs, não simplesmente permitir shell arbitrário.
- Freeze não é transação atômica com uma escrita de filesystem depois do preflight. Ações não gerenciadas e janelas TOCTOU ainda escapam, mesmo se a API retornou allowed=true.
- Falta P1 task awareness/handoff e P2 adapter MCP ChatGPT/Claude com duas sessões externas reais. Falta autorização de integrador para integrar Git/claims e promover documentação canônica.

## Handoff
Validar branch, status e claims ao retomar. Não editar arquivos P0-A ou M3 sem owner. Preservar a claim desta missão READY_FOR_INTEGRATION até integração ou handoff oficial. Próximo passo após a aceitação local desta etapa: P1, consultando IMPLEMENTER_PROMPTS.md, ou finalizar integração Git do pacote por integrador explicitamente designado; nenhum prompt autoriza essas operações automaticamente.
