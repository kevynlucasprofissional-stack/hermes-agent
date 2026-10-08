Sim. Li os **10 arquivos da pasta `workstation/experience_compiler/` no `main`** e segui o fluxo para fora dela, principalmente por `operational_capabilities.py`, `task_compiler.py`, `operational_kernel.py`, `control_plane/router.py` e `artifacts.py`.

A resposta principal é esta:

> **Uma Operational Capability não é um `.md`. Ela é essencialmente um pequeno programa determinístico serializado em JSON, acompanhado de contrato, esquema de inputs, verificador, evidências e metadados de aprendizado.**

### Skills e Operational Capabilities são coisas bem diferentes

Uma **Skill** funciona mais como um manual para a inteligência:

```text
SKILL.md

"Quando receber este tipo de tarefa:
  faça isso,
  considere aquilo,
  use estas ferramentas..."
```

Ela ainda depende da LLM interpretar as instruções.

Uma **OperationalCapability** é mais parecida com:

```text
PROGRAMA COMPILADO

ID
versão
inputs aceitos
pré-condições
efeitos
pós-condições
autoridade necessária
verificador
passos executáveis
dependências
evidências
estado de promoção
```

Por exemplo, conceitualmente:

```json
{
  "id": "experience_a81f...",
  "version": "1.0.0",

  "input_schema": {
    "repo": "...",
    "pr_number": "..."
  },

  "preconditions": [
    "pr_state == open"
  ],

  "implementation": {
    "steps": [
      {
        "primitive": "browser_click",
        "args": {
          "anchor": "..."
        }
      }
    ]
  },

  "postconditions": [
    "pr_state == merged"
  ],

  "verifier_contract": {...},

  "lifecycle": "promoted"
}
```

É o **Operational Kernel**, e não a LLM, que executa isso. Essa intenção está explicitamente documentada no próprio módulo: capacidades são procedimentos determinísticos aprendidos de experiência verificada e reutilizados automaticamente **sem pagar chamadas intermediárias de LLM**. Fonte: `workstation/operational_capabilities.py`, início do arquivo.

---

## Como o Experience Compiler funciona

Mentalmente, eu representaria assim:

```text
             EXPERIÊNCIA DO HERMES
                      │
                      ▼
          ┌─────────────────────┐
          │ Transition Samples  │
          │                     │
          │ estado antes        │
          │ ação realizada      │
          │ estado depois       │
          │ verificação         │
          │ provenance          │
          └──────────┬──────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │   EXPERIENCE COMPILER   │
        │                         │
        │ segmenta                │
        │ compara execuções       │
        │ remove passos inúteis   │
        │ encontra causalidade    │
        │ generaliza parâmetros   │
        │ aprende pré/efeitos     │
        └───────────┬─────────────┘
                    │
                    ▼
          OperationalCapability
                 DISCOVERED
                    │
                    ▼
             valida verifier
                    │
                    ▼
            controlled replay
                    │
                    ▼
             promotion policy
                    │
                    ▼
          OperationalCapability
                 PROMOTED
                    │
                    ▼
               REGISTRY
                    │
         ┌──────────┴───────────┐
         │                      │
         ▼                      ▼
     FUTURA TAREFA       outras capabilities
         │                 podem compor
         ▼
   reutilização
   determinística
```

Os arquivos dentro do Experience Compiler se dividem precisamente nessas funções: `models.py` define a ontologia observacional; `state_abstraction.py` transforma estados concretos em estados semânticos; `segmentation.py` encontra blocos de comportamento; `generalization.py` generaliza exemplos; `causal.py` descobre quais passos realmente contribuem para o efeito; `compiler.py` produz a `OperationalCapability`; `promotion.py` decide se ela é segura para promoção; `lifecycle.py` coordena validação → replay → promoção; `corpus.py` guarda a experiência; e `hierarchical.py` aprende capacidades maiores a partir de capacidades menores.

---

# O ponto que você estava realmente querendo entender: onde ela fica salva?

Aqui está a parte mais interessante.

Existem **dois lugares complementares**.

### 1. O corpo da capability fica como um artefato JSON

O registry chama:

```python
self.artifacts.store(
    "operational_capabilities",
    f"{capability.id}_{capability.version}_{sha[:16]}.json",
    sanitized
)
```

Fonte: `workstation/operational_capabilities.py`, método `OperationalCapabilityRegistry.register()`.

