---
name: instagram-web-ops
description: Read-only Instagram web operations through the authorized native Browser (perfil, post a post, painel de 30 dias, legendas em lote, stories arquivados)
version: 1.0.0
native: true
auto_update: true
site_map: site-ops/maps/instagram-web.json
ops_notes: C:/Github/ACIRV-Notebook/Hermes/instagram-insights/ferramentas/publicacoes_feed.py
---

# Instagram Web Operations — Native Skill

Mapeamento operacional do Instagram web feito com a conta **@acirvoficial** logada no
browser interno do Hermes. Complementa `instagram-post-metrics-reporting` (que traz o
pipeline de bases canônicas) com o **mapa do site**: rotas, seletores, o que funciona,
o que está bloqueado e por quê.

Mapa versionado: `site-ops/maps/instagram-web.json`. Se um seletor mudar, atualize o mapa
antes de mudar o playbook.

## As quatro regras que não se quebram

1. **Contagem de período = conjunto de shortcodes**, nunca o total de itens do grid.
   Um período fechado só vale com o inventário validado contra uma referência.
2. **A varredura longa do grid perde linhas.** O grid é virtualizado: rolar de uma vez
   com `scrollTo(0, document.body.scrollHeight)` (ou até passos de 900 px) pula lotes.
   Use passos de ~500 px com espera de ~300 ms e colete a cada passo.
3. **Nunca somar as três camadas**: post a post, painel da conta (30 d) e stories são
   fontes distintas, com janelas distintas. O painel de 30 dias é janela móvel: registre
   `janela_estimada` junto do payload.
4. **Legenda é campo obrigatório de toda rodada** e vem da API de mídia, não do grid.

## Rotas

| Rota | Para que serve | Autoridade |
|---|---|---|
| `/acirvoficial/` | inventário do feed (shortcodes) | conjunto de posts |
| `/insights/media/<media_id>/` | métricas de um post | post a post |
| `/accounts/insights/?timeframe=30` | agregado da conta | painel 30 d |
| `/accounts/insights/content/?media_type=...` | ranking de itens | cross-check |
| `/archive/stories/` + `/stories/archive/<dayId>/` | stories expirados | contagem por dia |

## Workflows

### 1. Inventário do feed (com data sem abrir post)

```js
// decoder: shortcode -> media_id (ms epoch)
var A='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
function dec(sc){var n=0n;for(var i=0;i<sc.length;i++)n=n*64n+BigInt(A.indexOf(sc[i]));return Number(n>>23n)+1314221100000}
window.__M=window.__M||new Map();
function col(){[].slice.call(document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]')).forEach(function(a){
  var s=(a.getAttribute('href')||'').match(/\/(?:p|reel)\/([A-Za-z0-9_-]{11})/);
  if(s&&!window.__M.has(s[1]))window.__M.set(s[1],dec(s[1]))})}
// 5 passos por chamada (~1,5 s). Mais que isso estoura o dispatch do browser_console.
for(var i=0;i<5;i++){window.scrollBy(0,500);var t=Date.now();while(Date.now()-t<300){};col()}
```

Regras de aceitação:
- Rode **duas varreduras independentes** (recarregue a página entre elas). Se o conjunto do
  período for idêntico nas duas, a contagem está corroborada.
- A varredura que chega ao mês alvo pode ter vindo incompleta nos meses anteriores
  (observado: 46 de agosto contra 62 conhecidos). Não use o total global como prova;
  use o conjunto do período.
- Diferença de 1–2 min entre data decodificada e `taken_at` é arredondamento. `taken_at`
  manda.

### 2. Painel de 30 dias

Navegue para `/accounts/insights/?timeframe=30`, espere ~3 s, leia
`document.body.innerText` e grave com `janela_estimada`. Nunca trate como "o mês".

### 3. Métricas post a post

`/insights/media/<media_id>/` — o `media_id` é o **inteiro do shortcode**, não o timestamp
decodificado. O snapshot abre às vezes com um bloco `Curtidas / 1`; registre o texto bruto.
Espere ~5 s antes de ler.

