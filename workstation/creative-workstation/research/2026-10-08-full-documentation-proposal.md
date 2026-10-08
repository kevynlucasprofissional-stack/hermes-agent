# Proposta original de organização documental — 2026-10-08

> **Fonte histórica:** segundo texto integral de proposta fornecido pelo usuário na conversa, iniciado por “Concordo com a criação da pasta...”. Apenas elementos gráficos de apresentação foram convertidos para Markdown comum. Esta transcrição é material de origem e não substitui decisões e estado técnico atuais.

Concordo com a criação da pasta `creative-workstation/`. Mas faria um ajuste importante: em vez de simplesmente copiar minha resposta anterior para um README, transformaria aquela análise em uma especificação técnica de produto, preservando o texto original como documento de referência.

Consultei a estrutura do seu repositório Hermes Agent, incluindo o roadmap, a arquitetura, a Source Matrix e as regras de desenvolvimento. A proposta se encaixa bem no projeto, desde que respeite os componentes e contratos já existentes.

## 1. Onde colocar a documentação

Eu usaria o caminho:

`hermes-agent/workstation/creative-workstation/`

E organizaria assim:

```text
workstation/
  creative-workstation/
    README.md
    ARCHITECTURE.md
    IMPLEMENTATION_PLAN.md
    INTEGRATIONS.md
    research/
      2026-10-08-original-analysis.md
```

- **README.md:** Visão geral, objetivos, escopo, prioridades e links para os demais documentos.
- **ARCHITECTURE.md:** Integração com Chromium, MCP, APIs, Creative Runtime, TaskCompiler e Experience Compiler.
- **IMPLEMENTATION_PLAN.md:** Etapas, dependências, arquivos afetados, critérios de aceitação e testes.
- **INTEGRATIONS.md:** Catálogo de ferramentas, MCPs, skills, licenças, compatibilidade e estado de verificação.
- **research/2026-10-08-original-analysis.md:** Texto integral da análise anterior, preservado como referência histórica.

A vantagem dessa estrutura é permitir que qualquer agente responsável pela implementação encontre rapidamente o que precisa, sem reler toda a discussão.

## 2. Integrar ao sistema de documentação existente

Seu Hermes já possui documentos canônicos. Não faria sentido criar novas fontes de verdade concorrentes.

| Documento existente | Alteração que recomendo |
| --- | --- |
| ROADMAP.md | Registrar Creative Workstation como iniciativa planejada, com dependências e milestones |
| SOURCE_MATRIX.md | Adicionar Penpot, Remotion, Three.js, Graphite e demais tecnologias, distinguindo referências de adoções aprovadas |
| HERMES_WORKSTATION_INTELLIGENCE.md | Registrar a visão estratégica: Hermes como ambiente criativo programável por agentes |
| DECISIONS.md | Registrar apenas decisões arquiteturais efetivamente aprovadas |
| engineering-journal | Documentar experimentos, implementações, problemas e resultados quando forem executados |

O README será o ponto de entrada da iniciativa, mas o `ROADMAP.md` continuará responsável pela priorização geral do Hermes Workstation.

## 3. Como implementar sem prejudicar o Hermes atual

Eu dividiria em cinco etapas.

**01 — Documentação e decisões**

Criar a pasta, preservar a análise, registrar as integrações candidatas e conectar a iniciativa ao roadmap. Nenhuma mudança funcional.

**02 — Contrato do Creative Runtime**

Definir como o Hermes descobre, instala, inicia, supervisiona e desliga uma ferramenta criativa, reutilizando o gerenciamento de processos, permissões e estados já existentes.

**03 — Primeiro fluxo criativo ponta a ponta**

Testar geração de projeto React/SVG, preview no Chromium, renderização e exportação por Remotion/FFmpeg, sujeito à validação da licença. Comprovar persistência e recuperação.

**04 — Integração dos editores visuais**

Adicionar Penpot via MCP e Three.js Editor via bridge tipada. Garantir que o humano possa modificar o projeto sem desincronizar o agente.

**05 — Capacidades operacionais reutilizáveis**

Conectar operações verificadas ao Experience Compiler. Introduzir templates e recipes certificadas com parâmetros, verificadores e invalidação de versões.

Há uma restrição relevante: o roadmap atual determina que as qualificações centrais H-080A/H-080B e os gates upstream-first tenham precedência sobre expansões amplas. Portanto, a documentação pode ser criada agora; as mudanças funcionais precisam respeitar os bloqueios e gates vigentes no momento de começar a implementação.

## 4. Como a integração deveria funcionar tecnicamente

Eu não criaria outro sistema independente de gerenciamento de agentes, sessões ou navegador.

O Creative Workstation precisa ser uma extensão das capacidades já existentes:

- `workstation/capabilities.py` e `workstation/control_plane/`: classificação e encaminhamento das operações.
- `workstation/task_compiler.py`: decomposição de tarefas criativas.
- `workstation/experience_compiler/`: aprendizagem e reutilização após validação.
- `apps/desktop/`: apresentação das interfaces visuais, reutilizando o Chromium integrado.
- `workstation/components.lock.json`: identificação e controle de componentes externos quando aplicável.

Esses são pontos de investigação e integração, não uma autorização para modificá-los todos. A fase de implementação deve primeiro confirmar os contratos atuais do código e minimizar o número de alterações first-party.

Por exemplo, ao solicitar:

> Crie uma logo 3D animada, com iluminação e exportação para vídeo.

O Hermes deveria reconhecer as capacidades exigidas, verificar dependências, montar a cena Three.js, abrir a prévia, aplicar alterações e produzir o vídeo por um pipeline compatível. Depois, a execução comprovada poderia gerar uma candidata à reutilização operacional.

Isso aproveita o Hermes existente em vez de construir um segundo agente dentro dele.

## 5. Como eu faria o primeiro commit

A primeira entrega seria exclusivamente documental, numa branch própria, com algo como:

`docs/creative-workstation-foundation`

Critérios de conclusão:

- README e documentos específicos criados.
- Análise original preservada, sem confundir hipóteses com fatos verificados.
- Tecnologias e integrações registradas com origem, licença e estado de validação.
- Roadmap e Source Matrix atualizados com referências à nova pasta.
- Nenhuma alteração de runtime, instalação automática ou dependência introduzida.
- Links internos e consistência documental verificados.

Sugestão de commit:

`docs(workstation): establish creative workstation architecture and implementation plan`

A partir desse commit, qualquer IA que trabalhar no Hermes poderá receber uma instrução curta apontando para `workstation/creative-workstation/README.md`, e de lá chegar aos contratos e tarefas específicas.

## Minha recomendação

Sim, crie a pasta. E preserve integralmente a análise anterior. Só não a transforme diretamente na especificação oficial sem separar fatos confirmados, propostas e hipóteses.

Eu trataria o `creative-workstation/` como um subprojeto planejado e documentado dentro do Hermes Workstation, não como um produto independente ou uma nova arquitetura concorrente.

O primeiro objetivo seria deixar o repositório suficientemente claro para que outro agente consiga implementar a iniciativa em pequenas entregas verificáveis, respeitando a arquitetura atual, sem depender de reler nossas conversas.

Esse é o próximo passo que considero mais adequado.