O `ArtifactStore` normalmente fica em:

```text
<HERMES_HOME>/
└── workstation/
    └── artifacts/
```

Fonte: `workstation/artifacts.py`, linhas 61–69.

Portanto, normalmente você terá algo conceitualmente assim:

```text
<HERMES_HOME>/
└── workstation/
    └── artifacts/
        └── operational_capabilities/
            ├── experience_a81f..._1.0.0_93ac81....json
            └── experience_a81f..._1.0.0_93ac81....json.meta.json
```

No Windows, se você não definiu outro `HERMES_HOME`, o default atual é:

```text
%LOCALAPPDATA%\hermes
```

porque `hermes_constants.py` define o default Windows como `LOCALAPPDATA / "hermes"`.

Então seria tipicamente algo parecido com:

```text
C:\Users\Kevyn Lucas\AppData\Local\hermes\
    workstation\
        artifacts\
            operational_capabilities\
                experience_....json
```

O próprio ArtifactStore cria uma referência canônica para o objeto:

```text
artifact://tasks/operational_capabilities/experience_....json
```

Fonte: `workstation/artifacts.py`, linhas 104–139.

---

## 2. Existe um catálogo separado: `index.json`

O Hermes não precisa sair vasculhando milhares de JSONs para encontrar uma capacidade.

Há um **registry index**.

Normalmente:

```text
<HERMES_HOME>/
└── workstation/
    └── operational_capabilities/
        ├── index.json
        └── index.lock
```

Fonte: `workstation/operational_capabilities.py`, `OperationalCapabilityRegistry`, linhas 248–264.

O `index.json` guarda aproximadamente:

```text
experience_a81f...@1.0.0
│
├── id
├── version
├── name
├── route
├── lifecycle
├── drift_state
├── semantic_fingerprint
├── compatibility_fingerprint
├── scope
├── family_id
├── ref ─────────────────────────────┐
├── sha256                           │
└── immutable_contract              │
                                     ▼
                  artifact://tasks/operational_capabilities/...
                                     │
                                     ▼
                       JSON COMPLETO DA CAPABILITY
```

Essa é provavelmente a imagem mais importante para você entender o sistema.

**O `index.json` é o catálogo.  
O ArtifactStore contém o objeto completo.**

Há uma compatibilidade adicional: se já existir `workstation/capabilities/`, o Registry usa essa pasta em vez de `workstation/operational_capabilities/`. Fonte: `operational_capabilities.py`, linhas 254–263.

---

# Portanto, a capability é realmente um arquivo?

**Sim, em última instância é persistida em JSON.**

Mas dizer simplesmente “é um JSON” esconderia a arquitetura.

É mais correto pensar:

```text
OperationalCapability
       │
       │ serialize
       ▼
JSON versionado
       │
       ├────────────► ArtifactStore
       │
       └────────────► Registry index
```

E um detalhe muito bom da implementação atual: quando o conteúdo muda, o SHA muda.

Então pode surgir:

```text
experience_X_1.0.0_AAAAA.json
experience_X_1.0.0_BBBBB.json
```

e o:

```text
index.json
```

passa a apontar para a representação atual.

Para capabilities aprendidas que já foram `PROMOTED`, o código grava ainda um:

```text
immutable_contract
```

e se alguém tentar alterar aquele contrato histórico mantendo a mesma versão, o Registry rejeita:

```text
historically promoted learned contract is immutable;
create a new version
```

Isso é bastante importante. A capability promovida vira praticamente um **artefato versionado imutável**.

---

# Como uma experiência vira capability

O Experience Compiler não simplesmente observa:

```text
clicou aqui
digitou ali
clicou acolá
```

e grava isso.

Ele faz algo bem mais elaborado.

A experiência original vira algo chamado:

```text
TransitionSample
```

que contém:

```text
SemanticState BEFORE
       │
       ▼
    Operation
       │
       ▼
SemanticState AFTER
       │
       ▼
    StateDelta
       │
       ▼
  Verification
       │
       ▼
   Provenance
```

Fonte: `workstation/experience_compiler/models.py`.

Inclusive ele deliberadamente remove coisas que seriam ruins para reaproveitamento, como IDs efêmeros, referências vivas, timestamps, scroll, page text e raciocínio.

Então:

```text
"clique no @e493"
```

não deveria simplesmente virar uma capability permanente.

