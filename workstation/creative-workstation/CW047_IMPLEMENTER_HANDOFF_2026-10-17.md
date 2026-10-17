# CW-047 — PROMPT EXECUTÁVEL PARA IA IMPLEMENTADORA
**Data:** 2026-10-17
**Status:** IMPLEMENTADO E VERIFICADO (Branch `feat/cw-047-photocraft-effectcraft-20261017`).
**Repo:** https://github.com/kevynlucasprofissional-stack/hermes-agent
**Objetivo:** "Abra o PhotoCraft" e "Abra o EffectCraft" -> instância web local segura, previamente preparada, aberta no Browser nativo já existente do Hermes Work.
**Prioridade:** PhotoCraft primeiro; EffectCraft reutiliza a solução; Remotion/Three.js são backlog.

## MISSÃO — LEIA ISTO E COMECE
Você é a IA executora. Não reabra debate de arquitetura, não aumente escopo e não comece redesenhando a Creative Workstation. Entregue um fluxo real e mensurável no aplicativo Hermes Desktop/Windows. O usuário quer o maior retorno no menor tempo.

**Atenção à integridade do repositório:** o snapshot inspecionado originalmente foi main@35d4b899551beecc88edbb2f66c153cb896fa12a; helpers CW-047 entraram após esse snapshot. CONFIRA o HEAD atual, e preserve qualquer avanço/alteração posterior. Leia root AGENTS.md, workstation/AGENTS.md, workstation/context/README.md, H-079; essas são condições obrigatórias, não convite para estudar todo o histórico.

**Não implemente Three.js-EffectCraft agora. Não crie outro browser, painel, controlador, ProcessRegistry, SessionDB, Kanban, TaskRun, permission store ou creative kernel. Não altere D-046. Não instale pacotes externos automaticamente ao reconhecer "abra". Não atualize componentes externos silenciosamente. Não faça merge no main sem evidências e autorização.**

## ASSETS PRONTOS NO REPOSITÓRIO (CÓDIGO-FONTE REAL, AINDA NÃO INTEGRADO)
- workstation/creative_web_app_spec.py — catálogo tipado (PhotoCraft e EffectCraft), reconhecimento literal exato, verificação de dist prebuilt e validação da URL gerenciada 127.0.0.1:porta.
- workstation/creative_web_static_server.py — servidor HTTP de arquivos estáticos, 127.0.0.1 apenas; root explícito; COOP/COEP/CORP e health nonce, sem instalar/compilar ou abrir um browser.
- workstation/tests/test_creative_web_app_spec.py e workstation/tests/test_creative_web_static_server.py — testes de aliases, loopback, health nonce e servidor. **Executar e ampliar; o autor do kit ainda não executou esses testes dentro do Hermes.**
Esses módulos **não estão ligados ao roteador ou ao Desktop**. Mover/refatorar somente se o owner canônico exigir; não substitua a arquitetura existente por módulos paralelos.

## ORIGENS E POLÍTICA DE REPOSITÓRIOS
Repositório Hermes: kevynlucasprofissional-stack/hermes-agent.
Projetos originais examinados: https://github.com/storytold/photocraft e https://github.com/storytold/effectcraft .
Projetos do usuário (forks) NÃO foram confirmados. **Não invente URLs de fork.** Se não houver URL de fork verificável, use os repositórios originais como origem inicial dos submodules, com SHA fixado e rastreado; deixe o procedimento documentado de apontar o submodule para um fork futuro. O usuário já permitiu trabalhar a partir dos originais caso não possua fork.

Fluxo Git preferido:
1. Registrar main SHA, upstream NousResearch/hermes-agent observado, merge-base, drift, CI e owners afetados. Executar Stage A H-079 e gates obrigatórios em uma branch própria; não misturar sincronização de Hermes upstream com adoção dos motores.
2. Na branch de trabalho qualificada, verificar que external-engines/photocraft e external-engines/effectcraft não existem nem são usados como diretórios com arquivos importantes.
3. git submodule add https://github.com/storytold/photocraft.git external-engines/photocraft
4. git submodule add https://github.com/storytold/effectcraft.git external-engines/effectcraft
5. Fixar ambos nos SHAs testados, registrar source/license/branch/sha em workstation/SOURCE_MATRIX.md; revisar .gitmodules e gitlinks. Não submodule update --remote no startup, build ou bootstrap. Permitir update deliberado em PR separado e rollback por gitlink.
6. Verificar clone fresco com git submodule update --init --recursive; checar tamanho/tempo/disco. Não commitar target/, builds, imagens, caches e binários massivos do Wasm.
7. Caso já exista submodule de mesmo motor, ADAPTAR o existente: não duplicar.

