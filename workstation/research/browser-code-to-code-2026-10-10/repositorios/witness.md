# Relatório de Auditoria Code-to-Code: Witness

**Projeto:** Witness (`EricFinland/witness`)  
**Commit SHA:** `2d3ccdcd6ce6a21356bfb9e1e2333036a1955b25`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/EricFinland--witness`  
**Licença:** **MIT** (`LICENSE`)  
**Stack:** Python (core `witness/`), React / Vite / Tailwind (`viewer/`)  
**Tamanho Auditado:** 17 arquivos TS, 30 arquivos Python, 10 testes  
**Classificação de Reuso:** **COPY / ADAPT** (Módulo de custos `pricing.py` e observabilidade)  

---

## 1. Identidade e Arquitetura

O Witness é uma ferramenta de observabilidade e auditoria para agentes de navegação web. Ele intercepta chamadas de LLM, ações de navegador e mutações de página, gerando:
1. Contabilidade precisa de tokens e custo financeiro por resultado (`pricing.py`).
2. Rastreamento e exportação OpenTelemetry (`otel_bridge.py`).
3. Diffs visuais e de DOM para comprovação de efeitos (`diff.py`).
4. Um visualizador web (`viewer/`) para replay passo a passo da execução do agente.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Contabilidade Financeira Exata de Execução (`pricing.py`)
- **Arquivo:** `witness/pricing.py`
- **Mecanismo:** Mantém uma tabela atualizada de custos por milhão de tokens de entrada/saída e por chamada de visão para todos os provedores modernos (OpenAI, Anthropic, DeepSeek, Google). Calcula o custo consolidado de cada TaskRun.
- **Aplicação no Hermes Work:** O Hermes Work possui diretrizes estritas no H-080A e nas regras canônicas exigindo **"verdade contábil de custo"** (*truthful cost accounting*). O módulo `pricing.py` pode ser incorporado diretamente ao `TaskRun` e ao `ExecutionJournal` do Hermes para atribuir custo exato por tarefa concluída.

### 2.2. Diffs e Redação de Dados Sensíveis (`diff.py`, `redact.py`)
- **Arquivos:** `witness/diff.py` e `witness/redact.py`
- **Mecanismo:** Mascara tokens, senhas e chaves antes de persistir o rastro, comparando o estado do DOM antes e depois de ações para confirmar se uma mutação realmente ocorreu no servidor remoto.

---

## 3. Recomendações Objetivas para o Hermes Work

- **COPY:** Adotar o cálculo de custo de `witness/pricing.py` dentro de `workstation/telemetry.py` ou `workstation/operational_telemetry.py`, fechando a exigência de medir o custo por resultado verificado.
- **ADAPT:** Integrar o viewer do Witness ao `task-journal-drawer.tsx` do Hermes Desktop, permitindo que o usuário assista ao replay visual de tarefas executadas pelo agente.
