# P0-A — Coordenador multiagente: claims persistentes e admissão estrita (2026-10-25)

**Estado:** IMPLEMENTADO NO CHECKOUT LOCAL / 18 TESTES CANÔNICOS PASS / AGUARDANDO INTEGRAÇÃO GIT AUTORIZADA. Não é release, CI ou aplicação global dos hooks.

## Checkout, propriedade e preservação
- Checkout: C:\Github\hermes-agent; branch main; HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e no início e ao final.
- Checkout compartilhado com muitos arquivos dirty/untracked de outras sessões. Sem branch, worktree, checkout, reset, clean, stash, stage, commit, push ou merge.
- Claim exclusivo: agent chatgpt-p0a-coordinator-20261025, lane p0a-coordinator-20261025.
- Arquivos reclamados: workstation/scripts/multi_agent_coordination.py, workstation/tests/test_multi_agent_coordination.py, este journal.
- Outros claims preservados. Registros reais observados ao final: 10 claims no momento da consulta, incluindo siteops-contract READY_FOR_INTEGRATION e a claim deste agente. Contagem não é invariável durante trabalho paralelo.

## Diagnóstico e prova RED
- Baseline tinha check_path() filtrando apenas status ACTIVE, liberando indevidamente READY_FOR_INTEGRATION/BLOCKED/DONE; caminhos inválidos permitidos; nenhuma flag de strict; read_claims() explodia em JSON inválido; claim() ignorava outra lane incompleta.
- Testes adicionados ANTES da correção, executados via python workstation/tests/test_multi_agent_coordination.py -v no Windows: 16 testes coletados, 1 falha e 16 erros reportados (incluindo subtests, razão pela qual contagem de erros pode exceder número de testes).
- Primeira tentativa do runner canônico via bash.exe de WSL falhou antes de coletar: env: bash\r: No such file or directory, devido ao shebang CRLF de scripts/run-in-hermes-env neste host. Nenhuma correção fora do escopo foi feita.

## Alterações de código
1. workstation/scripts/multi_agent_coordination.py::read_claims — registros sem owner.json retornam INCOMPLETE_CLAIM, JSON corrompido/tipo inválido/lane divergente retornam CORRUPT_CLAIM; nenhum é removido.
2. validated_claim_paths — valida registro e paths normalizados antes de permitir nova claim ou escrita; registro parcial/inválido bloqueia novas reservas, sem steal.
3. claim — usa validação depois de checar conflito de lane; mantém erro histórico "already claimed" e atomicidade do mkdir.
4. check_path — preserva ownership para QUALQUER status até release, recusa paths inválidos, registry parcialmente publicado/busy e claims sobrepostos; owner recebe ALLOW apenas por --agent explícito (identidade cooperativa ainda não autenticada). Retorno estruturado com reason: INVALID_PATH, REGISTRY_BUSY, REGISTRY_UNAVAILABLE, CONFLICTING_CLAIMS, OWNED_BY_OTHER_AGENT, CLAIM_REQUIRED.
5. CLI main — acrescenta --require-claim à subcommand check-path; compatibilidade preservada na chamada antiga e modo legado permite caminho não reclamado para rollout gradual. Modo strict NÃO está ativado globalmente.

## Provas GREEN e regressões
- 18/18 testes PASS no runner oficial, incluindo concorrência real de dois subprocessos em diretórios temporários e testes para READY_FOR_INTEGRATION, BLOCKED, DONE, ownership, saída de strict, corrupção de JSON, registro incompleto, registros conflitantes e lock de transição.
- Comando canônico no Windows:
  PowerShell: $env:HERMES_PYTHON=((python -c 'import sys;print(sys.executable)') -replace '\\','/')
  PowerShell: & 'C:\Program Files\Git\bin\bash.exe' scripts/run_tests.sh workstation/tests/test_multi_agent_coordination.py -q --tb=short
  Resultado: 1 arquivo; 18 passed / 0 failed / exit 0 (Windows Python 3.13; pytest 9.0.2).
- Ruff: ruff check workstation/scripts/multi_agent_coordination.py workstation/tests/test_multi_agent_coordination.py — All checks passed, exit 0.
- git diff --check dos dois arquivos — exit 0.
- Registo real (apenas leitura): check-path apps/desktop/electron/ipc/site-ops.ts --require-claim --agent chatgpt-p0a-coordinator-20261025 => OWNED_BY_OTHER_AGENT (siteops-contract, status READY_FOR_INTEGRATION); check-path de arquivo deste agente => allowed true; unclaimed => CLAIM_REQUIRED.
- Diffs restritos aos dois arquivos Python (202 inserções, 22 exclusões no snapshot); arquivo journal separado.
- Sem testes Browser/WhatsApp reais, CI, Stage A de runtime ou promoção; coordenação é tooling local, sem mutação de runtime Workstation.

## Revisão crítica do patch preparado
A proposta reference/multi_agent_coordination_p0.patch foi inspecionada e melhorada. Em vez de quebrar o comando status em JSON inválido, a implementação marca CORRUPT_CLAIM e bloqueia novas mutações. Além disso, a validação de claims permite manter o erro legado ao tentar reclamar a mesma lane, cobre registry_guard presente e caminhos duplicadamente reclamados. Os testes do arquivo operacional são a evidência de integração local; os 11 testes do candidato não substituem esse conjunto.

## Próximo gate e ownership
**P0-B**: alterar guards/hooks de Claude e adicionar identidade de sessão autenticada, estrito na superfície de escrita controlada e governança exclusiva para operações Git. Atualmente --agent é autodeclarado e os hooks ainda falham abertos; o terminal/MCP irrestrito não é interceptado pelo coordenador. NÃO anunciar proteção de segurança universal.

A claim p0a-coordinator-20261025 permanece READY_FOR_INTEGRATION (não liberar antes de reconciliação/integração ou handoff formal pelo integrador). A integração Git não foi autorizada nesta missão. Nenhuma edição em docs centrais reclamados pelo WhatsApp M3. Este documento é o handoff. Não expandir escopo nem refazer auditoria genérica.
