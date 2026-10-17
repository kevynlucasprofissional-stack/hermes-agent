# CW-047 — Motores externos versionados + abertura sob demanda no Browser nativo

## Próximo passo executável (2026-10-17)
O [prompt implementador CW-047](CW047_IMPLEMENTER_HANDOFF_2026-10-17.md) inclui fontes oficiais, sequência por fase, arquivos/símbolos exatos, integração de aliases e URL gerenciada, requisitos de segurança, testes e registro de evidências. Já existem helpers isolados no repositório, porém **nenhuma ligação ao runtime/servidor e nenhum submodule** foi completado nesta fase.

**Data:** 2026-10-17
**Status:** PLANO SOLICITADO / documentação; importação dos repositórios, servidor localhost e comando de abertura AINDA NÃO IMPLEMENTADOS NESTA ALTERAÇÃO.
**Precedência:** D-046 (baixo acoplamento primeiro); D-043 continua hipótese condicionada; H-079 upstream-first e gates de segurança/qualificação continuam válidos.

## Objetivo operacional
Ao dizer `abra o PhotoCraft` ou `abra o EffectCraft`, o Hermes resolve uma intenção humana tipada, descobre a versão web local *previamente instalada*, inicia **sob autorização e apenas quando necessário** seu servidor loopback, verifica que está pronto e abre a URL no **Browser nativo existente**. Sem novo browser, painel, motor, runtime criativo ou subsistema de autoridade. A simples abertura não certifica edição, exportação ou aprendizagem.

## 1. Estrutura Git: múltiplos projetos de origem, não múltiplos upstreams de uma única história
- Um repositório Git pode ter diversos `remotes`, mas eles referenciam históricos potencialmente diferentes. Não mesclar os commits de PhotoCraft, EffectCraft ou Remotion no `main` do Hermes como se fossem mais um `upstream` Hermes Agent.
- **Primeira escolha para PhotoCraft e EffectCraft quando os repositórios exatos forem confirmados:** submodules Git independentes, por exemplo `external-engines/photocraft` e `external-engines/effectcraft`, com entradas explícitas em `.gitmodules`, commit pinado e opção de atualizar somente mediante revisão. Esse diretório é PROPOSTO, não existente.
- Candidatos de origem pública verificados: https://github.com/storytold/photocraft e https://github.com/storytold/effectcraft. O proprietário declarou interesse em **seus forks**: confirmar a URL exata de cada fork antes de adicioná-los como `url` de submodule. Uma pesquisa no GitHub conectado não encontrou forks com esses nomes no proprietário `kevynlucasprofissional-stack`; ausência de resultado não comprova inexistência em outra conta.
- Se usar fork: `origin` do submodule aponta para o fork do proprietário; o projeto original fica como `upstream` **dentro daquele submodule/fork**. Primeiro reconciliar upstream no fork, depois avançar o gitlink no Hermes.
- Submodule é um ponteiro para um commit, **não sincronização automática**. Atualizar por ação humana/PR isolada (`git submodule update --remote --merge` após validar branch/remote, build e licença), testar e gravar novo SHA. Proibir atualização silenciosa no bootstrap/startup e proibir forçar o HEAD para a ponta móvel.
- Ao clonar o Hermes em outro PC, inicializar os submodules com `git submodule update --init --recursive` após consentimento e requisitos locais; o clone padrão do repositório não instala runtimes, compila Rust ou inicia servidores. Revisar tamanho dos clones, LFS, submodules recursivos, consumo de disco e custos de CI antes.
- Se a futura integração exigir absorção/modificação frequente de partes do código, reavaliar `git subtree`, biblioteca versionada, pacote ou adapter; não converter automaticamente todo submodule em subtree.
- **Remotion:** preferir dependência de pacote versionada no projeto que efetivamente produza vídeo, sem clonar o monorepo como submodule por padrão; licença e distribuição são gates separados. **Three.js:** pacote versionado e, se existir demanda, editor web separado; sem importar todo o repositório só para renderização.

## 2. Levantamento do runtime já existente (base inspecionada em main)
- `workstation/prefabs/catalog.py`: resolução determinística de comandos `abre ...`; catálogo atual usa URLs **HTTPS** e `canonical_browser_url` rejeita HTTP/porta. Não reutilizar essa validação HTTPS como se aceitasse loopback: definir política EXPLÍCITA somente para instâncias locais gerenciadas.
- `workstation/prefabs/integration.py` e `workstation/prefabs/engine.py`: entrada de origem humana e navegação sob autoridade; evitar fast path para instruções não confiáveis.
- `workstation/creative_studio_service.py`: precedente de ciclo de vida do HyperFrames (ProcessRegistry, scope, aprovação, origem, porta, health/readback); reutilizar componentes **sem generalizar cegamente protocolos diferentes**.
- `apps/desktop/electron/workstation-browser-ipc.ts`, `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx`, `tools/browser_workstation.py`: Browser/aba atuais e owners existentes; não criar outro Chromium ou outra SessionDB/TaskRun.
- Prioridade funcional: abrir o app com UMA intenção sem iniciar duas instâncias; se já está pronto, apenas focar/abrir a aba, sem reload destrutivo; retornar `missing_installation`, `not_ready`, `user_control_active`, `unsupported` ou `open_requested` com status verdadeiro, não declarar sucesso prematuramente.

## 3. Factibilidade do modo web por motor — não pressupor um localhost pronto
**EffectCraft:** https://github.com/storytold/effectcraft/blob/main/docs/web.md documenta `cargo xtask web --serve 8765` (Rust/Wasm, wasm-bindgen-cli em versão compatível). Investigar se esse processo é viável no Windows do operador, se pode servir um dist previamente construído e quais pré-requisitos são necessários. Não compilar a cada abertura. A URL 127.0.0.1:8765 é **exemplo do projeto**, não porta obrigatória do Hermes.

