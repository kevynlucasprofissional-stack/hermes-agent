# Relatório de Auditoria Code-to-Code: Driftlock

**Projeto:** Driftlock (`VasuBansal7576/driftlock`)  
**Commit SHA:** `917396a43ca18d77124cf0cf099045cbf4afc90f`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/VasuBansal7576--driftlock`  
**Licença:** **MIT** (`LICENSE`)  
**Stack:** JavaScript / Node.js ESM (`.mjs`), TypeScript  
**Tamanho Auditado:** 2 arquivos TS, 10+ módulos MJS, 2 arquivos de teste  
**Classificação de Reuso:** **ADAPT / COPY** (Perfeito para alimentar a detecção de drift do `OperationalKernel`)  

---

## 1. Identidade e Arquitetura

O Driftlock é uma biblioteca especializada em diagnosticar, classificar e reparar **quebras de automação causadas por mudanças de layout e design** (*UI Drift*).

Em fluxos operacionais compilados, o problema número um é a volatilidade dos seletores: quando o site atualiza seu código front-end (ex: novas classes de Tailwind, renomeação de IDs, troca de ordem de nós), automações estáticas quebram imediatamente.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Classificação e Diagnóstico de Drift (`diagnose.mjs`)
- **Arquivo:** `driftlock/lib/diagnose.mjs`
- **Símbolo:** `diagnoseDrift(baseline, current): DriftVerdict`
- **Mecanismo:** Compara o estado da página gravado no momento em que a automação foi bem-sucedida (*known-good baseline*) com o estado atual da página quando a ação falha. Ele classifica o drift em quatro categorias formais:
  1. `COSMETIC`: Mudança apenas de estilos/cores (a ação ainda pode prosseguir).
  2. `LAYOUT_SHIFT`: Elemento mudou de posição ou container pai.
  3. `RENAMED_ATTRIBUTES`: Atributos de acessibilidade ou IDs mudaram.
  4. `STRUCTURAL_BREAK`: O elemento foi removido ou o fluxo de negócio mudou radicalmente.

### 2.2. Protocolo de Veredito (`drift-verdict.schema.json`)
- **Arquivo:** `driftlock/protocol/drift-verdict.schema.json`
- **Mecanismo:** Retorna um objeto JSON padronizado com diagnóstico e recomendação:
  - `REPAIR_SELECTOR`: Reparo determinístico sem envolver o modelo.
  - `QUARANTINE_AND_ESCALATE`: Quarentena segura da capacidade com escalonamento para o agente (System-2).

---

## 3. Integração com o Hermes Work

No Hermes Work, o `workstation/operational_kernel.py` já possui a exceção `CapabilityDriftError`. No entanto, quando um drift ocorre hoje no Hermes, o kernel simplesmente aborta o passo e joga um erro genérico.

Com a integração do algoritmo de diagnóstico do Driftlock:
1. O `OperationalKernel` pode tentar **reparo autônomo do seletor** quando o drift for puramente cosmético ou de atributos renomeados.
2. Quando o drift for estrutural, ele emite um relatório enriquecido com a exata discrepância visual/semântica para o `ExperienceCompiler` e o `Laya/System-1`, acelerando a re-compilação da capacidade.

---

## 4. Recomendações Objetivas

- **ADAPT:** Portar as regras de classificação de `diagnose.mjs` para o `OperationalKernel` em Python (`workstation/operational_kernel.py`), permitindo auto-reparo de seletores antes de acionar a quarentena total.
