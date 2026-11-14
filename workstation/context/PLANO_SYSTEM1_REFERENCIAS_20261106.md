# Hermes Work — Plano de integração incremental System 1 (06/11/2026)

> **Para agentes implementadores:** seguir Superpowers (planejar → teste RED → código mínimo → GREEN → verificação) e community-agent-workflows/ECC. Executar uma tarefa por vez; não considerar este documento uma autorização de merge, push ou alteração de permissões.

**Objetivo:** reduzir latência e chamadas desnecessárias ao System 2 em operações frequentes do Hermes Work sem perder correção, segurança, continuidade ou capacidade de recuperação.

**Estratégia:** manter os owners atuais (BrowserTask, CapabilityRouter, System1DecisionProvider, TaskRun, Policy/Verifier, ExperienceCompiler). Usar os repositórios de `referências/05-System-1` como referências auditáveis, copiando apenas soluções específicas quando agregarem valor. Priorizar um fluxo real do Browser; expandir somente com benefício medido.

**Stack:** Python 3.13 / Laya 0.3.23 existente; Electron/TypeScript/Chromium; pytest/Vitest; benchmark local Windows 11. Configurações de comportamento via `config.yaml`, sem novos serviços residentes obrigatórios.

**Contexto canônico:** `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md`, `CURRENT_STATE.md`, `KNOWN_ISSUES.md`, `workstation/ARCHITECTURE.md`, `workstation/context/LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md` e `workstation/context/HERMES_NATIVE_BROWSER_RELIABILITY_MASTER.md`. Documentos antigos que descrevem Stage A como obrigatório estão supersedidos: Stage A/H-079 é opcional para desenvolvimento local; critérios de segurança e qualificação da entrega continuam necessários.

## Estado observado na elaboração

- Checkout `C:\Github\hermes-agent`, `main@f1d5ab2f03`, com **pelo menos 77 arquivos versionados modificados** no inventário só de leitura (excluídos untracked); outras mudanças concorrentes são possíveis. Não trocar de branch, resetar/stash/limpar ou sobrescrever arquivos sem checar o estado atual e os escritores.
- 10 referências em `referências/05-System-1`: nove clones recentes e `NandhaKishorM--laya` preexistente. Nenhuma é automaticamente uma dependência instalada.
- Owners existentes: `agent/system1_decision.py` (`DecisionRequest`, `DecisionResult`, `decide_system1`); `workstation/system1/laya_provider.py`; `workstation/system1/calibration.py`; `workstation/system1/dataset.py`; `workstation/integrations/hermes/adapter.py`; `workstation/control_plane/router.py`; `workstation/experience_compiler/compilability_monitor.py`.
- O Browser já expõe elementos com referências através de `apps/desktop/electron/workstation-browser-runtime.ts` e `browser_snapshot`, com despacho em `tools/browser_workstation.py`. Não substituir `WebContentsView`, `BrowserTask`, admissões, leases ou recuperação.
- Decisão System 1 não concede autoridade; pontuação/confiança não é prova de efeito; execução não verificada permanece incerta. O monitor de compilabilidade opera com SHADOW por padrão e DIRECT somente com qualificação autenticada.

## Critérios de aceite do primeiro MVP

1. **Segurança/compatibilidade:** zero efeitos não autorizados, zero replay automático de mutações incertas; respeito a lease humano, tarefa/sessão, DOM desatualizado, cancelamento e política existente. Sem regressão observada do fluxo atual.
2. **Correção observável:** completar o mesmo conjunto de tarefas de navegação/leitura de baixo risco usando Browser nativo, com verificação independente do estado final; não contar `DONE` do modelo como sucesso.
3. **Benefício medido:** registrar p50/p95 de latência, chamadas System 2, fallback/abstenção e custo por resultado verificado; só ativar a rota rápida se houver ganho líquido relevante sem reduzir a taxa de sucesso. Até lá, SHADOW.

## Entrega 0 — Baseline reproduzível (obrigatória, sem novas dependências)