O sistema procura anchors semanticamente recuperáveis como:

```text
testid
role + name
text
```

---

## Depois vem a parte que realmente parece um compilador

Imagine que o Hermes realizou algo três vezes:

```text
EXECUÇÃO 1

abrir PR 15
clicar Merge
confirmar
verificar merged
```

```text
EXECUÇÃO 2

abrir PR 27
clicar Merge
confirmar
verificar merged
```

```text
EXECUÇÃO 3

abrir PR 81
clicar Merge
confirmar
verificar merged
```

O `generalization.py` tenta perceber:

```text
15
27
81
```

não são parte essencial do procedimento.

Então produz algo como:

```text
abrir PR $inputs.pr_number
clicar Merge
confirmar
verificar merged
```

E junto cria automaticamente o:

```text
input_schema
```

Isso é estruturalmente uma **compilação de experiências concretas em um procedimento parametrizado**.

---

# Ele também tenta descobrir quais passos eram realmente necessários

O `causal.py` constrói um grafo de dependências.

Algo como:

```text
A ──► B ──► C ──► D
     ╲
      └────► D

X
```

Se `X` aconteceu durante a experiência mas não contribuiu causalmente para o resultado verificado, o `operational_slice()` pode removê-lo.

Depois `segmentation.py` compara várias execuções e classifica os passos como:

```text
CORE

CONDITIONAL

OPTIONAL

ANOMALOUS / RECOVERY
```

Passos opcionais/anômalos não são simplesmente incorporados cegamente à capability.

---

# E ela não fica reutilizável imediatamente

Esse é outro ponto essencial.

Quando `compiler.py` cria:

```python
OperationalCapability(...)
```

ela começa como:

```text
DISCOVERED
```

Não:

```text
PROMOTED
```

Existe um verdadeiro funil:

```text
DISCOVERED
     │
     ▼
evidência de múltiplos runs
     │
     ▼
formal contract
     │
     ▼
verifier validation
     │
     ▼
controlled replay
     │
     ▼
ExperiencePromotionPolicy
     │
     ▼
PROMOTED
```

O `lifecycle.py` exige, entre outras coisas, experiência em pelo menos dois runs, boa parametrização, provenance completa e ausência de drift.

Depois o verifier precisa ser validado.

Depois a capability é executada novamente em um ambiente seguro via:

```text
controlled_replay
```

Só então `ExperiencePromotionPolicy` considera promovê-la.

Fonte: `workstation/experience_compiler/lifecycle.py` e `promotion.py`.

---

# Depois de promovida, como ela é encontrada novamente?

Aqui entra o outro lado do sistema.

```text
NOVA SOLICITAÇÃO
      │
      ▼
OperationIntent
      │
      ▼
CapabilityRouter
      │
      ▼
OperationalCapabilityRegistry
      │
      ▼
somente PROMOTED
```

O `CapabilityRouter` reconstrói seu índice explicitamente usando:

```python
registry.list_capabilities(
    lifecycle=CapabilityLifecycle.PROMOTED
)
```

Fonte: `workstation/control_plane/router.py`, linhas 331–335.

Depois procura principalmente por:

```text
target_family
operation_family
family_id
```

Fonte: `router.py`, linhas 375–386.

Mas encontrar algo parecido **não basta**.

Ele verifica:

```text
target corresponde?
pré-condições verdadeiras?
postconditions satisfazem o objetivo?
efeitos estão dentro do permitido?
invariantes permanecem válidos?
usuário/sistema tem autoridade?
policy permite?
verifier é suficiente?
estado está fresco?
```

Somente depois disso produz:

```text
ExecutableDecision
```

---

# Aí entra o Operational Kernel

O fluxo completo de reutilização fica:

```text
             "Faça X"
                 │
                 ▼
         ┌──────────────┐
         │OperationIntent│
         └───────┬──────┘
                 │
                 ▼
       ┌──────────────────┐
       │ CapabilityRouter │
       └────────┬─────────┘
                │
           procura
                │
                ▼
       ┌──────────────────┐
       │ CapabilityRegistry│
       │    PROMOTED       │
       └────────┬─────────┘
                │
         capability encontrada
                │
                ▼
          contrato válido?
                │
               SIM
                │
                ▼
        ┌─────────────────┐
        │  TaskCompiler   │
        │ PIN da versão   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │OperationalKernel│
        │                 │
        │ $inputs         │
        │ $deps           │
        │ $prev           │
        │ primitives      │
        └────────┬────────┘
                 │
                 ▼
             VERIFIER
                 │
                 ▼
          resultado validado
```