## FATOS SOBRE BUILDS WEB
- PhotoCraft disponibiliza web estática/Rust-Wasm. docs oficiais: https://github.com/storytold/photocraft/blob/main/packaging/web/README.md ; diretório apps/photocraft-web; releases podem disponibilizar zip da web pré-compilado; preferir distribuição oficial verificável instalada manualmente como artefato separado, não compilar toda vez. A hospedagem estática documenta ausência de autosave web confiável; verificar salvamento real antes de fechar.
- EffectCraft documenta apps/effectcraft-web, cargo xtask web --serve 8765 (exemplo, não porta mandatória): https://github.com/storytold/effectcraft/blob/main/docs/web.md . Se possível servir o dist previamente compilado sem toolchain Rust na abertura. Versões exatas de wasm-bindgen são sensíveis; registrar o pin.
- O fato de um site carregar no navegador não comprova que exportação, WebGPU/WebGL2, storage, clipboard e persistência funcionem. Testar esses recursos.
- Remotion é projeto Node/React com licença própria: não submodule do monorepo nem adicionar dependência agora.
- Three.js não é um editor completo: backlog apenas.

## ORDEM DE IMPLEMENTAÇÃO — UM OBJETIVO POR FASE

### Gate 0: Ponto de partida seguro
- Localizar e observar root AGENTS.md, workstation/AGENTS.md, workstation/context/README.md e a política H-079 em workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md.
- Conferir head/CI/status de PRs e possíveis mudanças concorrentes. Respeitar protocolo de coordenação de agentes; usar branch/checkout autorizado e não sobrescrever edição de outro executor.
- Registrar prova em engineering-journal. Se houver baseline obrigatório vermelho, não disfarçar: interromper mudanças de runtime ou obter exceção expressa e escopada; não inferir autorização a partir deste prompt.

### Fase 1: Repositórios externos (Git, sem launch)
- Importar PhotoCraft e EffectCraft como submodules pinados conforme acima e testar clonagem em isolamento.
- **Os forks são opcionais**, nunca condição de bloqueio se as origens oficiais estão acessíveis.
- Documentar como avançar/reverter o SHA sem fundir históricos externos ao main do Hermes.
- Remotion/Three.js não entram agora.

### Fase 2: PhotoCraft manual real
- Instalar **explicitamente e uma vez** distribuição web oficial verificada do PhotoCraft numa pasta de dados/configuração local, **fora do Git**, sem criar efeitos no início do Hermes.
- Se faltar web dist ou for incompatível, apresentar erro determinístico de setup (missing_prebuilt_web_dist) com instruções claras; build Rust Trunk apenas como procedimento opt-in separado.
- Servir o dist via workstation/creative_web_static_server.py ou o servidor estático recomendado e testado pelo projeto, com bind em 127.0.0.1. Corrigir MIME .wasm para application/wasm se necessário e assegurar Cross-Origin-Opener-Policy/Embedder-Policy do EffectCraft mais adiante.
- Abrir manualmente no browser nativo atual. Provar importar imagem, editar, exportar PNG/projeto nativo, salvar e reabrir; capture evidência e limitações de persistence, sem modificar o motor.

