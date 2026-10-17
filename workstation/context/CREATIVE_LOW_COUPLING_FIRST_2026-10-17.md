# D-046 — Integração por necessidade demonstrada: uso primeiro, acoplamento quando comprovado

**Data:** 2026-10-17  
**Status:** DECISÃO ESTRATÉGICA ACEITA / DOCUMENTAÇÃO APENAS; nenhuma mudança de runtime, instalação, integração ou qualificação é declarada.  
**Escopo:** Hermes Work, Creative Workstation e, como princípio geral, futuras integrações de motores e aplicativos.  
**Prioridade:** entregas reais e retorno sobre esforço do operador; D-043 permanece como arquitetura candidata de longo prazo, sem implementação compulsória.

## 1. Decisão central

> **Uma experiência unificada, múltiplos motores independentes e integração profunda somente mediante necessidade operacional demonstrada.**

A experiência unificada de uso **não** exige fusão de código-fonte, nem implica que baixo acoplamento seja provisório ou inferior. A situação final ideal de uma ferramenta pode ser permanecer independente para sempre. O Hermes deve extrair o maior valor das capacidades disponíveis com a menor engenharia adicional necessária.

**Não há compromisso de absorver progressivamente todos os aplicativos.** A absorção de código é uma opção condicionada a evidências, não um marco de maturidade.

## 2. Aplicação imediata à Creative Workstation

1. **Utilizar sem reconstruir:** quando possível, abrir PhotoCraft, EffectCraft, Remotion Studio e outros aplicativos web nos **painéis/abas e Browser nativo já existentes** no Hermes Work. Reaproveitar mecanismos atuais de abertura/registro de aplicativos, se disponíveis; não construir uma nova camada de painéis ou um browser paralelo só para hospedar as ferramentas.
2. **Trabalhar de verdade:** usar cada aplicação manualmente ou com apoio do agente para produzir artefatos profissionais, preservando o motor e o formato nativo de cada uma. Avaliar qualidade, exportação e retomada antes de pedir uma integração profunda.
3. **Automatizar com o que já existe:** testar recursos atuais de navegação/interação/automação do Browser sob os owners, aprovação e controle humano canônicos, e registrar as limitações verificadas. Em aplicativos Canvas/WebGL, controle de DOM pode ser insuficiente; isso é hipótese a testar, não uma justificativa automática para absorver o editor.
4. **Conectar minimamente quando necessário:** se uma limitação real e repetida persistir, preferir primeiro uma API/CLI, bridge fina, adapter tipado, script ou contrato de artefatos limitado ao caso de uso, com testes e limites de autoridade.
5. **Acoplar código-fonte somente como último recurso racional:** considerar fork, adaptação interna ou incorporação de partes do motor apenas após comparar benefícios mensuráveis com manutenção de upstream, compatibilidade, licenças, segurança, testes de regressão e custo de oportunidade.

**Nota técnica:** a interface do Remotion Studio pode abrir no browser, mas build, render e processamento podem exigir Node.js/CLI e processos externos ao renderer; isso não comprova que todo Remotion opera dentro do browser. Para Three.js, usar um editor existente se houver caso real; a biblioteca Three.js isolada não é um editor profissional pronto.

## 3. Três níveis que não devem ser confundidos

| Nível | Mecanismo | Condição de aceite | Implica avanço? |
| --- | --- | --- | --- |
| **Disponibilizar** | App/motor independente num painel do Browser nativo | Abre, permite trabalhar e exportar/guardar artefatos reais | **Não** |
| **Automatizar** | Ferramentas Browser existentes; depois ponte pequena se indispensável | Repetição confiável, autoridade e verificações válidas, ganho demonstrado | **Não** |
| **Internalizar** | Adaptar/incorporar código-fonte ou runtime profundamente | Gargalo comprovado, alternativa leve insuficiente, benefício líquido superior ao custo permanente | **Não** |

## 4. Critérios para permitir integração mais profunda