E esse caminho é **determinístico**.

Não precisa de uma LLM decidindo novamente cada clique.

---

## Existe até um mecanismo para impedir que a capability mude no meio de uma tarefa

Antes de executá-la, `TaskCompiler._execute_capability()` faz um **pin**.

Ele guarda no WorkPlan:

```text
capability_id
version
semantic_fingerprint
compatibility_fingerprint
contract_fingerprint
```

Depois recarrega a capability e verifica:

```text
"continua exatamente a capability que escolhi?"
```

Se mudou:

```text
pinned capability contract changed
```

ou:

```text
pinned capability implementation changed
```

A execução é recusada.

Fonte: `workstation/task_compiler.py`, linhas 1344–1406, e `experience_compiler/promotion.py`, `pin_capability()`.

---

# E existe um segundo nível de aprendizado que achei especialmente interessante

O `hierarchical.py` não aprende apenas:

```text
ações → capability
```

Ele aprende:

```text
capability A
     │
     ▼
capability B
     │
     ▼
capability C
```

Se isso se repete em diversos runs, pode nascer:

```text
Composite OperationalCapability
```

Mas o código deliberadamente **não achata** tudo novamente em cliques.

Fica:

```text
CAPABILITY ABC
│
├── depende de A
├── depende de B
└── depende de C
```

Isso está escrito literalmente no módulo:

> `NO FLATTENING`

Ou seja, o Hermes começa a construir uma espécie de **biblioteca hierárquica de comportamento**.

---

# E após reutilizar, o sistema aprende de novo

Cada execução de uma capability gera:

```text
CapabilityInvocation
```

com:

```text
capability_id
version
run_id
inputs
estado antes
estado depois
verificação
evidence refs
authority
timestamp
```

O `OperationalKernel` persiste isso novamente no ArtifactStore como:

```text
invocation_<id>.json
```

e também registra no `ExecutionJournal`.

Essas invocações são justamente o material que o **Hierarchical Experience Compiler** pode analisar depois.

Então o loop é:

```text
EXPERIÊNCIA
    │
    ▼
CAPABILITY
    │
    ▼
REUTILIZAÇÃO
    │
    ▼
CAPABILITY INVOCATION
    │
    ▼
NOVA EXPERIÊNCIA
    │
    ▼
CAPABILITY MAIS ABSTRATA
```

Esse é, para mim, o modelo mental correto do Experience Compiler atual. 

---

## Para a imagem que você quer pedir depois

Eu **não faria uma imagem mostrando somente “Experience Compiler”**.

Faria um grande diagrama em **duas metades**:

```text
╔══════════════════════╗       ╔══════════════════════╗
║      APRENDER        ║       ║      REUTILIZAR      ║
║                      ║       ║                      ║
║ ações                ║       ║ nova intenção        ║
║ ↓                    ║       ║ ↓                    ║
║ TransitionSamples    ║       ║ CapabilityRouter     ║
║ ↓                    ║       ║ ↓                    ║
║ Experience Compiler  ║       ║ Registry             ║
║ ↓                    ║       ║ ↓                    ║
║ Candidate            ║       ║ OperationalKernel    ║
║ ↓                    ║       ║ ↓                    ║
║ validation/replay    ║       ║ execução             ║
║ ↓                    ║       ║ ↓                    ║
║ PROMOTED             ║──────►║ CapabilityInvocation ║
╚══════════════════════╝       ╚══════════╤═══════════╝
                                        │
                                        └──── feedback
```

E **bem no centro**, grande, eu colocaria visualmente o Registry com duas peças:

```text
┌─────────────────────────┐
│       INDEX.JSON        │
│                        │
│ "Onde está?"           │
│ "Qual versão?"         │
│ "Está promoted?"       │
│ "Está healthy?"        │
└───────────┬─────────────┘
            │ artifact://...
            ▼
┌─────────────────────────┐
│ CAPABILITY JSON         │
│                        │
│ inputs                 │
│ contract               │
│ steps                  │
│ verifier               │
│ evidence               │
└─────────────────────────┘
```

Porque **essa é exatamente a resposta visual para sua dúvida principal sobre onde e como as capacidades operacionais ficam salvas para poderem ser reutilizadas**.