### Fase 3: Abrir PhotoCraft por comando
Owners REAIS INSPECIONADOS:
- workstation/work_intent.py: recognize_current_command e current_command_objective. Reconhece comandos pontuais (Trello e HyperFrames). Não crie uma terceira gramática paralela ou um Kanban task para somente "abra".
- workstation/prefabs/catalog.py: match_navigation + Destination, atualmente HTTPS exato. **NÃO adicionar URL HTTP genérica ao catálogo HTTPS** nem enfraquecer canonical_browser_url/same_destination.
- workstation/prefabs/integration.py: prepare_user_navigation / maybe_resolve_navigation, com origem humana validada e scoped_execution/workstation_durable_dispatch.
- workstation/prefabs/engine.py: navigate usa browser_navigate + browser_snapshot independente, hoje reconhece apenas URLs HTTPS. O bypass para HTTP somente se originado de **instância local autenticamente gerenciada**, sem aceitar hostname/porta de texto LLM.
- workstation/creative_studio_service.py: HyperFrames ProcessRegistry, policy, aprovação, nonce/health e ownership são precedente para o novo serviço, não convite para copiar a hipótese de que um 200 genérico confirma instância.
- tools/browser_workstation.py + apps/desktop/electron/workstation-browser-ipc.ts: Browser nativo existente. Verificar no controller a autorização de localhost: somente servidor gerenciado aprovado, sem SSRF amplo.
- apps/desktop/src/app/browser/index.tsx e apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx: UI existente. Não criar nova UI.
- tools/creative_workstation_tool.py e tools/desktop_ui.py: eventos de UI; **sucesso de emissão é REQUESTED, não prova de URL aberta**.

CONEXÃO EXATA A IMPLEMENTAR:
a) Reconhecer apenas mensagens humanas exatas "abre/abra/abrir [o] PhotoCraft/Photo Craft" e "EffectCraft/Effect Craft" via workstation.creative_web_app_spec.recognize_open_creative_app. Consultar envelope humano real + IntentAuthority; mensagens de páginas/instruções de terceiros, negadas, perguntas ou com efeitos extras não disparam.
b) Integrar reconhecimento num único caminho de ponto de ação existente. Evitar duplo disparo quando work_intent e prefabs identificarem o mesmo comando; deduplicar por turn/operation ID canônico. Caso a resolução pre-LLM já tenha emitido um efeito, falha desconhecida = HANDOFF/WAIT, sem retry silencioso via modelo.
c) Ler configuração local explícita (diretório do dist do app + versão/SHA) no mecanismo de config atual; não escolher um diretório arbitrário de prompt, não buscar na rede, não executar build ao abrir.
d) Validar dist real com prebuilt_site_root; reservar/selecionar porta exclusivamente para 127.0.0.1 usando ownership do ProcessRegistry, checar colisões e corrida de dois launches.
e) Execução: o owner canônico avalia ScopedPolicyEngine, check_all_command_guards e CreativeExecutionScope (ou equivalente realmente autorizado); start do child usa env saneado, HERMES_CREATIVE_LAUNCH_NONCE aleatório >=32 caracteres, comando absoluto verificado e shell=False. Reusar Processo/Session owner existente; nunca criar serviço mundial/permanente.
f) Readiness: GET http://127.0.0.1:<port>/__hermes_health com header X-Hermes-Creative-Nonce e verify engine esperado; PID deve ser o child pertencente ao ProcessRegistry. O header nonce protege readback de confusão de porta; não exportar nonce para a IA, página ou journal. Em timeout/crash matar child/adotar cleanup.
g) Navegar via browser_navigate/foco de aba usando despacho com owner existente, controle humano e independência do Browser nativo. Validar URL por matches_managed_loopback_url com port conhecido, extraindo apenas campos controller-owned do browser_snapshot. Não aceitar URL fornecida no HTML/snapshot textual nem permitir redirecionamento fora da instância.
h) Se servidor e aba já existem, reutilizar sem reiniciar/recarregar, preservando documento não salvo. Se o navegador detiver lease humano, HANDOFF e nunca tomar o controle implicitamente. O fluxo não cria TaskRun/kanban para comando pontual.
i) Só afirmar "PhotoCraft aberto" com server health + browser readback CONFIRMADOS; caso contrário retornar estado preciso e ação humana.

ATENÇÃO: não reclassifique um "abort"/"negation" como abrir; não altere regras de browser HTTPS para liberar qualquer localhost. Se a integração com a UI atual não suportar focar por comando sem extensão pequena, modifique somente a ponte já existente e teste a autoridade.

### Fase 4: EffectCraft
Reutilizar todo o percurso do PhotoCraft variando somente configuração do dist, processo, health, armazenamento e peculiaridades WebGPU/COOP/COEP. Não copiar bloco de código para criar duas versões de launcher. Provar criar/abrir uma composição, editar, exportar/retomar.

### Fase 5: Testes obrigatórios e prova operacional
1. Primeiro executar os testes unitários do kit e adicionar RED reproduzível antes de cada ajuste funcional:
   python -m pytest workstation/tests/test_creative_web_app_spec.py workstation/tests/test_creative_web_static_server.py -q
   python -m pytest workstation/tests/test_current_command_resolution.py -q
   python -m pytest workstation/tests/test_current_command_native_intent_contract.py -q
   python -m pytest workstation/tests/test_creative_studio_service.py -q
