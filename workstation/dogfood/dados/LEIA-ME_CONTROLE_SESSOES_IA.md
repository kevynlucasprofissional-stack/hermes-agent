# Controle canônico — sessões Claude Code e relatórios de IA

Verificação inicial: **23/10/2026**. Escopo: 60 históricos JSONL brutos arquivados.

## Resultado auditado

| Condição | Total |
|---|---:|
| Sessões distintas indexadas | 60 |
| Sessões com relatório vinculado | 60 |
| Relatórios novos, um por sessão | 31 |
| Sessões cobertas por relatórios preexistentes | 29 |
| Backups de transcrições sincronizados no momento da última conferência | 60 |
| Erros de integridade na conferência | 0 |

Há **61 arquivos Markdown** na pasta de relatórios: 30 antigos e 31 novos. Dois antigos são cópias idênticas de um relatório de análise comparativa; os relatórios legados não estão obrigatoriamente em relação um-para-um com os IDs de sessão.

**Atenção:** ter um relatório vinculado não significa que todos os critérios de aceite de engenharia da sessão foram atingidos. Os documentos diferenciam intenção, operações registradas, conclusões reportadas e validação. O controle prova a existência e o vínculo dos artefatos, não a verdade de qualquer afirmação técnica sem evidência.

## Arquivos de controle

- CONTROLE_SESSOES_IA.json — fonte estruturada, indexada por UUID, com hash SHA-256, caminhos e método de vínculo.
- CONTROLE_SESSOES_IA.csv — consulta prática em tabela.
- atualizar_controle_sessoes_ia.py — reconciliador reutilizável sem edição do código do Hermes.
- AUDITORIA_COBERTURA_SESSOES_2026-10-23.md/.csv — **fotografia anterior** à geração dos relatórios, agora superada pelo controle canônico.

## Atualização

No PowerShell:

    python "C:\Github\hermes-agent\workstation\dogfood\dados\atualizar_controle_sessoes_ia.py"

O script compara a pasta de relatórios, os JSONL arquivados e os históricos originais da pasta do usuário. Informa quando:

- há relatório para uma sessão, confirmado por vínculo armazenado e hash;
- o relatório foi removido ou alterado desde a última conferência;
- um histórico bruto ainda não foi arquivado;
- o backup está desatualizado em relação ao Claude Code.

Para atualizar também os arquivos de backup antes da conferência:

    python "C:\Github\hermes-agent\workstation\dogfood\dados\Sessões Claude - BRUTO\backup_sessoes_claude.py"
    python "C:\Github\hermes-agent\workstation\dogfood\dados\atualizar_controle_sessoes_ia.py"

As sessões ativas continuam recebendo mensagens, portanto o status de sincronização é sempre válido **no instante da execução**. Um relatório existente pode se tornar historicamente desatualizado quando a sessão continua; nesse caso é necessária nova auditoria ou atualização do documento.

## Critérios de correspondência

1. **ID_EXATO:** o relatório novo traz o UUID da sessão original no cabeçalho (prova de vínculo individual).
2. **COBERTURA_TEXTUAL_VERIFICADA:** para relatórios antigos, correspondência extensa de texto do relatório no transcript original.
3. **REFERENCIA_EXPLICITA:** para dois relatórios de análise comparativa, os UUIDs são citados como fontes no documento compartilhado. Isso não comprova cobertura exaustiva de todos os turnos.

Não é apropriado considerar dois documentos equivalentes apenas por título ou data.

## Segurança e preservação

Os registros brutos podem conter código, comandos e dados privados. Não fazer commit de JSONL nem do backup no GitHub; o diretório bruto contém um arquivo .gitignore. Os relatórios e controles foram **salvos localmente e não foram commitados**. Os 30 relatórios preexistentes foram preservados.

Os relatórios novos são auditorias estruturadas a partir dos logs, com referências a linhas da transcrição e limites de evidência declarados. Não substituem testes executados contra o runtime atual.

## Revisão qualitativa (23/10/2026)

Os 31 relatórios novos foram reescritos como sínteses críticas, após leitura dos históricos e conferência de partes do código atual. As versões iniciais de extração automática estão preservadas em `Sessões Claude - BRUTO\VERSOES_ANTERIORES_RELATORIOS_AUTOMATICOS` e não compõem a pasta principal de relatórios.

O parecer `Relatório de sessões de IA\09_Auditorias-Testes\PARECER_CONSOLIDADO_QUALIDADE_CODIGO_2026-10-23.md` registra a avaliação transversal de qualidade. Foram observados **61 testes Python aprovados**, outro conjunto de **20 aprovados e 5 ignorados**, além de **6 erros de TypeScript no typecheck do Desktop**. Portanto, a existência de relatório não significa código completamente validado ou implementação pronta para produção.

No controle JSON/CSV, o campo `avaliacao_conteudo` distingue sínteses qualitativas novas de relatórios legados não revisitados. O campo `sha256_jsonl_no_ultimo_relatorio` permite detectar histórico bruto que mudou após a base da auditoria. Quando isso ocorre, a situação passa a `RELATORIO_POSSIVELMENTE_DESATUALIZADO`; esse status significa que o documento existe, porém seus resultados podem não incluir turnos novos.
