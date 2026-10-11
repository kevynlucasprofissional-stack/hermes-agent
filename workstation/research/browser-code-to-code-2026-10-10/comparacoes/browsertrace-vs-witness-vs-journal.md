# Comparação Cruzada: BrowserTrace x Witness x Execution Journal do Hermes

## 1. Visão Geral Comparativa
Comparação das ferramentas de observabilidade, auditoria e replay:
- **BrowserTrace:** Comparação e diagnóstico de divergência entre execuções bem-sucedidas e falhas (`compare.py`).
- **Witness:** Medição contábil de custo em dólares (`pricing.py`), diffs de DOM e visualizador de replay em React.
- **Execution Journal:** Persistência determinística de receipts operacionais e amostras de transição.

## 2. Decisão de Integração
Adotar o módulo `pricing.py` do Witness para gerar a verdade financeira do TaskRun no Hermes, e o algoritmo de alinhamento de rastros do BrowserTrace para auxiliar o ExperienceCompiler a descartar ruído em tarefas com falha.