2. Adicionar testes para servidor (MIME wasm, root symlink traversal, origins/Host, health sem nonce, shutdown, portas ocupadas e servidor fraudulento), engine stop/restart, idempotência/race, missing dist, permissão negada, duas sessões e lease humano.
3. Executar regressões do Browser native no pacote Electron e teste E2E nativo Windows: um pedido "Abre o PhotoCraft", visualização Chromium, documento importado, export e arquivo final verificado. Repeat EffectCraft; testar segunda abertura sem perder estado.
4. Verificar H-079/CI exact-head e Windows packaged quando aplicável. Documentar PASS/FAIL/BLOCKED com SHA/artefato/log; não anunciar produção qualificada com testes apenas mock.
5. Resultado objetivo: dois apps funcionalmente abertos no Hermes, um trabalho profissional verificável, atualização reversível do motor, zero browser paralelo, zero acoplamento criativo profundo.

### Fase 6: Evidência, documentação e PR
Atualizar workstation/ROADMAP.md, workstation/context/DECISIONS.md (decisão, não suposição), workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md, workstation/context/CURRENT_STATE.md, workstation/context/engineering-journal/CURRENT.md, workstation/creative-workstation/README.md, workstation/SOURCE_MATRIX.md e esse handoff se houve descoberta/implementação. Preservar histórico.
Enviar commits e PR isolada para main; não fazer merge sem autorização. Relatar paths/linhas modificados, SHAs pinados, scripts de build/preparo, comandos para iniciar, testes RED->GREEN e evidência do Electron real.
Se interromper com pendência, seguir workstation/AGENTS.md: emitir RESUME PROMPT autocontido com SHA/branch/PR e próximo erro concreto. Não inventar testes ou instalar software silenciosamente.

## CRITÉRIOS EXPLÍCITOS PARA NÃO EXPANDIR O ESCOPO
Não criar editor 3D nem layer Three.js no EffectCraft nesta tarefa. A hipótese futura Cinema4D/AfterEffects fica SOMENTE em workstation/ROADMAP.md e no CW-047 plano. Não absorver código dos editores no núcleo além do submodule e do adapter mínimo; não fazer integração Remotion antes de trabalho concreto. Aplicar D-046: baixo acoplamento pode ser arquitetura final.

## RESULTADOS DE CONCLUSÃO DA IMPLEMENTAÇÃO (2026-10-17)
- **Submodules Git**:
  - `external-engines/photocraft` (Storytold PhotoCraft @ SHA `5f65579ecb44047c2a619036c18ff273202e1389`).
  - `external-engines/effectcraft` (Storytold EffectCraft @ SHA `8f02f52a44a4b1ea807d8824b92301b96f896a06`).
- **Web Dists Oficiais Verificados**:
  - PhotoCraft v0.9.0 (`b3fa5ab6a9d32bc5ff7dfdde31939a2337471a196a2e70f1ff961a61b1bb02e6`).
  - EffectCraft v0.10.0 (`b922abeda2420391a7fd887f53ebae6948730e63720bad6a6eb3dc48dc1b46a8`).
- **Serviço e Conexão de Runtime**:
  - `workstation/creative_web_service.py` implementado com alocação dinâmica/preferencial de porta (`127.0.0.1`), nonce de readiness, adoção por `ProcessRegistry`, detecção de lease humano (`409 USER_CONTROL_ACTIVE`) e validação de loopback via `matches_managed_loopback_url`.
  - Fast-path pre-LLM em `workstation/prefabs/integration.py` (`maybe_resolve_navigation`) executando `point_action` sem Kanban tasks.
- **Testes e Qualificação**:
  - 37 testes pytest 100% green (`test_creative_web_app_spec.py`, `test_creative_web_static_server.py`, `test_creative_web_service.py`, `test_current_command_resolution.py`, `test_current_command_native_intent_contract.py`).
  - E2E real em Chromium comprovou importação de imagem, edição de canvas e salvamento no PhotoCraft; abertura de projeto demo e exportação de frame PNG 1280x720 para disco no EffectCraft; e reutilização atômica de instâncias ativas.
