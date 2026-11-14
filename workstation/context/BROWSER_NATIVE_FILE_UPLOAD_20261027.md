# Upload nativo do Browser — contrato operacional (2026-10-27)

**Status:** implementado localmente; não homologado para release. H-079 dispensado pelo mantenedor apenas para este ciclo de implementação local. Sem alterações de branch, reset, stash, commit ou push.

## Configuração explícita antes de usar

No arquivo `config.yaml` do perfil Hermes ativo (HERMES_HOME), um operador confiável deve incluir um grant com identidades reais da TaskRun e origem web. **Não atribuir permissões em branco ou raiz do disco.** Exemplo ilustrativo (trocar todos os valores conforme a sessão, origem, prazo e pasta específicos):

```yaml
browser:
  workstation:
    upload_grants:
      - task_id: "ID-DA-TAREFA"
        session_id: "ID-DA-SESSAO"
        run_id: "ID-DA-EXECUCAO"
        expires_at: "ANO-MES-DIAT23:59:00Z"
        allowed_roots:
          - "C:/Pasta/Especifica/Arquivos"
        allowed_origins:
          - "https://app.example.test"
        max_bytes: 52428800
        max_files: 10
```

`expires_at` precisa ser ISO8601 válido no futuro. A ferramenta falha com `upload_scope_required` quando não há grant válido ou quando a execução não corresponde; `upload_origin_denied` quando a aba do Browser não está na origem autorizada. O destino da página é verificado imediatamente antes de selecionar o arquivo e novamente após a resolução do input. O ID de tarefa padrão não recebe grant.

Os arquivos devem existir, ser regulares, ter caminho absoluto e estar sob raiz real autorizada, sem escape por symlink/junction; limite padrão 50 MiB/arquivo, 10 arquivos. Iframes e Shadow DOM não recebem bypass: somente um elemento HTMLInputElement[type=file] do frame principal, com correspondência CSS única.

## Fluxo e evidência

`tools/browser_workstation.py` expõe `browser_file_upload`; o runtime Electron realiza a seleção no Chromium embutido via `DOM.setFileInputFiles`. É uma ação mutável com autorização de controle humano/TaskRun, admission e replay bloqueado por ID de operação em caso de estado incerto. Após seleção, o runtime lê `FileList.length`, persiste receipt e responde apenas status `selected`, contagem e identificador de operação. Não divulga caminhos locais completos.

**Importante:** o site pode reagir ao evento `change` enviando arquivo automaticamente; portanto configure somente origens de confiança. O resultado `selected` comprova seleção no input local, **não** entrega ao site ou a contatos WhatsApp. Não liberar WA-M3, nem reinterpretar ausência de readback como permissão de retry.

## Evidência de testes

- RED antes do código: helper 4 falhas, integração runtime 3 falhas; origem adicional teve RED 1 falha.
- GREEN final: 68 testes Electron focados/regressivos em seis suítes.
- Electron/Chromium 144 em data: offline: 1 arquivo na FileList, 1 evento change; exit 0. A fixture comprova CDP real, não foi um E2E do aplicativo Hermes completo.
- Typecheck deve ser verificado novamente após cada alteração tipada; CI e E2E produto/canal real não executados aqui.

## Riscos restantes

1. `config.yaml` é editável por quem possui acesso de escrita ao perfil. O grant não constitui barreira contra um agente que já possa alterar livremente essa configuração.
2. `realpath` e `stat` reduzem symlink escapes, mas não eliminam totalmente races no filesystem entre validação e leitura CDP.
3. Requer teste E2E do Hermes Desktop completo no BrowserTask real antes de release. Não testar enviando mensagens reais ou fazendo postagens.
