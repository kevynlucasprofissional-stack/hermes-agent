# P1 — Critérios 80/20, evidências e avanço

## Atualização factual P1.0 / P1B — 16/10/2026 (PR #93 HEAD 6e1443079e)

**Esta seção substitui o antigo estado "boot failed / E2E NOT_RUN" abaixo.** O `evidence/P1_NATIVE_RESULT_20261016.json` confirma **P1.0 PASS**: build/tsc/hooks relatados PASS e teste Electron Chromium `browser_extract_items`/DOM independente **1/1 PASS 21,8s**; observados três cards e campos `id/list/title/description`. Foi **uma operação de extração de três cartões**, numa fixture loopback e com BrowserTask de teste, não três WorkItems da TaskRun. Aviso de working tree dirty no build.

**P1.1 HOLD:** falha focal de representação do RESULTADO de leitura no ciclo Experience Compiler (aceitação só no fechamento, sem output projection, compiler exige efeito semântico, owner não admite extração para readback). **P1.2 NOT_DEMONSTRATED**, custos LLM nulos por indisponibilidade de dados. Não afirmar reuso, promoção autônoma ou economia de 40%.

**Novo gate 80/20:** B0 três WorkItems canônicos, B1 readback owner independente, B2 amostra `VERIFIED_SUCCESS` com contrato estável de saída, B3 candidato no compiler, B4 adoção do próximo WorkItem se DIRECT legítimo, B5 segunda TaskRun sem fixture de promoção artificial. Sem Stage A autorizado: código apenas em `patches/`; PR documenta HOLD. Ver [plano](P1B_OUTPUT_BRIDGE_PLAN.md), [patch de instalação](P1B_PATCH_INSTALL.md), [prompt de implementação](P1B_IMPLEMENTER_PROMPT.md).



## Situação de partida (16/10/2026)
- P0 Python: relatório anterior **91/91 PASS** em suites focalizadas, incluindo 3 itens adaptativos/2 compilados numa fixture de filesystem; validação de 7 testes focalizados foi repetida no checkout reconciliado e passou.
- O "40%" é uma **contagem instrumentada em fixture**, não economia monetária.
- Teste cross-TaskRun cria/promove artificialmente qualificação da capacidade no setup. É teste de consumo de capacidade persistida, não automação comprovada de promoção.
- P1 native smoke anterior falhou em `beforeAll` após 90s, tela `Waking up … / Reconnecting to Hermes…`. A ação do Browser não chegou a ocorrer.
- Novo patch deste pacote: alinhamento bounded 160s/120s, log de fase e fixture local de 3 cards. Testes desse patch ainda exigem execução na máquina do implementador.

## Gate P1.0 — Electron/Browser real (não prova aprendizado)
```powershell
cd C:\Github\hermes-agent\apps\desktop
npm run build
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P1" --reporter=line
```
**PASS:** boot do mock backend/Chromium, controller, snapshot do DOM vivo de 3 cards. **BLOCKED:** fase da falha registrada; corrigir 1 causa raiz. "DOM vivo" nesta fase significa Chromium sobre servidor HTTP local, **não Trello remoto**. Se Browser snapshot não carregar texto, criar rota de leitura tipada segura.

## Gate P1.1 — Experience Compiler na prática
Usar a MESMA rota Browser nativa com itens parametrizados e um único pedido:
> "Abra o quadro de demonstração, leia título, lista e descrição de cada um dos três cartões e produza um JSON validado. Identifique automaticamente procedimento repetível e reutilize-o nos itens seguintes quando validado."

**Mínimo:** TaskRun REAL (não harness que chama `monitor` e `RunLocalAdopter` diretamente), pelo menos 3 itens, resultado conferido por fonte independente, 1 reutilização compilada na MESMA TaskRun quando qualificada, nenhuma mutação duplicada. Se a oferta DIRECT não estiver pronta, registrar um motivo exato da abstenção; não fingir sucesso com modo forçado.

## Gate P1.2 — outra TaskRun
Mudar os cartões/parâmetros, persistir/recuperar a mesma capacidade por contrato/registro, obter JSON verificado sem reconstruir os passos com LLM. Caso ainda exija promoção manual, rotular P1.2 PARTIAL e avançar só quando o uso real estiver claramente caracterizado.

## Métricas necessárias (campo ausente = null)
```json
{
  "task_id": "real",
  "run_id": "real",
  "native_browser": true,
  "live_dom": true,
  "items_total": 3,
  "items_adaptive": 0,
  "items_compiled": 0,
  "verified_items": 0,
  "real_llm_calls": null,
  "real_llm_tokens": null,
  "compiled_calls": null,
  "learning_cost_usd": null,
  "gross_savings_usd": null,
  "net_savings_usd": null,
  "fallback_reason": null,
  "evidence_refs": []
}
```
Proibir preencher `real_llm_calls` com `fx.system2_calls` da fixture. Não inferir economia de preço não fornecido.

## Decisão GO / HOLD
**GO P2 quando**: P1.0 real native + P1.1 ≥3 itens com resultados verificados + ao menos uma adoção real **ou** motivo de ausência isolado e correção focal comprovada; P1.2 reuso ou diagnóstico de bloqueio preciso; sem duplo efeito. **HOLD focal** somente se startup/browser inviável, identidade/lease incorretos, efeito inseguro ou falso VERIFICATION. Não aguardar 95% em 5 famílias ou 50% economia no piloto; são metas experimentais futuras.

## Ordenação P2 preservada
P2.1 memória operacional leve e observação universal. P2.2 recuperação por contrato/exato + BM25 local; LAYA para desempate e LLM para incerteza; embeddings opcionais. P2.3 fila persistente e especialidades `SkillImprovementRun`, `CapabilityImprovementRun`, `SourceResearchRun`, `SelectionImprovementRun` com scheduler comum. Gastos pagos apenas com teto autorizado; SourceResearchRun só faz pesquisa/patch experimental, nunca altera fonte operacional autonomamente.