Antes de abrir trabalho de código, registrar:
- **Tarefa e demanda reais:** qual entrega concreta, quantas repetições e que etapa está bloqueada.
- **Baseline observada:** tempo humano, quantidade de intervenções, taxa de sucesso/falhas, qualidade e exportação; separar fatos de expectativas.
- **Alternativas testadas:** browser existente, uso manual, CLI/API, adapters específicos e ferramentas já incluídas no Hermes.
- **Hipótese falsificável:** melhoria esperada e como medir antes/depois; não contar instalação, teste sintético ou quantidade de integrações como resultado de usuário.
- **Custo total de propriedade:** segurança, permissões, compatibilidade com upstream, licenças, manutenção, regressões, custo de inferência, tempo de supervisão e custo de oportunidade.
- **Autorização e gates:** continuar respeitando TaskRun, SessionDB, BrowserTask, controle humano/lease, readback, H-079, H-080, CI no SHA exato e os demais requisitos existentes.

Se a versão de baixo acoplamento já resolve o trabalho com qualidade e custo adequados, **encerrar a investigação sem internalizar**.

## 5. Repriorização de execução — regra 80/20

- **Agora:** preservar o que existe e concentrar esforço em trabalhos reais com Browser e motores disponíveis. Ajustes mínimos de lançamento são configuração, não uma nova Creative Workstation.
- **Quando houver repetição:** automatizar os passos recorrentes e corrigir o menor gargalo real, preferindo recursos já existentes.
- **Experience Compiler:** manter o que já está desenvolvido, mas priorizar a demonstração empírica de `execução real -> experiência -> capacidade candidata validada -> reuso posterior`. A compilação orientada por LLM pode ser o caminho inicial mais simples; investigação autônoma, mineração geral e expansão especulativa não são pré-requisitos para obter resultados úteis.
- **Depois:** reabrir planos complexos de kernel criativo compartilhado, motor próprio, edição profunda, Three.js ou absorção de código somente mediante uma nova decisão fundamentada em evidências.

Não há percentual fixo obrigatório de alocação de horas ou declaração de congelamento definitivo; trata-se de um **gate de priorização por valor operacional**, não de proibição permanente de inovação.

## 6. Relação com decisões anteriores

- **D-043 (engine-neutral)** continua registrada e útil como hipótese de arquitetura compartilhada para casos que venham a justificá-la; **não** autoriza, por si só, executar imediatamente CWN-00..09 nem determina que os motores precisem ser fundidos. Seu roadmap detalhado passa a ser **backlog condicionado à demanda observada**. Não descartar testes, contratos e trabalho anterior.
- **D-040, D-042 e gates de qualificação** permanecem válidos; documentação não equivale a implementação ou certificação.
- **Runtime/Browser/TaskRun**: reutilizar owners e controles existentes. Não criar novo navegador, nova autoridade de estado, ou camada paralela para integrar editores.
- A política **vale além da Creative Workstation** para novas propostas de integração no Hermes: capacidade útil não equivale a obrigação de incorporação.

## 7. Primeiro experimento recomendado, ainda NÃO EXECUTADO

Escolher **um** fluxo profissional recorrente e:
1. Abrir o editor existente no Browser/painel atual do Hermes sem alterar código.
2. Concluir e exportar um artefato real; registrar dificuldades e qualidade.
3. Repetir o fluxo com automação de Browser onde fizer sentido.
4. Medir trabalho concluído, tempo total, taxa de sucesso, intervenções humanas, erros e manutenção.
5. Só então propor um adapter ou integração de código, citando a limitação específica e prova de ganho.

**Estado da evidência nesta decisão:** registro da escolha estratégica do mantenedor, **sem teste real dos aplicativos nesse fluxo, sem benchmark, sem CI e sem prova de compatibilidade ou automação de PhotoCraft/EffectCraft/Remotion**. Não converter a decisão em `IMPLEMENTED`, `VERIFIED` ou `QUALIFIED`.

## 8. Regra de lembrança para agentes

> **O Hermes Work não deve absorver ferramentas por serem úteis. Deve utilizá-las primeiro, automatizá-las quando houver retorno e só internalizá-las quando o gargalo observado justificar o custo de propriedade. Baixo acoplamento bem-sucedido é resultado final válido.**

Este documento é a referência canônica D-046; registros resumidos nos arquivos de inteligência, decisões, estado, journal, roadmap e Creative Workstation devem apontar para ele, sem duplicar ou reinterpretar suas condições.