**Trabalho:**
- Mapear contrato real do snapshot/refs, admissão da BrowserTask e interface de `DecisionRequest` no HEAD de trabalho; confirmar posse de arquivos modificados antes de editar.
- Selecionar um conjunto pequeno e representativo de tarefas **autorizadas, somente leitura**: navegação, localizar botão/aba, abrir página, procurar informação e decidir esperar. Incluir pelo menos: DOM alterado, alvo ausente, operação ambígua, falha do modelo e takeover humano. Sanitizar snapshots para não armazenar segredos/PII de terceiros.
- Reutilizar telemetria e `workstation/benchmarks/` para guardar uma linha-base instrumentada de p50/p95, System 2 e resultado verificado. Se o fluxo de Browser nativo não funcionar, registrar o bloqueio específico e não inventar benchmark.

**Arquivos candidatos:** `workstation/benchmarks/`, `workstation/tests/test_system1_contracts.py`, `workstation/tests/test_system1_safety.py`, `apps/desktop/electron/workstation-browser-runtime*.test.ts`. Localização final dos testes depende do contrato encontrado.

**Aceite:** existe evidência repetível da linha-base e de um fluxo real (não apenas mocks). Se faltar Browser operacional, fazer somente a comparação de decisão offline, marcada como parcial.

## Entrega 1 — Fast path System 1 para Browser (MVP principal)

**Referências primárias:**
- `referências/05-System-1/browser-use--jev-ultrafast/jev_ultrafast/{snapshot.js,model.py,agent.py}`: espaço de ações indexadas, escolha de operação+alvo, fresh-check, abstenção.
- `referências/05-System-1/ThinkFlowLab--system1-agents`: cenários comparativos e avaliação de decisão agente vs LLM.

**Implementação mínima proposta:**
1. Criar um **adaptador pequeno de propostas**, sob `workstation/system1/`, que recebe o snapshot autorizado existente + objetivo resumido e constrói `DecisionRequest` com um conjunto limitado de operações e referências válidas. Sem comandos JS, CSS arbitrário, URLs, shell ou efeitos produzidos pelo modelo.
2. Usar o Laya existente para escolher operação/elemento ou abster-se. Preservar o caminho determinístico/System 2 em timeout, baixa confiança, alvo ausente, incerteza ou schema inválido. Começar em SHADOW, somente registrar propostas.
3. Integrar seletivamente no ponto de orquestração **já existente** entre snapshot e `browser_*`, mantendo as verificações reais de acionabilidade, estado, lease e `TaskRun`; não criar navegador ou executor paralelo.
4. Somente depois do replay SHADOW e da homologação, liberar a rota para navegação/leitura autorizada. Cliques que possam disparar efeitos de escrita não entram automaticamente na categoria READ.
5. Medir novamente os casos da Entrega 0; comparar p50/p95, System 2 e verificação final. Reverter apenas a nova rota em caso de regressão; preservar a linha-base.

**Testes RED→GREEN:** proposta válida aponta para ref observada; ref stale é rejeitada; input adversarial não vira código/selector; falha/abstenção cai no caminho anterior; lease/cancelamento e operação mutante não são contornados; resultado final exige readback. Um E2E nativo com página de teste prova o trajeto real, inclusive foreground/background onde aplicável.

**Aceite:** rota rápida operacional em pelo menos um cenário read-only real; melhoria mensurável contra a mesma tarefa e ambiente; nenhuma regressão nos testes de autoridade e recuperação. Não ativar por percentual de confiança inventado.

## Entrega 2 — Benchmark de modelos e execução local (somente se Entrega 1 revelar gargalo de inferência)

**Referências:** `ollaya-dev--ollaya`, `receptron--laya`, `firelex--jeff`, `NandhaKishorM--laya`.