**PhotoCraft:** https://github.com/storytold/photocraft/blob/main/packaging/web/README.md documenta site estático WebAssembly, release web compactado e imagem Docker opcional para `localhost:8080`; `apps/photocraft-web` usa Trunk. Escolher primeiro o pacote web já construído e validado, se disponível e compatível; não exigir recompilação Rust ou Docker como efeito colateral do comando `abra`. O Docker de exemplo é comunitário e seu estado deve ser verificado. O browser armazena alguns dados localmente; salvar/exportar antes de fechar pode ser obrigatório.

**Remotion:** Studio/preview no navegador, mas runtime/CLI/render Node.js podem exigir processo local; só adicionar depois de um fluxo real que o exija. Não fingir que o editor visual equivale ao renderizador completo.

## 4. Etapas sequenciais 80/20
| Etapa | Entrega mínima | Gate de saída |
|---|---|---|
| 0 — Identidade | Confirmar URL dos forks desejados, permissões, licença, política de branch e custo de disco; não alterar código | Evidência de origem e commit por motor |
| 1 — Fonte | Dois git submodules **pinados** em branch de implementação, sem instalação automática | Fresh clone com `--init --recursive`, histórico e commit independentes; procedimento de update/revert |
| 2 — Manual | Instância web PhotoCraft funcional em loopback, aberta manualmente pelo Browser atual | Abrir imagem, editar, exportar, fechar e retomar; artefato verificado |
| 3 — Comando | `abra o PhotoCraft` via roteamento já existente + lifecycle supervisionado de servidor já instalado | Comandos idempotentes, health, sessão/lease humanos, negativos de porto/origem/instalação; Windows Electron E2E |
| 4 — Reaproveitar | Repetir para EffectCraft usando perfil de lifecycle do seu servidor, sem copiar endpoint/flags de PhotoCraft | Abrir projeto, alterar composição e exportar; health e shutdown reais |
| 5 — Automação | Usar Browser atual para um fluxo de edição real e repetir, medindo tempo/erros/intervenções | Comparação com manual e necessidade de adapter discriminada |
| 6 — Expansão | Somente então avaliar Remotion, Three.js/editor e bridges internas | Trabalho recorrente + ganho líquido comprovado, sem violar D-046 |

**Prioridade de esforço:** PhotoCraft primeiro, EffectCraft depois; Remotion e Three.js não bloqueiam P0. Caso haja um trabalho profissional melhor adaptado a EffectCraft, inverter apenas as etapas 2–4, nunca implementar todos simultaneamente.

## 5. Contrato de lançamento proposto (NÃO implementado)
1. Resolver aliases humanos exatos `PhotoCraft`, `Photo Craft`, `EffectCraft`, `Effect Craft` sem interpretar URL arbitrária; não iniciar automaticamente instalações ou builds.
2. Resolver configuração local por motor: diretório instalado/artefato web validado, comando conhecido e hash/pin, diretório de projeto, porta dinâmica ou configurada, rota de health e política de autenticação/capacidades.
3. Verificar instalação/consentimento/ownership antes de criar processo; bind estritamente `127.0.0.1` ou `localhost` confiável, sem `0.0.0.0`, sem API privilegiada exposta à web externa; isolar credenciais/ambientes.
4. Se processo gerenciado já está saudável, reutilizá-lo; senão iniciar via ProcessRegistry com guarda, timeout, readiness real e limpeza/kill em falha. Não depender de PID órfão ou de portas ocupadas por outro serviço.
5. Abrir/focar URL local validada pelo Browser nativo, respeitando sessão e lease humano. Confirmar readback da navegação. A mera confirmação de abertura não declara tarefa criativa concluída.
6. Cobertura: ausência de instalação, porta indevida, processo crashando, timeout, URL redirecionada, race de dois comandos, tomada de controle humana, projeto com alterações não salvas, reinício e Windows real.

## 6. Backlog de P&D — Three.js ↔ EffectCraft, inspiração Cinema 4D/After Effects
**IDEIA FUTURA, NÃO DECISÃO DE IMPLEMENTAÇÃO:** permitir criar/editar uma cena 3D em um editor existente baseado em Three.js e compô-la/visualizá-la como fonte ou camada vinculada no EffectCraft, com atualização de preview e parâmetros de tempo/câmera, inspirado no intercâmbio entre Cinema 4D e After Effects. A solução final pode ser uma **ponte mínima de frames/texturas/arquivos GLB/scene JSON** e referências temporais em vez de embutir um editor 3D inteiro numa camada.

Antes de acoplamento: provar PoC com um asset 3D, animação temporal, alpha, espaços de cor, resolução, performance e exportação; verificar se EffectCraft oferece fonte/plugin/host de render ou contrato público suficiente. Não pressupor editor Three.js completo ou um canal de composição live existente. Só internalizar motor/código se o experimento demonstrar vantagem grande e recorrente, mantendo sincronização com origem e limites de ownership.

## 7. Métricas e antídotos à expansão
- Trabalhos concluídos (com arquivo/projeto editável), tempo até primeira entrega, tempo por repetição, intervenções humanas, falhas/retomadas e tempo gasto mantendo motor externo.
- Custos de setup e atualização: minutos por release, conflitos de merge, falhas de build, espaço em disco, Windows/Rust/Wasm/toolchain, mudança de licença.
- Nenhuma integração profunda por prestígio arquitetural. Baixo acoplamento continua sendo resultado final aceito e preferencial enquanto satisfizer o fluxo.
