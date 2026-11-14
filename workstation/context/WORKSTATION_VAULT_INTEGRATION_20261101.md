# Workstation — Integração do Vault (01/11/2026)

## Resultado
O Vault deixou de ser uma navegação lateral independente do Desktop e passou a ser o terceiro módulo interno do dashboard **Hermes Workstation**.

Navegação:
- `/browser`: dashboard com Navegador, Database, Vault.
- `/browser?module=vault`: monta diretamente o `VaultPage` existente no Workstation.
- `/vault`: rota de compatibilidade com `Navigate replace` para `/browser?module=vault`.
- `/browser?module=browser` e `/browser?module=database` permanecem inalterados.

## Implementação mínima
- `apps/desktop/src/app/workstation/index.tsx`: import lazy de `@/plugins/vault/vault-page`, tipo `WorkstationArea` atualizado, cartão do Vault no dashboard, botão de módulo na navegação interna e renderização da página existente.
- `apps/desktop/src/plugins/vault/plugin.tsx`: `bindApi(ctx)` preservado; removida contribuição `SIDEBAR_NAV_AREA`; contribuição `ROUTES_AREA` agora só redireciona links antigos.
- `apps/desktop/src/app/workstation/index.test.tsx`: mock do Vault e testes de seleção pelo dashboard e link direto.
- Nenhuma alteração em `workstation/vault.py`, `plugins/vault/dashboard/plugin_api.py`, `vault-page.tsx`, notas existentes, permissões, diretório raiz ou plugin manifest. O backend e a API são os originais.

## Evidências de funcionamento real
- Hermes em execução com AI Control: clique no cartão `Vault` a partir de `#/browser` abriu `#/browser?module=vault`, exibiu `Hermes Vault` e botão `Nova`.
- Rota `#/vault` redirecionou automaticamente para `#/browser?module=vault`; Vault renderizado.
- `GET /api/plugins/vault/status`: `status=ok`, root configurado e `notes_count=0` antes da verificação.
- Smoke real no backend: `POST /api/plugins/vault/notes` com título temporário único, `GET` confirmou conteúdo, `DELETE` confirmou limpeza; `GET /notes` final retornou `count=0`.
- 4 testes aprovados: `.venv\\Scripts\\python.exe -m pytest -q tests/plugins/test_vault_plugin_api.py tests/hermes_cli/test_vault_sources_shape.py` (1 aviso Starlette, não bloqueante).
- `eslint` dos arquivos TSX alterados e JSX parse via esbuild passaram sem erros.
- Registry da sessão atual: nenhuma contribuição `vault:nav`; antiga rota `vault:page` removida apenas da instância em execução, mantendo `vault:legacy-vault-route`. Após recarga, o novo código de plugin não registra nav lateral.

## Preservação
- HEAD base `f1d5ab2f03`; checkout compartilhado. Sem commit, reset, stash, clean, push ou restart.
- Não houve alteração nas 79 tarefas upstream, nem no banco próprio do Workstation. O Vault iniciou vazio e terminou vazio.
- Durante o smoke, a interface foi restaurada à sessão `#/20261101_152355_b21925`, que estava ativa antes do último teste do dashboard.

## Limites
- A execução do arquivo `index.test.tsx` pelo Vitest permaneceu não comprovada devido ao runner já inconclusivo na missão anterior; os testes foram escritos, não devem ser reportados como aprovados.
- Não houve necessidade de separar o armazenamento do Vault: ele já usa persistência local independente. O objetivo desta etapa foi apenas integrar a navegação e preservar compatibilidade.
