# 00 — Baseline e Escopo da Auditoria Code-to-Code do Ecossistema Browser

**Data da Auditoria:** 10 de Outubro de 2026  
**Status:** AUDITORIA ATIVA / CODE-TO-CODE / NÃO-INTRUSIVA NO RUNTIME  
**Diretório de Trabalho:** `C:\Github\hermes-agent`  
**Branch Ativa:** `codex/creative-d043-engine-neutral`  
**HEAD SHA Local:** `56f5758d9b589f3bc04f5a4b4305d80d8fd459a7`  
**Upstream Local Pinned:** `NousResearch/hermes-agent@6a2662a4aaad68e1b75f6e7ac789409aa653abf7`  

---

## 1. Contexto e Missão

Esta auditoria tem por objetivo executar uma análise comparativa profunda, baseada estritamente em código-fonte, arquitetura e implementação real (*code-to-code*), confrontando o subsistema Browser do **Hermes Work** com os 25 repositórios de referência presentes na biblioteca local em `C:\Github\hermes-agent\referências\02-Browser-Automacao-Web` e adjacências.

A auditoria foca na identificação de:
1. Mecanismos externos comprovadamente superiores ou mais maduros.
2. Problemas que o Hermes Work tenta resolver e que já possuem soluções robustas no ecossistema.
3. Complexidades acidentais, redundâncias ou gargalos no código do Hermes.
4. Código, algoritmos e testes que podem ser copiados (`COPY`), adaptados (`ADAPT`), mantidos externos (`INTEGRATE EXTERNAL`) ou que devem ser rejeitados (`REJECT`).
5. Decisões arquiteturais do Hermes Work que são superiores e devem ser preservadas (`KEEP HERMES`).
6. Combinações sinérgicas entre projetos que superam qualquer alternativa isolada.

---

## 2. Invariantes Arquiteturais e Restrições Não-Negociáveis

Qualquer proposta gerada por esta auditoria deve respeitar as seguintes regras canônicas do Hermes Agent e do Hermes Work:

1. **Prompt Caching é Sagrado:**
   Qualquer alteração que invalide mid-conversation o prefixo em cache multiplica o custo e latência do usuário. Ferramentas, esquemas e prompts devem ser estáveis por sessão.
2. **O Core é uma Cintura Estreita (Narrow Waist):**
   Ferramentas do modelo são enviadas a cada chamada. A capacidade deve viver nas bordas (skills, CLI, plugins, toolsets de sessão), e não expandir o core de forma irrestrita.
3. **Capacidade de Superfície pertence à SESSÃO, não ao ambiente (`HERMES_DESKTOP=1`):**
   O gate para ferramentas de desktop UI e browser deve depender da sessão (ex: GUI conectada) e não de variáveis de ambiente de processo.
4. **Propriedade Única e Ausência de Segundo Control Plane:**
   O Hermes Work já possui donos canônicos de estado:
   - `BrowserTask` e `BrowserSessionState` (Electron / WebContentsView)
   - `TaskRun` e `ExecutionJournal`
   - `OperationalKernel`, `TaskCompiler` e `VerifiedOperationalControl Plane`
   - `ExperienceCompiler` e `Laya/System-1` (limitado a detecção contratual de estágio)
   *Não é permitido introduzir um segundo BrowserTask, segundo gerenciador de abas ou segundo compilador de experiência.*
5. **Portão Upstream-First (H-079, H-080A, H-080B):**
   Nenhuma modificação no runtime é feita nesta etapa de auditoria.

---

## 3. Vocabulário Canônico de Evidência

Em conformidade com `workstation/context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md`:

- **`FACT`**: Fato diretamente comprovado no código-fonte, teste automatizado executável ou receipt real.
- **`PARTIAL`**: Evidência parcial ou divergência histórica/versão observada.
- **`NV`**: Não Verificado nesta rodada de auditoria (*Nota: `NV` não significa "não existe"*).
- **`INFERENCE`**: Dedução lógica derivada de fatos verificados; nunca registrada como fato primário.
- **`RECOMMENDATION`**: Ação técnica proposta com justificativa arquitetural.

---

## 4. Escopo dos Repositórios Auditados

### Prioridade P0 (Auditoria Profunda Obrigatória)
1. **BrowserOS** (`browseros-ai--BrowserOS` @ `9d4eaf6ae8`, espelho `BrowserOS-main`)
2. **Stagehand** (`browserbase--stagehand` @ `f261c38b4d`)
3. **browser-use/desktop** (`browser-use--desktop` @ `f073b7574f`)
4. **browser-use/browser-use** (`browser-use--browser-use` @ `c75e8476e2`)
5. **browser-use/browser-harness** (`browser-use--browser-harness` @ `dbf0e4f3a3`)
6. **browser-use/browsercode** (`browser-use--browsercode` @ `b200643fe0`)
7. **vercel-labs/agent-browser** (`vercel-labs--agent-browser` @ `44af398426`)
8. **abundantbeing/hermes-browser-extension** (`abundantbeing--hermes-browser-extension` @ `ba4d30e609`)
9. **Camofox** (`camofox-browser-main`, snapshot unversioned)
10. **openbrowserclaw** (`openbrowserclaw-master`, snapshot unversioned)
11. **browserclaw** (`browserclaw-main`, snapshot unversioned v0.20.3)

### Prioridade P1 (Memória, Percepção e Confiabilidade)
12. **browser-memory** (`browser-memory--browser-memory` @ `138d05d515`)
13. **apatureai/lattice** (`apatureai--lattice` @ `84f815b8c0`)
14. **aaronlab/browsertrace** (`aaronlab--browsertrace` @ `05f0215dbe`)
15. **EricFinland/witness** (`EricFinland--witness` @ `2d3ccdcd6c`)
16. **VasuBansal7576/driftlock** (`VasuBansal7576--driftlock` @ `917396a43c`)
17. **lamenting-hawthorn/browserbench** (`lamenting-hawthorn--browserbench` @ `9d01df4276`)
18. **visnia-ai/browsewebapp-bench** (`visnia-ai--browsewebapp-bench` @ `be18eccdc5`)
19. **visnia-ai/browser-agent** (`visnia-ai--browser-agent` @ `d6b7545f10`)

### Prioridade P2 (Arquitetura, UX e Baseline)
20. **NousResearch/hermes-agent** (Upstream baseline @ `6a2662a4aa`)
21. **platonai/Browser4** (`platonai--Browser4` @ `0fdba82a60`)
22. **vibesurf-ai/VibeSurf** (`vibesurf-ai--VibeSurf` @ `cd6e519d50`)
23. **nesquena/hermes-webui** (`nesquena--hermes-webui` @ `81e1e7f7c4`)
24. **openclaw/openclaw** (`openclaw--openclaw` @ `00e095399b`)

---

## 5. Sessões Reais do Hermes

O repositório local possui 49 sessões reais gravadas em:
`c:\Github\hermes-agent\workstation\dogfood\dados\Sessões Hermes\`

Cobrindo tarefas de:
- Automação do Trello (ex: `abrir-trello-na-internet-*.json`, `importar-cart-es-trello-*.json`)
- Hyperframe (ex: `abrir-hyperframe-20261009.json`)
- Redes sociais e extração de dados (Instagram / ACIRV, WhatsApp Web)
- Navegação direta, snapshots e tentativas de recuperação.

Essas sessões serão utilizadas como contraprova empírica para avaliar problemas reais observados no comportamento do agente em produção.