- Comparar Laya Python já registrado vs Ollaya/Laya e, se justificável, Laya ONNX Node no Windows. Jeff entra como candidato especializado apenas se houver dados rotulados compatíveis.
- Mesmos exemplos e splits por tarefa; distinguir accuracy, abstenção, ECE/calibração, p50/p95 e RAM/VRAM; testes com textos em português.
- Não iniciar daemon obrigatório no boot nem trocar dependências do produto por benchmark. Se o Laya existente for suficientemente bom, **não integrar Ollaya/Receptron/Jeff**.

**Aceite:** decisão documentada baseada em medições locais e conjunto rotulado. Se não houver ganho, encerrar esta frente sem código de produção.

## Entrega 3 — Roteamento LLM mais econômico (independente; após ganho do MVP)

**Referências:** `mmornati--system-one-router` e `vllm-project--semantic-router`.

- Inspecionar o roteamento real do Hermes (`workstation/control_plane/router.py`, `workstation/runtime.py`, `agent/operational_resolution.py`) e a telemetria disponível. Manter o roteador canônico, perfil, privacidade e exclusões de provedores.
- Apenas quando o roteamento atual usar System 2 indevidamente para decidir a próxima capability/modelo, adicionar classificação System 1 de complexidade/risco/provedor permitido e ranking **dentro das opções já autorizadas**.
- Medir custo por tarefa verificada e qualidade das respostas; fallback imediato se classificação incorreta ou privada.

**Aceite:** custo ou latência menor com qualidade e restrições preservadas. Não introduzir gateway vLLM ou sistema alternativo de credenciais.

## Entrega 4 — Aprendizado operacional verificado (condicionada)

**Referências:** `solvi-ai--solvi` (hard checks, evidência e calibração), `ThinkFlowLab--system1-agents`, padrões especializados de `firelex--jeff`.

- Reutilizar `workstation/experience_compiler/compilability_monitor.py`, `workstation/system1/dataset.py` e `workstation/run_adoption.py`. Identificar a **primeira família real** com exemplos VERIFIED_SUCCESS, replay independente e verificador válido; não treinar com simples observações `uncertain`.
- Calibrar com conjunto held-out separado, permitir oferta/abstenção e validar a adoção no mesmo TaskRun, sem novo owner de autoridade.
- Provar com cenário real que dois itens equivalentes executam sem nova chamada desnecessária ao System 2, com recibo independente por item; se não houver ambiente de validação real, manter SHADOW.

**Aceite:** reutilização realmente verificada, medição de System 2 evitado, nenhum efeito duplicado ou promoção sem prova.

## Adiado explicitamente

- `tinnel123666888--OmniJev`: percepção visual para Canvas/PhotoCraft/EffectCraft somente quando DOM/acessibilidade atuais se mostrarem insuficientes; comparar uma tarefa real antes de integrar GPU.
- Adotar a stack inteira de `vllm-project--semantic-router`, reimplementar Jeff, criar outra memória/DB/Browser/executor, alterar upstream ou reconstruir dashboard: **não fazem parte deste plano**.
- Problemas como ACIRV Database 404, recuperação de operações incertas ou agendamentos perdidos exigem frentes próprias; System 1 não deve ser usado como disfarce para correções transacionais.

## Sequência e paradas

**Ordem:** Entrega 0 → Entrega 1 → avaliar resultado. Se o ganho não se confirmar após duas iterações, reduzir o MVP à classificação offline, registrar o resultado e encerrar a tentativa de integração até surgir nova evidência. Entregas 2–4 são oportunidades posteriores, não gates que bloqueiam o MVP.

**Verificação final obrigatória para cada mudança:** teste focado RED/GREEN, regressões necessárias, fluxo nativo real quando aplicável, preservação de mudanças preexistentes, hashes/identidade de branch e status honesto de CI. Não confundir build, mocks, benchmarks de terceiros ou README com funcionamento do Hermes.

**Execução autorizada por este documento:** nenhuma; esta entrega é apenas um plano de trabalho, sem instalação, modificação de runtime, commit, push ou merge. Antes de implementar, verificar o estado atual e coordenar alterações em arquivos compartilhados.
