# C2C-EC-HARNESS — Inventário de referências
Data da auditoria: 2026-10-11. Checkout: C:\Github\hermes-agent. Branch local: fix/hermes-oneclick-lock-startup-20261011, HEAD 9fffa7f3ffcc2c50774654c271fe25e92ce459e8. GitHub main e origin/main: a2b56db1bc9e0b5acf48d94fa86a9844a1005842. Não se alterou nenhum código produtivo.

## Escopo contado
Contagem obtida por os.walk dos diretórios e por zipfile.infolist() para o Activepieces. Manifesto individual em REFERENCE-FILE-MANIFEST.csv.gz (collection, project, path, bytes, classification, container); metadados em reference-inventory.json. Excluídos recursivamente do manifesto: .git, node_modules, __pycache__, .next, .venv, venv, dist, build, .turbo, .cache, target e coverage; caminhos dos subdiretórios excluídos constam de excluded_subtrees por projeto. A classificação de source é por extensão, portanto não equivale a revisão semântica. Não foram calculados hashes para cada um dos 147.365 arquivos; registraram-se os commits de cada clone e SHA256 do ZIP. O inventário é COMPLETO PARA A ÁRVORE NÃO EXCLUÍDA, não para metadados Git/dependências/gerados.

| Referência | Arquivos | Código (extensão) | Docs | Commit local |
|---|---:|---:|---:|---|
| OpenHands | 2.595 | 2.302 | 80 | e0a26af82f0b |
| Cradle | 507 | 242 | 11 | d7752fccf890 |
| DeerFlow | 3.810 | 3.227 | 424 | 38c55c67f601 |
| DeepSeek Harness | 14.988 | 9.338 | 4.484 | d74326738864 |
| OpenManus | 145 | 108 | 17 | 3309bf4e416f |
| LangGraph | 687 | 536 | 29 | b4991f1ba36a |
| OpenClaw | 53.402 | 46.563 | 2.274 | 00e095399b20 |
| Activepieces (ZIP) | 30.496 | 28.848 | 1.264 | SHA256 começa 0c237aee3b |
| SkillRL | 1.217 | 802 | 81 | 4d984d455b9b |
| Double Ratchet | 113 | 107 | 3 | 0f14e910d361 |
| Ratchet | 133 | 122 | 6 | 4401662ef477 |
| FlowEvo | 73 | 67 | 1 | 36e81efd4d1f |
| rethinkskill | 167 | 131 | 16 | 8252445918eb |
| Voyager | 457 | 243 | 189 | 55e45a880755 |
| n8n | 30.690 | 28.453 | 767 | 7424f0ca0452 |
| Trace2Skill | 6.856 | 44 | 547 | 3d0b52a140f0 |
| memorizz | 974 | 719 | 127 | 3feb42103140 |
| agent-workflow-memory | 55 | 32 | 17 | 8c0ff8cd11d6 |
| TOTAL | 147.365 | 121.884 | 10.337 | — |

## Critério de leitura e evidência
Neste ciclo, foram lidas implementações direcionadas e comparadas por fonte e função, NÃO os 121.884 arquivos classificados como código. Qualquer afirmação de cobertura semântica integral seria falsa. Evidências citam caminhos, símbolos e, quando inspecionados, linhas; onde faltou inspeção, recomendações são hipóteses. Não publicar cópias integrais de terceiros nem conteúdos privados de sessões.

## Estado do checkout
Git status registrou múltiplos arquivos modificados sob apps/desktop/src e registros de dogfood não rastreados, além de .tmp_kanban_backup.py; todos preservados. Não executar checkout, reset, clean, add -A, commit ou merge automaticamente. GitHub confirmou o commit a2b56db1... no main.

## Limitações
A inspeção estática não substitui teste nativo Electron, qualificação Laya real ou sessão produtiva com recibos de verificação. Python 3.14 acessível por py -3.14 não possui o módulo pytest; nenhum teste foi declarado aprovado nesta rodada. Status: AUDITORIA PARCIAL E REPRODUZÍVEL, não certificação integral.