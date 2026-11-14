# Hermes Workstation — Dashboard central e Database (01/11/2026)

## Decisão substitutiva
O Workstation é **uma única entrada lateral**, não módulos avulsos no menu. O destino `/browser` abre o dashboard inicial; `/browser?module=browser` preserva a interface de navegador; `/browser?module=database` abre Database. Links antigos `/workstation/kanban` redirecionam à Database quando o plugin é recarregado. A rota de acesso criativo `?creative=1` mantém abertura direta do navegador.

**Database** é o domínio; Kanban e Tabela são apenas duas visualizações dos mesmos registros, com consultas e mutações compartilhadas. Não regressar a One State Hermes.

## Código alterado nesta missão
- Novo `apps/desktop/src/app/workstation/index.tsx`: dashboard, seleção de módulo, navegação por URL e montagem sob demanda.
- `apps/desktop/src/app/contrib/surfaces.tsx`: dois encaixes cirúrgicos: rota existente de Browser/Workstation passa a montar `WorkstationHub`, em vez de BrowserView diretamente.
- `apps/desktop/src/plugins/workstation-board/plugin.tsx`: não registra mais item lateral; mantém bind de API e redirecionamento compatível do link legado.
- `apps/desktop/src/plugins/workstation-board/board.tsx`: nome Database, seleção de base e alternância Kanban/Tabela; tabela usa `fetchBoard` e `moveCard`/`editCard` existentes; nenhuma duplicação de dados.
- `apps/desktop/src/app/chat/right-rail/preview-pane.tsx`: pop-out navega diretamente para `?module=browser` para preservar acesso ao navegador.
- Novo teste de navegação `apps/desktop/src/app/workstation/index.test.tsx` (não concluído no runner nesta sessão).

## Dados preservados
- Banco Workstation `<HERMES_HOME>/workstation/board.sqlite` (esquema interno legado `boards/columns/cards`), 1 base e 1 registro. `PRAGMA integrity_check=ok`.
- Banco upstream `<HERMES_HOME>/kanban.db`, 79 tarefas, integridade ok. **Nenhum registro transferido ou excluído**.
- Uma edição temporária de teste na descrição foi revertida pela API; revisão final do registro: 6.
- `apps/desktop/src/app/browser/index.tsx` já modificado por outra missão: **não tocado**. Browser original é montado sem modificações.
- Não fez reset, stash, clean, commit, push ou restart.

## Evidências executadas
- ESLint dos arquivos relacionados: 0 erros.
- Cinco arquivos JSX/TSX transformados pelo esbuild: parse OK.
- `pytest -q tests/workstation/test_kanban_local.py`: 3 passed, 1 aviso não bloqueante do Starlette.
- AI Control real: dashboard `#/browser`; módulo Database `#/browser?module=database`; tabela contém o registro existente; alternar pelo botão INTERNO para Kanban preserva o mesmo registro e a rota.
- Edição real a partir do editor da Tabela atualizou a API com revisão 5; descrição revertida usando a API, revisão 6.
- Browser existente exibido sob `#/browser?module=browser`; retorno a `#/browser` mostrou dashboard. Sidebar antiga `workstation-board:navigation` removida **da instância em execução**; a mudança durável está em `plugin.tsx`.
- Vitest de dashboard iniciado, mas seu runner ficou sem concluir; não considerar teste aprovado. Typecheck integral também não qualificado.

## Intake Trello 04/11/2026 — dados institucionais (PENDENTE; não implementado nesta revisão)
- Fontes: [ACIRV + VCOM #934](https://trello.com/c/XeiqfGoN/934) e checklist do [#944](https://trello.com/c/gZy747hA/944), ambos abertos na lista Quarta. O item Database do #944 repete o objetivo do #934: **uma entrega, não duas importações independentes**.
- Requisito: tornar bases autorizadas da ACIRV pesquisáveis e visualizáveis em `/browser?module=database`, reutilizando o módulo Database existente e sem substituir o Kanban independente, criar store paralelo ou importar dados pessoais para contexto público.
- Dependência possível, **não bloqueio automático**: [curadoria #933](https://trello.com/c/ln2RMJPt/933) (pesquisas, Doity, ACIRV Check-in, SudoExpo Match, associados e relatórios mensais: seis itens ainda desmarcados no Trello), e [centralização #821](https://trello.com/c/YEZuSElM/821). A presença real dessas fontes no Git/HD não foi verificada nesta revisão.
- **MVP Quality First:** selecionar uma fonte real autorizada e representativa; mapear schema/chave/proveniência; carregar via caminho existente, observar registros na Tabela/Kanban quando aplicável e uma visualização/consulta útil; conferir persistência após recarregar, integridade, permissões e ausência de duplicação. Expandir às demais fontes apenas depois do fluxo mínimo verificado.
- **Estado:** backlog do Trello; código/importador, execução, volume e cobertura **não auditados nesta atualização documental**. Não alterar o status de implementação do MVP de dashboard acima.

## Pendências posteriores ao MVP
- Validar `index.test.tsx` em runner saudável e typecheck sob ambiente estável, sem bloquear o uso atual.
- Portar checklists, histórico, arquivo e delegações opcionais do Hybrid antigo, conforme uso e risco; **somente depois** remover modificações correspondentes do upstream.
- Migrar oportunamente nomes internos de `boards/cards` para entidades Database/Record **sem duplicar armazenamento ou perder dados**; não é bloqueio do MVP.
- Avaliar Vals e demais módulos em missões separadas, dentro do dashboard central e sem novas entradas laterais.
- O código antigo híbrido já tinha duas falhas de teste (rota `/hybrid/boards` e `_handle_hybrid` ausentes). Ver `WORKSTATION_KANBAN_DECOUPLING_20261101.md`.