### 4. Legendas em lote (varredura de segundo plano)

```js
window.__Q=[{id:'<media_id>',sc:'<shortcode>',ta:<taken_at>}, ...];
window.__L=[];
window.__go=async function(){while(window.__Q.length){var q=window.__Q.shift();
  try{var r=await fetch('/api/v1/media/'+q.id+'/info/',{credentials:'include',
    headers:{'x-ig-app-id':'936619743392459'}});var j=await r.json();var it=j.items&&j.items[0];
    window.__L.push({id:q.id,sc:q.sc,ta:it.taken_at,mt:it.media_type,pt:it.product_type,
      cap:it.caption?it.caption.text:null,lk:it.like_count,cm:it.comment_count})}
  catch(e){window.__L.push({id:q.id,sc:q.sc,err:1})}}};
```

Ritmo: ~1 chamada/s. Depois de ~50 chamadas rápidas a API devolve 429 (e
`web_profile_info`/`feed/user` passam a 404/429) — não insista, espere ou mude de rota.
Grave o resultado no disco **pelo sink** antes de qualquer navegação de topo.

### 5. Sink local (sem diálogo de download)

```bash
cd ~/.hermes/skills/productivity/instagram-post-metrics-reporting/scripts
python sink_save.py 8791     # destino = captura/<mes>-<ano>
curl -s http://127.0.0.1:8791/health
```

No browser, navegação de topo:

```js
var s=JSON.stringify(payload),b=btoa(unescape(encodeURIComponent(s)));
location.href='http://127.0.0.1:8791/salvar?nome=_arquivo.json&d='+encodeURIComponent(b);
```

`/health` responde `{"ok":true,"destino":...}`. Se responder `{"error":"Não encontrado"}`,
a rota está errada (é `/health`, não `/`), não o sink.

### 6. Auditoria antes de publicar número

```bash
python ferramentas/publicacoes_feed.py auditar --periodo 2026-10
```

Só publique contagem com veredito `COMPLETO`. Referência por período fica em
`registro_fontes` (`grid_out` para outubro). Post sem legenda por natureza entra em
`SEM_LEGENDA_POR_NATUREZA` — hoje `DcCPbyLGzGd` e `Dez7NIBtL71`.

## Stories arquivados — estado real (02/11/2026)

Funciona: o painel `/archive/stories/` lista os dias, clicar num dia expõe o
`archiveDayId` em `/stories/archive/<id>/` e o viewer abre os stories daquele dia.

Não funciona (testado a fundo, não repetir):
- `GET /api/v1/archive/reel/day_shells/` → `{"error":1357004,"__ar":1}`; o token é de uso
  único e o replay é recusado, mesmo com cookies + `x-csrftoken` + `x-ig-app-id`.
- `POST /api/v1/feed/reels_media/` com `reel_ids=["archiveDay:<id>"]` → 1357004 (CSRF) ou
  HTML de 500 KB; nenhuma combinação de `x-ig-www-claim`, `x-asbd-id`,
  `x-instagram-ajax`, `x-requested-with` passou.
- Hook em `window.fetch` depois do load **não** captura as chamadas do app (referência
  original já guardada). Hook em `Response.prototype.json/text` funciona, mas só para
  chamadas futuras — e dias já visitados vêm do cache, sem request.
- `/accounts/insights/content/?media_type=stories` mostra só os itens de melhor
  desempenho (19 em 02/11/2026), não o inventário.

Caminho que ainda não foi tentado: recarregar o painel, armar `Response.prototype` **antes**
do primeiro clique num dia nunca visitado e ler o corpo do GraphQL do viewer; ou capturar o
`day_shells` no load via `Network.getResponseBody` sobre um cliente WebSocket do CDP.

## Limites de operação

Somente leitura: inventariar, medir, listar. Publicar, comentar, curtir, seguir e alterar
perfil não são operações deste mapa e exigem autorização explícita.
