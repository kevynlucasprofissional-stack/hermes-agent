# Comparar ferramentas de design

**User:** Anonymous  
**Created:** 10/3/2026 1:34:30  
**Updated:** 10/3/2026 1:41:02  
**Exported:** 10/8/2026 10:29:59  
**Link:** [https://chatgpt.com/c/6ac085d6-9a74-83e9-899b-348b420bc77b?src=history_search](https://chatgpt.com/c/6ac085d6-9a74-83e9-899b-348b420bc77b?src=history_search)  

## Prompt:
03/10/2026, 01:34:53

PhotoGimp Vs Photoshop Vs Penpot Vs Inkscape Vs outra alternativa que eu talvez desconheça e deveria conhecer

## Response:
03/10/2026, 01:35:03 · gpt-5-6-thinking

Vou comparar pelo que realmente importa no seu caso: **qualidade de edição**, **raster/vetor/UI**, **automação por agente**, **self-host/local**, e o quanto cada ferramenta encaixa no Hermes Work. E vou incluir as alternativas que mudam de fato a decisão, não só clones.

> **Comparando ferramentas**
>
> Estou comparando Photoshop, PhotoGIMP, GIMP e Penpot por raster, vetores, colaboração, automação e controle local. Para o Hermes Work, Penpot parece mais agent-friendly; GIMP/PhotoGIMP oferecem mais controle de imagem, mas exigem automação local mais frágil.
>
> **Comparou ferramentas**
>
> 
>
> **Ampliando alternativas**
>
> Estou incluindo Inkscape para SVG determinístico, Krita para pintura raster, Graphite como aposta experimental baseada em nós e Scribus para publicação. Também estou verificando o Affinity, que pode ser relevante apesar de não ser totalmente aberto.
>
> **Posicionando no ranking**
>
> Estou elevando Affinity pela combinação de gratuidade e integração baseada em MCP, mas sem tratá-lo como aberto ou auto-hospedável. Para o Hermes Work, Penpot lidera em colaboração; Inkscape, em SVG determinístico; Graphite, como aposta futura.
>
> **Ampliou alternativas e posicionou no ranking**
>
> 
>
> **Pesquisou 14 sites**
>
> 
>
> Pensou por 46s

Sim. E tem uma alternativa que hoje, em outubro de 2026, eu colocaria **obrigatoriamente nessa comparação: Affinity**. Ela mudou bastante de posição recentemente.

O ponto principal é que você está comparando ferramentas de categorias diferentes. Para o que você está imaginando com o **Hermes Work**, eu separaria assim:

| Ferramenta | Especialidade | Raster | Vetor | Layout/UI | Automação | Web/self-host | Adequação ao Hermes Work |
|---|---|---:|---:|---:|---:|---:|---:|
| **Photoshop** | Foto/composição | Excelente | Médio | Médio | Alta | Não | Média |
| **PhotoGIMP / GIMP** | Raster geral | Muito bom | Básico | Básico | **Muito alta** | Não | **Alta** |
| **Affinity** | Raster + vetor + layout | **Excelente** | **Excelente** | Muito bom | **Muito alta** | Não | **Muito alta** |
| **Penpot** | Design/UI/layout | Fraco | **Excelente** | **Excelente** | **Excelente** | **Sim** | **Excelente** |
| **Inkscape** | SVG/vetor | Fraco | **Excelente** | Bom | **Excelente** | Não | **Excelente** |
| **Krita** | Pintura/ilustração | **Excelente** | Médio | Fraco | Alta | Não | Alta |
| **Graphite** | Design procedural | Bom* | **Excelente*** | Médio | Potencial enorme | Browser | **Muito promissor** |

\* Graphite ainda está em alpha.

### Photoshop

Continua sendo a referência quando a tarefa é manipulação fotográfica complexa: máscaras, smart objects, filtros, Camera Raw, composição, mockups, PSDs de terceiros, tratamento de pele, retoque etc.

E ele é mais automatizável do que às vezes parece. O UXP oferece JavaScript para manipular documentos, layers, selections, Camera Raw e outros recursos. ([Adobe Developer](https://developer.adobe.com/uxp/uxp-api/?utm_source=chatgpt.com))

O problema para o **Hermes Work** é arquitetural: Photoshop continua sendo um aplicativo desktop proprietário. Você consegue criar um plugin/bridge UXP e mandar comandos para ele, mas estaria adaptando o Hermes ao Photoshop.

Não seria minha primeira escolha para uma infraestrutura agentic.

---

### PhotoGIMP

Aqui existe uma distinção importante:

**PhotoGIMP não é um editor diferente do GIMP.**

É essencialmente uma configuração/patch para o GIMP que reorganiza interface, atalhos e comportamento para ficar mais familiar para usuários de Photoshop. O próprio projeto o descreve dessa maneira. ([GitHub](https://github.com/Diolinux/PhotoGIMP/?utm_source=chatgpt.com))

Portanto:

**PhotoGIMP = GIMP + UX parecida com Photoshop.**

E o **GIMP 3** ficou bastante interessante para o Hermes. Ele tem API estável para a série 3.x e suporta plugins/scripts em Python 3, Script-Fu, C e outras linguagens/bindings. ([Desenvolvimento GIMP](https://developer.gimp.org/api/3.0/?utm_source=chatgpt.com))

Isso permite algo como:

```text
Hermes Work
   ↓
Python
   ↓
GIMP API / PDB / GEGL
   ↓
abrir imagem
criar camada
recortar
aplicar máscara
redimensionar
aplicar efeito
exportar
```

Isso é muito mais interessante do que controlar o mouse do GIMP.

PhotoGIMP/GIMP é GPLv3. ([GitHub](https://github.com/Diolinux/Photogimp?utm_source=chatgpt.com))

Para **tratamento raster open-source automatizado**, continua sendo uma escolha muito séria.

---

# Penpot

Aqui está uma diferença enorme.

Penpot não tenta ser Photoshop.

Ele compete muito mais com:

```text
Figma
Sketch
Adobe XD
```

do que com Photoshop.

Só que para o **Hermes Work**, essa diferença é justamente sua maior vantagem.

Penpot é:

```text
web
+
self-hostable
+
SVG
+
CSS
+
HTML
+
design tokens
+
components
+
API
+
plugins
+
MCP
```

O projeto é open source sob MPL 2.0. ([GitHub](https://github.com/penpot/penpot?embed=0&utm_source=chatgpt.com))

E ocorreu uma mudança particularmente relevante para a ideia que você está desenvolvendo: **Penpot agora possui um servidor MCP oficial para agentes**.

O agente pode ler e modificar a estrutura dos arquivos Penpot, incluindo componentes, styles, tokens, páginas e layers. A documentação cita explicitamente criação de tokens, variantes, organização de componentes e auditoria de design systems. ([Centro de Ajuda Penpot](https://help.penpot.app/mcp/?utm_source=chatgpt.com))

Ou seja:

```text
Hermes Work
      ↓
     MCP
      ↓
    Penpot
      ↓
Design estruturado
```

Isso é radicalmente melhor que:

```text
Hermes
 ↓
move mouse
 ↓
clica em ferramenta
 ↓
arrasta camada
```

Para a ideia de **creative workstation controlável por agentes**, Penpot é atualmente um dos candidatos mais óbvios.

---

# Inkscape

Eu não descartaria Inkscape. Pelo contrário.

Para automação determinística, ele pode ser até **mais interessante que Penpot** em determinados trabalhos.

O motivo é SVG.

Um agente pode produzir:

```xml
<svg>
  ...
</svg>
```

diretamente.

Depois:

```text
Hermes
  ↓
gera/modifica SVG
  ↓
Inkscape CLI
  ↓
PNG / SVG / PDF
```

Inkscape tem automação por linha de comando com `--actions`, processamento em batch e várias operações de transformação/exportação. ([Wiki Inkscape](https://wiki.inkscape.org/wiki/Release_notes/1.4?utm_source=chatgpt.com))

Além disso, suporta extensões em Python. ([Inkscape](https://inkscape.org/zh-hant/develop/extensions/?utm_source=chatgpt.com))

Então, para coisas como:

```text
posts
infográficos
logos
diagramas
cartazes
cards
layouts geométricos
assets vetoriais
```

ele é extremamente interessante.

Eu não faria o Hermes "clicar no Inkscape".

Eu faria:

```text
LLM
 ↓
SVG estruturado
 ↓
Inkscape
 ↓
renderização profissional
```

Essa arquitetura é excelente.

---

# Affinity - o que estava faltando na discussão

Aqui é onde a comparação ficou bem mais interessante em 2026.

O novo **Affinity** agora reúne:

```text
Photo
+
Designer
+
Publisher
```

em um único aplicativo.

Ou seja:

```text
raster
+
vetor
+
layout editorial
```

no mesmo documento.

E desde 2025 ele passou a ser **gratuito**, embora continue proprietário e ligado à Canva. ([Canva](https://www.canva.com/newsroom/news/all-new-affinity/?msockid=00cd9774d1af65a23fe581ecd0116496&utm_source=chatgpt.com))

Mas a mudança realmente relevante aconteceu agora.

Em **15 de setembro de 2026**, Affinity lançou **scripting dentro do próprio aplicativo**. Um script pode operar simultaneamente em objetos vetoriais, pixels e layouts. ([Affinity](https://www.affinity.studio/blog/affinity-automation-scripting-claude?utm_source=chatgpt.com))

Então você pode ter:

```text
script
 ↓
editar fotos
 ↓
montar objetos vetoriais
 ↓
montar página
 ↓
exportar
```

sem mudar de software.

E existe ainda um **AI Connector baseado em MCP para Claude**, capaz de gerar workflows e scripts reutilizáveis a partir de linguagem natural. ([Affinity](https://www.affinity.studio/integrations?utm_source=chatgpt.com))

Oficialmente eles o apresentam como integração com Claude; portanto eu não assumiria automaticamente compatibilidade oficial com Hermes. Mas o fato de a arquitetura usar **MCP** torna isso particularmente interessante para investigação.

Para o que você está construindo, eu estudaria Affinity com bastante atenção.

---

# E tem outro: Graphite

Esse é provavelmente o projeto que mais combina conceitualmente com a maneira como você pensa o Hermes Work.

**Graphite** é um editor open-source raster + vetor com uma arquitetura baseada em **node graph**.

Ele se descreve como:

```text
layers
+
nodes
+
procedural graphics
+
nondestructive editing
```

e está sendo desenvolvido em Rust. É MIT/Apache-2.0. ([GitHub](https://github.com/GraphiteEditor/Graphite?utm_source=chatgpt.com))

Hoje ainda está **alpha**, então eu não usaria como editor principal de produção.

Mas conceitualmente:

```text
Hermes
 ↓
gera grafo
 ↓
Graphite
 ↓
render
```

é uma arquitetura extremamente interessante.

É quase a lógica do Blender aplicada ao design 2D.

E o roadmap inclui áreas como raster, composição, motion graphics, pintura e VFX. ([GitHub](https://github.com/GraphiteEditor/Graphite/blob/master/README.md?plain=1&utm_source=chatgpt.com))

Esse eu definitivamente colocaria na **Matrix Source do Hermes Work**.

---

# Krita

Krita entra quando você precisa de:

```text
pintura
ilustração
concept art
brush engine
texturas
drawing
```

mais do que layout gráfico.

Também possui uma API Python relativamente poderosa para automação, criação de plugins, exportadores e processamento em lote. ([Krita Docs](https://docs.krita.org/en/user_manual/python_scripting.html?utm_source=chatgpt.com))

É GPL e open source. ([GitHub](https://github.com/kde/krita?utm_source=chatgpt.com))

Para peças publicitárias, eu colocaria abaixo de GIMP/Affinity/Inkscape/Penpot.

Para ilustração, colocaria acima deles.

---

## E tem uma descoberta ainda mais relevante para o seu pipeline

Affinity agora possui integração direta com **Cavalry**, e a Canva anunciou o **Cavalry gratuito** em 2026. Affinity também passou a integrar arquivos `.af` diretamente com DaVinci Resolve. ([Affinity](https://www.affinity.studio/blog/affinity-update-april-2026))

Isso produz um pipeline muito próximo do que você vinha tentando montar:

```text
                    ┌─ GIMP
                    │  raster
                    │
Hermes Work ────────┼─ Inkscape
                    │  SVG
                    │
                    ├─ Penpot
                    │  design systems / layouts
                    │
                    ├─ Affinity
                    │  raster + vector + layout
                    │
                    └─ Graphite
                       procedural 2D
                           │
                           ↓
                  Remotion / Cavalry
                           │
                           ↓
                      Three.js
                           │
                           ↓
                    Blender
```

Mas eu **não instalaria tudo como ferramentas equivalentes**.

Eu começaria a pensar no Hermes Work em termos de **engines especializadas**.

Para **design agentic**, minha arquitetura hoje seria:

```text
PENPOT
interface/design systems
MCP + browser + self-host
           │
           ├───────────────┐
           ↓               ↓
      INKSCAPE         AFFINITY
      SVG engine       pro design engine
      CLI/Python       pixel+vector+layout
           │               │
           └───────┬───────┘
                   ↓
          REMOTION / CAVALRY
                   ↓
             THREE.JS
                   ↓
               BLENDER
```

E deixaria:

```text
GIMP
```

como **raster engine open-source programável**, não necessariamente como a interface principal.

A maior mudança em relação ao que discutimos ontem é esta: **eu colocaria Affinity e Graphite na investigação imediatamente. E Penpot continua sendo provavelmente a melhor "creative surface" para integrar profundamente ao Hermes Work, porque já pensa explicitamente em agentes, MCP e self-hosting.** ([Centro de Ajuda Penpot](https://help.penpot.app/mcp/?utm_source=chatgpt.com))

Para trabalho manual profissional puro, porém, **Affinity agora talvez seja o concorrente mais interessante ao Photoshop nesse conjunto**, especialmente porque combina pixel, vetor e layout no mesmo documento e acabou de ganhar scripting. ([Affinity](https://www.affinity.studio/blog/affinity-automation-scripting-claude?utm_source=chatgpt.com))

---

**Sources:**

- [UXP API Reference](https://developer.adobe.com/uxp/uxp-api/?utm_source=chatgpt.com)
- [GitHub - Diolinux/PhotoGIMP: A Patch for GIMP 3+ for Photoshop Users · GitHub](https://github.com/Diolinux/PhotoGIMP/?utm_source=chatgpt.com)
- [Reference for GIMP 3.0 API – GIMP Developer](https://developer.gimp.org/api/3.0/?utm_source=chatgpt.com)
- [Penpot MCP server](https://help.penpot.app/mcp/?utm_source=chatgpt.com)
- [Release notes/1.4 - Inkscape Wiki](https://wiki.inkscape.org/wiki/Release_notes/1.4?utm_source=chatgpt.com)
- [Extensions | Inkscape](https://inkscape.org/zh-hant/develop/extensions/?utm_source=chatgpt.com)
- [Introducing the all-new Affinity: Professional design, now free for everyone](https://www.canva.com/newsroom/news/all-new-affinity/?msockid=00cd9774d1af65a23fe581ecd0116496&utm_source=chatgpt.com)
- [New in Affinity: Scripting and AI automation with Claude](https://www.affinity.studio/blog/affinity-automation-scripting-claude?utm_source=chatgpt.com)
- [Python Scripting — Krita Manual 5.3.0 documentation](https://docs.krita.org/en/user_manual/python_scripting.html?utm_source=chatgpt.com)

## Prompt:
03/10/2026, 01:38:10

Affinity é MIT?

## Response:
03/10/2026, 01:38:18 · gpt-5-6-thinking

> **Pesquisou 2 sites**
>
> 
>
> Pensou por 4s

Não. **Affinity não é MIT e não é open source.** O software é proprietário da Canva/Affinity e seu uso é regido pelos termos de licença próprios da Canva. ([Canva](https://www.canva.com/policies/affinity-additional-terms/?utm_source=chatgpt.com))

O que pode confundir é que, em 2026, o Affinity passou a ser **gratuito para pessoas físicas**, com ferramentas de Pixel, Vector e Layout liberadas. Mas **gratuito ≠ open source**. ([Affinity](https://www.affinity.studio/pt_br?utm_source=chatgpt.com))

Se o critério para o Hermes Work for **“código aberto + permissivo + integrável”**, então eu separaria assim:

- **MIT/Apache:** Graphite é o mais interessante.
- **MPL 2.0:** Penpot.
- **GPL:** GIMP/PhotoGIMP, Inkscape, Krita.
- **Proprietário gratuito:** Affinity.
- **Proprietário pago/ecossistema Adobe:** Photoshop.

Então, se você quer especificamente algo no espírito **MIT**, eu investigaria **Graphite com muito mais atenção que Affinity**.

---

**Sources:**

- [Affinity Terms](https://www.canva.com/policies/affinity-additional-terms/?utm_source=chatgpt.com)
- [Affinity | Software Criativo Profissonal, Grátis para Todos](https://www.affinity.studio/pt_br?utm_source=chatgpt.com)

## Prompt:
03/10/2026, 01:39:35

Alternativas open source ao Affinity

## Response:
03/10/2026, 01:39:44 · gpt-5-6-thinking

Se você quer um **“Affinity open source” de verdade**, a resposta curta é: **não existe hoje um substituto 1:1 maduro que reúna Photo + Designer + Publisher no mesmo app**. O melhor caminho é combinar 2–3 ferramentas, e há um projeto emergente que tenta reduzir essa fragmentação.

> **Pesquisou 8 sites**
>
> 
>
> Pensou por 19s

Sim. Se o que você procura é **“Affinity, mas open source”**, eu dividiria a resposta em duas: o substituto **prático hoje** e o substituto **arquiteturalmente mais interessante para o Hermes Work**.

### O equivalente open source mais próximo hoje

O Affinity atual reúne três disciplinas:

| Affinity | Open source equivalente | Licença | Maturidade |
|---|---|---|---|
| **Affinity Photo** | **GIMP** | GPLv3+ | 🟢 Muito madura |
| **Affinity Designer** | **Inkscape** | GPL | 🟢 Muito madura |
| **Affinity Publisher** | **Scribus** | GPL | 🟢 Muito madura |
| Photo + Designer parcialmente | **Graphite** | **MIT + Apache-2.0** | 🟡 Alpha |
| Designer/UI | **Penpot** | MPL 2.0 | 🟢 Madura |
| Photo/Illustration | **Krita** | GPLv3 | 🟢 Muito madura |

Então, literalmente:

```text
AFFINITY
Photo + Designer + Publisher

          ≈

OPEN SOURCE
GIMP + Inkscape + Scribus
```

O Scribus é particularmente importante aqui porque costuma ser esquecido. Ele cobre justamente a parte **Publisher/InDesign**: layouts multipágina, impressão profissional, CMYK, spot colors, gerenciamento ICC e PDFs para gráfica. ([SourceForge](https://sourceforge.net/projects/scribus/?utm_source=chatgpt.com))

---

## 1. Graphite - o que eu mais observaria

Esse é o projeto que mais parece estar tentando chegar a um verdadeiro:

> **Affinity Designer + Photo open source moderno.**

O Graphite oficialmente se define hoje como um editor **vetorial + raster**, não destrutivo, combinando layers com um sistema procedural baseado em nodes. Está sob **MIT + Apache-2.0**. ([GitHub](https://github.com/GraphiteEditor/Graphite?utm_source=chatgpt.com))

A arquitetura é muito interessante:

```text
             GRAPHITE

Raster ───────┐
              │
Vector ───────┼──→ Layers
              │       +
Procedural ───┘     Nodes
                      ↓
                composição
                      ↓
                   output
```

Isso significa que em vez de:

```text
imagem final
```

você pode ter algo conceitualmente mais parecido com:

```text
[Texto]
   ↓
[Transform]
   ↓
[Gradient]
   ↓
[Mask] ← [Shape]
   ↓
[Blend]
   ↓
[Output]
```

Para **agentes**, isso é excelente.

O agente não precisa pensar:

> "clique no botão X, arraste 30 pixels para a esquerda."

Ele pode pensar:

> "adicione um TransformNode entre Shape e Composite."

### O problema

Ainda está explicitamente em **alpha**. ([GitHub](https://github.com/GraphiteEditor/Graphite?utm_source=chatgpt.com))

Então eu faria:

```text
produção hoje:
Inkscape / GIMP

P&D Hermes:
Graphite
```

Mas, entre tudo que estamos discutindo, **Graphite é provavelmente o projeto que eu acompanharia mais de perto**.

---

## 2. Inkscape - substituto do Affinity Designer

Aqui a equivalência é extremamente clara.

```text
Affinity Designer
       ↓
    Inkscape
```

Ele é um editor vetorial completo, usa **SVG como formato nativo** e trabalha com logos, tipografia, ilustrações, diagramas e materiais gráficos. ([Inkscape](https://inkscape.org/acerca-de/?utm_source=chatgpt.com))

Para o Hermes, há ainda uma vantagem enorme:

**SVG é texto.**

Então o Hermes pode fazer:

```text
Hermes
  ↓
gera SVG
  ↓
abre no Inkscape
  ↓
refina
  ↓
exporta PNG/PDF/SVG
```

Ou sequer abrir a UI:

```text
Hermes
 ↓
SVG
 ↓
Inkscape CLI
 ↓
PNG
```

Isso é uma arquitetura excelente para automação.

---

## 3. GIMP - substituto do Affinity Photo

Essa equivalência também é direta:

```text
Affinity Photo
     ↓
    GIMP
```

O próprio GIMP se posiciona para retoque fotográfico, composição e image authoring e é software livre sob GPL. ([GIMP](https://www.gimp.org/about/?utm_source=chatgpt.com))

Para:

- edição fotográfica;
- máscaras;
- layers;
- recortes;
- composição;
- ajustes;
- filtros;
- processamento raster;

é a escolha OSS mais óbvia.

E para o Hermes existe uma vantagem relevante: ele é muito mais aberto à automação do que ferramentas proprietárias.

---

## 4. Scribus - o componente que fecha o trio

Este aqui merece muito mais atenção.

```text
Affinity Publisher
       ↓
     Scribus
```

Ele é um **Desktop Publishing profissional open source** com suporte a:

```text
CMYK
spot colors
ICC color management
PDF para impressão
layouts multipágina
tipografia avançada
```

([SourceForge](https://sourceforge.net/projects/scribus/?utm_source=chatgpt.com))

Então:

```text
Inkscape → gráficos
GIMP     → imagens
Scribus  → publicação/layout final
```

é basicamente o equivalente FOSS da suíte Affinity.

E existe uma propriedade interessante para automação: o formato de documentos do Scribus é **XML-based e aberto**. ([GitHub](https://github.com/scribusproject/scribus/blob/master/doc/en/index.html?utm_source=chatgpt.com))

Isso abre possibilidades muito interessantes de geração programática.

Por exemplo, conceitualmente:

```text
Hermes
 ↓
dados ACIRV
 ↓
template
 ↓
Scribus/XML
 ↓
Relatório de 30 páginas
 ↓
PDF
```

Aqui já começa a ficar muito relevante para o que você faz.

---

## 5. Krita

Krita não é exatamente um concorrente do Affinity inteiro.

É melhor pensar:

```text
Affinity Photo
       ↕
      Krita
```

mas com foco muito maior em:

```text
drawing
painting
concept art
texturing
illustration
brush engine
```

O próprio projeto deixa claro que não pretende substituir Photoshop; o foco é pintura e criação artística. ([Krita Docs](https://docs.krita.org/en/?utm_source=chatgpt.com))

Está sob **GPLv3**. ([Krita](https://krita.org/pt-br/about/license/?utm_source=chatgpt.com))

Para você eu o colocaria como:

```text
GIMP → fotografia/manipulação
Krita → arte/ilustração
```

---

## 6. Penpot

Penpot também não substitui Affinity inteiro.

Seria mais:

```text
Affinity Designer
      +
Figma
      ↓
   Penpot
```

Mas em **web/UI/layout/design systems**, Penpot é possivelmente superior como arquitetura para o Hermes.

Ele roda no browser, pode ser self-hosted e oferece API/plugin system; hoje a própria plataforma está promovendo workflows para agentes e um MCP aberto. ([Penpot](https://penpot.app/self-host?utm_source=chatgpt.com))

Portanto:

```text
manual graphic design
Inkscape

product/UI design
Penpot

agentic design
Penpot
```

é uma distinção que eu faria.

---

# Se exigirmos licença MIT

A lista muda drasticamente.

É importante distinguir:

```text
Open source ≠ MIT
```

GIMP, Krita, Inkscape e Scribus são GPL. Penpot é MPL.

O grande destaque permissivo aqui é:

> **Graphite - MIT + Apache-2.0.** ([GitHub](https://github.com/GraphiteEditor/Graphite?utm_source=chatgpt.com))

Então, se a questão por trás da pergunta for:

> **“Qual editor eu consigo incorporar profundamente ao Hermes Work, modificar, distribuir e talvez transformar quase em componente first-party?”**

aí eu mudaria bastante o foco:

```text
                    HERMES WORK
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
       PENPOT         GRAPHITE       THREE.JS
       MPL 2.0       MIT/Apache      MIT
          │              │              │
       UI/design       2D engine       3D/web
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                      Remotion
```

**Graphite fica muito mais estratégico nesse cenário do que GIMP.**

---

## Minha divisão para o Hermes Work

Eu não tentaria encontrar **um** software para fazer tudo. Criaria uma Creative Toolchain:

```text
HERMES CREATIVE WORKSTATION

Design/UI
└── Penpot

Vector / SVG
├── Inkscape
└── Graphite ★

Raster
├── GIMP
└── Krita

Publishing
└── Scribus

Motion
├── Remotion
└── Cavalry

3D / realtime
├── Three.js Editor
└── Blender
```

E existe uma diferença conceitual importante:

```text
                    AGORA

Affinity
= excelente aplicativo criativo

GIMP + Inkscape + Scribus
= excelente suíte FOSS

FUTURO

Graphite
= potencial engine gráfico 2D do Hermes

Penpot
= potencial workspace visual do Hermes

Three.js
= engine visual 3D/realtime

Remotion
= engine temporal/vídeo
```

Para **substituir Affinity hoje**, eu escolheria **GIMP + Inkscape + Scribus**.

Para **construir o Hermes Work**, eu ficaria muito mais interessado em **Penpot + Graphite**, especialmente porque Graphite tem justamente a combinação rara de **raster + vetor + procedural + licença MIT/Apache** que você está procurando. ([GitHub](https://github.com/GraphiteEditor/Graphite?utm_source=chatgpt.com))

---

**Sources:**

- [Scribus download | SourceForge.net](https://sourceforge.net/projects/scribus/?utm_source=chatgpt.com)
- [GitHub - GraphiteEditor/Graphite: Community-built comprehensive 2D content creation appplication for graphic design, digital art, and interactive real-time motion graphics powered by a node-based procedural graphics engine · GitHub](https://github.com/GraphiteEditor/Graphite?utm_source=chatgpt.com)
- [About | Inkscape](https://inkscape.org/acerca-de/?utm_source=chatgpt.com)
- [GIMP - About GIMP](https://www.gimp.org/about/?utm_source=chatgpt.com)
- [Welcome to the Krita 5.3 Manual! — Krita Manual 5.3.0 documentation](https://docs.krita.org/en/?utm_source=chatgpt.com)
- [Licença | Krita](https://krita.org/pt-br/about/license/?utm_source=chatgpt.com)
- [Self-host Penpot: Deploy it anywhere](https://penpot.app/self-host?utm_source=chatgpt.com)



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)