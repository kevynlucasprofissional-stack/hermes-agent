# Dogfood — amostras reais e limites do diagnóstico
Fonte local: workstation/dogfood/dados/Sessões Hermes/*.json; 55 arquivos legíveis. Agregação sem publicar conteúdos brutos em dogfood-session-aggregate.json. Este arquivo contém somente nomes dos arquivos, quantidades por role/tool e contagens de marcadores textuais; não contém mensagens nem HTML.

## Totais observados
55 sessões exportadas, 14.688 mensagens, 8.064 mensagens role=tool. ATENÇÃO: o número de eventos de ferramenta não é número de chamadas de provider nem custo monetário; dados agregados podem conter duplicidade de exportações/sessões.

| Sessão | Eventos role=tool | Amostra de chamadas por família |
|---|---:|---|
| open-trello-20261009.json | 470 | browser_console=180, read_file=97, terminal=93, browser_navigate=35, search_files=24, browser_snapshot=4 |
| abrir-hyperframe-20261009.json | 191 | terminal=62, read_file=39, skill_view=28, patch=27, search_files=10 |
| abrir-creative-workstation-20261011.json | 17 | tool_search=4, search_files=4, read_file=4, desktop_project=1, apply_layout=1 |

Marcadores textuais detectados dentro de mensagens NÃO constituem prova de que o pipeline usou o compilador. Nem totais de ferramenta demonstram oportunidade segura de compilação. É necessário correlacionar eventos por task_id, run_id, operation_id e evidence_ref com ArtifactStore, ExperienceCorpus e telemetry.

## Oportunidades candidatas, NÃO comprovação de aprendizagem
- Trello: repetição de consultas de console, navegação e leitura sugere pesquisa de fast paths de leitura, APIs autorizadas, estado semântico e batch retrieval. Não propor macro de clique sem readback/lease/URL/família.
- Hyperframes: repetições de leitura, terminal e skill_view sugerem otimização de acesso a arquivos, caches por hash/ref e compactação dos resultados; conclusão semântica da tarefa permanece na LLM.
- Creative Workstation: baixo volume, mas descoberta repetida de ferramentas é candidata a registry/prefab awareness e pre-LLM lookup.

## Experimentos seguros recomendados
1. Sessão sintética READ em site estável: capture owner evidence, Laya labels e match de intenção; reporte eligibility reasons.
2. Filesystem temporário: 3 casos equivalentes com readback, 4º item com gate DIRECT family-scoped, negativo por escopo, replay isolado.
3. Browser read-only: URL/snapshot owner independente, drift deliberado, sem usar dados privados.
4. Cronometrar efeitos de reutilização no mesmo TaskRun; medir LLM calls reais; não estimar por browser_console count.

## Lacunas
Não foram lidos neste ciclo todos os corpos das 55 sessões ou artefatos históricos; foi feito inventário agregado seguro. Sem prova do estado do registry/corpus de produção e sem replay de TaskRun real, não se pode atribuir cada evento repetido a uma capacidade que deveria ter sido promovida. pytest não está disponível em py -3.14; gates locais não foram reexecutados nesta rodada.