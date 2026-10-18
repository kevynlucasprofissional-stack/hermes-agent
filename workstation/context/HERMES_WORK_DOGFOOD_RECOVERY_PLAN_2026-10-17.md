# Hermes Work — Recuperação operacional pós-dogfood (17/10/2026)

> **Status:** investigação e plano; **NÃO IMPLEMENTADO**. Este documento reconcilia o relatório de sessão real e a inspeção do código em `main`. Nenhum defeito foi marcado como resolvido por criar este plano.
> **Baseline remoto:** `main` em 17/10/2026. **Atenção:** a working tree local de `C:\Github\hermes-agent` possui alterações não commitadas de outros trabalhos; não tocar nelas. Sempre verificar HEAD/build realmente executado.
> **Decisões:** D-046 baixo acoplamento, D-047 demonstração humana, D-048 (este plano).

## Fontes e contradições verificadas

- Dogfood real: `workstation/dogfood/17.10.26.md`; sessão `20261017_150608_11f39d`; LearningSession `learn-1792260534434-05158b7f` em `%APPDATA%\Hermes\workstation\learning-sessions`. Evidências no PC autorizadas; não colocar dados privados ou logs brutos no GitHub.
- O vídeo indicado como gravado não é uma gravação da aba: `apps/desktop/electron/workstation-learning-session.ts::startVideoRecording` usa `lavfi color=c=black:s=1280x720:r=15` e `-t 1`. `videoStatus=stopped` não implica captura visual válida. As afirmações M0/M1/M2 "implementado" nos documentos prévios são **claims de teste contratual**, não qualificação por dogfood real.
- `generateCandidate` formula questões a partir de um gesto isolado; `pointerup` gera template de coordenadas de Canvas. A demonstração local contém 321 gestos, 9 perguntas e correções humanas úteis, mas não observação visual corroborada.
- `record_human_demonstration_candidate` existe em `workstation/skill_learning.py`, porém a inspeção não encontrou chamada de produção a partir de `LearningSession.stop` (fora testes). M2: fronteira estática presente; ligação operacional não comprovada.
- Há uma implementação existente para ocultação de vista nativa: `apps/desktop/src/app/browser/native-view-occlusion.ts`, usada em Hub e Chat, que chama `setVisible` no owner de `workstation-browser-runtime.ts`. O bug de tela preta na pesquisa/notificação pode ser overlay + reattach/host, mas **a causa não foi confirmada**. `ERR_ABORTED (-3)` visto em navegação é indício, não causa definitiva.
- `workstation/execution_policy.py` pode produzir `SUGGEST_COMPILE`, mas `workstation/task_compiler.py` tem gate para `REQUIRE_COMPILE`; ações JS opacas continuam inelegíveis em `workstation/procedure_trace.py`. Não promover JavaScript, âncoras semânticas declaradas pelo LLM ou recibos inventados.
- O evento `review.summary` aparece no chat por `apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/status.ts`; aproveitá-lo como padrão de apresentação, sem introduzir canal/event bus paralelo.

## Seis problemas do dogfood e aceitação

| ID | Prioridade | Evidência | Gate de aceitação |
|---|---|---|---|
| DF-01 formato do convite | P1 | Briefing incompleto na sessão | Antes de iniciar edição pergunta **uma** especificação determinante (ex.: destino/formato), quando realmente ausente; não pergunta quando já dada |
| DF-02 controle PhotoCraft | P1 | Dependência de scripts auxiliares Python e Canvas difícil | Operação tipada/visual autorizada funciona num caso mínimo com verificação; scripts ad hoc não se tornam capacidade promovida automaticamente |
| DF-03 cartões Aprender | P1 | Aparecem sobre editor | Hipótese e Confirmar/Corrigir/Adiar/Dispensar no próprio transcript do chat, sem overlay do Canvas, conservando sessão e intensidade |
| DF-04 pesquisa browser preto | P0 | Navegação com viewport preto | Pesquisa e troca Hub/Chat rendem conteúdo; se falha houver status recuperável, evento de diagnóstico e sem reload destrutivo |
| DF-05 notificação browser preto | P0 | Sobreposições/notificações | Overlay/toast abre e fecha sem view permanentemente desmontada; respeita z-order, owner, epochs e view/sessão original |
| DF-06 observabilidade | P1 | Compilação/capacidades invisíveis no chat | Eventos auditáveis com `task_run_id`, `learning_session_id`, `capability_id`, `evidence_ref`, `state` e resultado reais, sem PII, com dedupe e replay |

