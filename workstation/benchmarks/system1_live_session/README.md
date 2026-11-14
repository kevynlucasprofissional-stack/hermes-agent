# Teste real do Hermes System 1 Browser — sessão humana

**Situação inicial verificada (07/11/2026):** servidor local em execução na porta 18791; páginas /unique, /partial, /duplicate e /missing com HTTP 200 e rótulos corretos. Processo iniciado pelo script `Start-Fixture.ps1`, sem conexões externas, autenticação ou ações de escrita.

## Arquivos
- `fixture_server.py` — servidor HTTP somente em 127.0.0.1, sem cookies ou eventos externos
- `Start-Fixture.ps1` — idempotente; recusa porta usada por servidor desconhecido
- `Stop-Fixture.ps1` — finaliza somente o PID previamente registrado, verificando a linha de comando
- `PROMPT_HERMES_TESTE_REAL.md` — instrução de preparação para enviar em sessão dedicada do Hermes

## Comandos opcionais no PowerShell
```powershell
& 'C:\Github\hermes-agent\workstation\benchmarks\system1_live_session\Start-Fixture.ps1'
Invoke-RestMethod http://127.0.0.1:18791/health
# Depois da homologação:
& 'C:\Github\hermes-agent\workstation\benchmarks\system1_live_session\Stop-Fixture.ps1'
```

## Ordem
1. Em **sessão dedicada do Hermes**, envie o prompt de setup do arquivo `PROMPT_HERMES_TESTE_REAL.md`.
2. O Hermes deve conferir identidade, BrowserTask, runtime isolado e flag antes de dizer "PRONTO PARA FRASE EXATA".
3. Em **mensagem separada, sem prefixos, sufixos ou aspas**, envie:
   `Localize o botão Relatórios na página atual`
4. A página /unique mede caminho de rótulo exato (sem Laya); /partial exige proposta do Laya; /duplicate e /missing exigem fallback sem falsa confirmação.

**Advertência:** ambiente PM do Laya isolado existe, mas não está ativado no processo Hermes em uso. A flag `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED` permanece desabilitada por padrão. Este fixture **não habilita a rota** nem comprova custo/latência end-to-end. Não reiniciar Hermes produtivo, nem alterar sessão, permissões ou ledger para forçar o teste.
