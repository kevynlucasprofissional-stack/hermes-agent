# Matriz Code-to-Code — aprendizagem e Experience Compiler
Alvo: workstation/experience_compiler/{compiler,corpus,segmentation,generalization,causal,hierarchical,lifecycle,promotion}.py, workstation/operational_capabilities.py, workstation/control_plane/router.py. Referências em referências/06-Experience-Compiler.

| ID | Código externo inspecionado/localizado | Mecanismo | Comparação com Hermes | Veredito |
|---|---|---|---|---|
| EXP-01 | amazon-science--Self-Evolving-Agents-Ratchet/skillevo/router/selector.py:1–55 | SkillSelector usa score ponderado de retrieval e SkillStats | Hermes já tem router de capacidade por contrato; ranking de UTILIDADE pode ser útil como desempate entre opções JÁ elegíveis, nunca substitui admission/verifier | ADAPT |
| EXP-02 | amazon-science--Self-Evolving-Agents-Double-Ratchet/vendor/skillevo/router/{router,selector}.py | Distribuição empacotada do SkillEvo; recuperar diferenciais de ratchet duplo antes de assumir ganho | Separar inovação real do código vendorizado; não duplicar ranking do Ratchet | INVESTIGATE |
| EXP-03 | aiming-lab--SkillRL/agent_system/memory/skill_updater.py:1–65 | Gera skills com LLM a partir de trajetórias falhadas; usa AzureOpenAI/o3 | Difere de ExperienceCompiler.compile() determinístico: bom para candidate lessons, não para promoção automática de código executável | INSPIRE |
| EXP-04 | DEFENSE-SEU--FlowEvo/src/compiler/workflow_memory_compiler.py:1–67 | Gera resumo textual determinístico de traces marcados success, incluindo repair stages e primeiro erro | Complemento para human-readable learning review, não substitui OperationalCapability, readback e gates | ADAPT |
| EXP-05 | HKUST-KnowComp--rethinkskill/src/rethinkskill/runtime/runner.py:1–65 | Orquestra avaliação com autoridade explícita, manifestos, recibos congelados e call accounting | Aplicação promissora para separar inferência, avaliação e validade de relatórios; ver requisitos de recibo em code-to-code | INSPIRE |
| EXP-06 | MineDojo--Voyager/voyager/agents/skill.py:1–65 | SkillManager persiste código/descrições, busca embeddings em Chroma e valida contagem | Retrieval é alternativa à lista de capabilities, mas embeddings aproximados não autorizam efeitos; use como geração de CANDIDATOS | ADAPT apenas retrieval |
| EXP-07 | Qwen-Applications--Trace2Skill/skill_evolver/skill_evolving_agent.py:1–65 | Refina skill a partir de erros, gera diffs e operações estruturadas | Incorporar diff/rollback e proposed revision; exigir novo fingerprint/verifier do Hermes | INSPIRE |
| EXP-08 | RichmondAlake--memorizz/src/memorizz/ui/routers/traces.py:1–65 | Página de traces com waterfall/health/lineage, filters e redaction | Painel read-only para Experience funnel é oportunidade de UX; licença PolyForm Noncommercial impede presumir reutilização de código comercial | INSPIRE, NÃO COPIAR |
| EXP-09 | zorazrw--agent-workflow-memory/mind2web/workflow/retrieve.py:1–65 | Armazena workflows textuais e recupera via FAISS/embeddings por site | Bons sinais de candidate matching, mas corpus/roteamento precisam de confiança e scope canônicos | INSPIRE |
| EXP-10 | n8n-io--n8n/packages/core/src/execution-engine/workflow-execute.ts:1–125 | Executor de workflows tipados, partial execution e run state | Comparar composição/visibilidade com Kernel; NÃO incorporar segundo motor | KEEP/INSPIRE |
| EXP-11 | activepieces-main.zip:packages/core/execution/src/lib/flows/flow-version.ts:1–36 | FlowVersion DRAFT/LOCKED com schema Zod e trigger | Boa referência para versão draft e revisão de capability; diferente de lifecycle discovered/validated/promoted | ADAPT dados, não autoridade |

## Propostas implementáveis
A. Adicionar ranking de utilidade pós-admissão e métricas de exposição (base em Ratchet) sem permitir selecionar capability não certificada.
B. LearningReview de falhas/contraprovas com trechos explicativos para usuário; não usar texto como evidence of success.
C. Criar diff de revisões e rationale inspecionável baseado em Trace2Skill + workflow versions, mantendo capability registry/artefatos existentes.
D. Criar traces timeline read-only com lineage e razões de negação; pode ser original, inspirada em memorizz, sem copiar código protegido.
E. Usar vetor/embedding para candidatos de read-only e detecção aproximada, mas routing final sempre requer typed intent, exact contract, owner, verifier, tenant/TaskRun.

## Restrições de licenciamento
memorizz é PolyForm Noncommercial 1.0.0 conforme LICENSE; n8n usa Sustainable Use License com exceção enterprise; Activepieces possui MIT Expat no core e diretórios EE sob licença separada. Reutilização de algoritmos/artefatos de ideias é diferente de importar código; confirmar licenças e terceiros por arquivo. Não foi concluída auditoria jurídica das demais referências.

## Limite da análise
Tabela cobre implementações específicas verificadas, não prova equivalência de todos os algoritmos nos 10 projetos. Requer aprofundar Double-Ratchet, benchmarks e regimes de avaliação antes de estabelecer ranking absoluto.