## Execução ótima: seis prompts sequenciais (dois conjuntos leves e quatro problemas de concentração)

1. **P01 — Browser nativo P0 (exclusivo):** `native-view-occlusion.ts`, Hub, chat pane, `workstation-browser-runtime.ts`, overlays. Diagnosticar `setVisible`, `attach`, `setBounds`, `removeChildView`, host/owner, falha de navegação; harness reproduzível Windows Electron. Gate: pesquisa + toast + dialog + alternância mantém WebContentsView original.
2. **P02 — Captura real P0 (exclusivo):** `workstation-learning-session.ts` + screenshot owner no runtime. Substituir `lavfi` por frames `webContents.capturePage()` com backpressure, encoder de vídeo e snapshots indexados; vídeo não preto com duração correta + sinal claro de erro, isolamento e consentimento.
3. **P03 — UX conversacional e eventos P1 (conjunto leve):** `learning-controls.tsx`, Chat session message UI, `status.ts`, IPC/preload e evento canônico. Separar controle Aprender de cartão de pergunta, renderizar no transcript e publicar milestones reais de compilabilidade/capacidade.
4. **P04 — Question Engine contextual + ponte CandidateLesson P1 (exclusivo):** agrupar gestos, usar snapshots/correções, custo de perguntas por intensidade; integrar stop/review ao Python sem nova memória, produzir apenas candidatas inertes com hashes/referências verificadas.
5. **P05 — Briefing criativo e operação PhotoCraft P1 (conjunto leve):** `workstation/work_intent.py`, roteamento de criatividade, skill existente e contrato browser; perguntar somente formato essencial, preferir comandos tipados/DOM/visão antes de scripts externos; prova de convite num fixture sem envio/edição de ativos privados.
6. **P06 — Compilação e reutilização autênticas P1/P2 (exclusivo):** `execution_policy.py`, `procedure_trace.py`, `task_compiler.py`, `control_plane/router.py`, `integrations/hermes/operational_resolution.py` e `run_local_adoption.py`. Tornar `SUGGEST_COMPILE` consumível, provar Candidate -> qualificação -> capacidade tipada -> segunda TaskRun seleção com readback e economia medida; sem promoção de JS opaco.

## Dependências, cortes 80/20 e regra de GO

- Ordem preferida **01 → 02 → 03 → 04 → 05 → 06**. P01/P02 são tecnicamente independentes, mas não desenvolver simultaneamente na mesma worktree; todos devem trabalhar sobre base e docs reconciliados. P03 deve preceder dogfood P04; P06 exige os contratos e evidências das anteriores.
- **Parar cada prompt ao satisfazer seu gate**: não continuar ampliando arquitetura após prova boa o suficiente. Reportar PASS/HOLD com caminho para evidências e comparação com baseline; falha real não vira sucesso "por mock".
- Não criar outro navegador, canal Gateway, compilador, banco, motor criativo, tela ou roteador. Utilizar mecanismos atuais e adapters pequenos.
- Nunca alterar a `main` ou limpar worktree suja; integração por branch/PR, com um owner por conjunto de arquivos. E2E externo, WhatsApp e editores profissionais: usar fixtures locais/dados sintéticos sem efeitos em terceiros.
- Captura de imagem/vídeo requer consentimento explícito, origem autorizada e proteção contra login/credenciais; não guardar capturas sensíveis no Git.
- Não exigir FPS alto: priorizar captura válida, custo finito e sincronização por timestamps. `capturePage` pode ter impacto de performance; testar em Chromium real no Windows.
- Consultar `workstation/context/HERMES_WORK_DOGFOOD_PROMPTS_2026-10-17.md` para os prompts operacionais completos.

## Fontes técnicas externas

Documentação Electron: `https://www.electronjs.org/docs/latest/api/web-contents-view`, `https://www.electronjs.org/docs/latest/api/web-contents` e `https://www.electronjs.org/docs/latest/api/view`. Em particular, `contentView.addChildView` reordena a view já presente para o topo; isso exige checar occlusão ao reanexar. `webContents.capturePage` retorna `NativeImage`; **não** codifica vídeo por si só.
