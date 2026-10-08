# Matriz de verificação e segurança — Hermes Creative Workstation

**Status: CRITÉRIOS PROPOSTOS / NENHUM TESTE AQUI FOI EXECUTADO.** Os nomes/owners reais dos comandos de teste devem ser confirmados no HEAD antes de rodar. Esta matriz não substitui as suítes existentes, release gates ou os controles do Workstation.

## Escala de evidência e bloqueio

- **NOT_RUN**: plano apenas; não equivale a PASS.
- **UNIT_PASS**: contrato em isolamento, sem demonstração do efeito real.
- **INTEGRATION_PASS**: provider/processo/ferramenta real num ambiente controlado, com evidência atribuída.
- **E2E_PASS**: Electron/WebContentsView, perfil, usuário, artefatos reais e regressão conforme aplicável.
- **QUALIFIED**: gates de baseline/segurança/CI exato e testes positivos/negativos completos, com owner receipts.
- **BLOCKED**: gate vermelho, ausência de licença/consentimento/autoridade, risco crítico ou impossibilidade de verificador verdadeiro.

Um caso de teste deve conter ID estável, precondição, comando/caminho real, perfil/ambiente, expectativa verificável, observação efetiva, evidência (receipt/ref/hash/log sanitizado) e decisão. **Nunca rotular mock/UI screenshot como prova de mutação no documento.**

## Matriz por fase

| Fase | Prova positiva mínima | Prova negativa obrigatória | Não avançar sem |
| --- | --- | --- | --- |
| CW-00 docs | Paths canônicos, links relativos, texto original acessível, documentação sem divergência de status | Confundir PROPOSED com IMPLEMENTED; refs quebrados; fontes externas proclamadas qualificadas | Diff apenas docs e checagem de links |
| CW-01 baseline | H-079 com SHA pinado/merge-base, owners, CI/gate, ref/licença e Source Matrix | Gate vermelho, UPSTREAM pin ausente, license NV, upstream drift não classificado | Baseline admissível, blockers e trace de auditoria |
| CW-02 capability-app | Discovery read-only, capability scoped, spawn autorizado, health real, stop, rollback e restart | Deny approval, missing dep, porta ocupada, serviço remoto indevido, cancel/crash, perfil errado, secrets no env/log | Sem processo órfão, cross-profile/fence e health receipt |
| CW-03A SVG/React | Criar projeto nativo, preview no Electron, exportar PNG que decodifica e tem dimensões/hash corretos | Input malformado, asset ausente, readback diverge, invalid path; browser bound sem fallback | Projeto reabre, outputs/provenance, E2E real |
| CW-03B FFmpeg | Render de assets controlados, ffprobe codec/duração/dimensões, checksum e readback | Falha encode, parâmetros injetados, codec não permitido, arquivo parcial, timeout, cancel/restart | Proveniência real, limpeza e sem retry de efeito incerto |
| CW-03C Remotion | License gate documentado, Studio preview/React fonte + render real verificado | Licença não elegível, falha build/render, dependência alterada, secret em props/output | Explicit legal/use case decision + E2E |
| CW-04 Penpot | MCP schema e mode validado; agente cria frame, humano altera texto, agente altera outro elemento, releitura preserva ambos | Scope/token inválido, stale revision, edit concorrente, plugin sem permissão, acesso entre perfis | Confirmação no owner, revisão protegida e teste Electron |
| CW-05 Three.js | Inspecionar cena, aplicar comando tipado, persistir/reabrir, GLB válido + viewport real | Unknown command/object, stale revision, JS injetado, edição humana concorrente, falha export, undo incorreto | Bridge version-pinned + snapshot/revision/undo e E2E |
| CW-06 motores | Inkscape/Blender processo isolado, input→output válido, versão e readback | Script não autorizado, acesso fora do workspace, asset malicioso, GPU/CLI ausente, falha de codec | Contrato de cada engine, negative regressions; sem instalação por padrão |
| CW-07 aprendizado | Accepted outcome real→candidate→validação empírica+negativos→replay→promoção→segunda resolução verificável | Auto-certificação, mudança de tool/schema/version/scope, resultado UNCERTAIN, replay mutante, evidence spoof | Verifier independente do executor e policy/registry canônicos |

## Domínios de risco: testes de falsificação

### Autoridade e consentimento (S-01)
- Descobrir skill/MCP **não** instala nem roda code-server automaticamente.
- Acesso sensível exige approval de origem correta; recusa não deixa subprocesso nem altera projeto.
- Instalação separada do uso da engine. Repositórios/sistemas de terceiros com execução arbitrária de Python/JS são opt-in e sandboxed.
- Tokens não aparecem em projetos, erros, logs, Source Matrix, telemetry, previews ou screenshots.

### Isolamento, processos, rede (S-02)
- Duas sessões e perfis A/B com projetos distintos: nenhuma leitura/mutação cruzada; key por owner e scope.
- Nunca bound BrowserTask passa silenciosamente ao Chrome do sistema; reutiliza WebContentsView autorizado.
- Bind loopback/porta efêmera/token de owner. Testar porta ocupada e serviço iniciado por perfil divergente.
- Terminando TaskRun (sucesso, falha, cancelamento, crash e restart) sem worker órfão nem nova mutação incerta.
- Limites CPU/RAM/duração/armazenamento e fechamento explícito em erro, com grace/kill supervisionado.

### Integridade de projeto e efeito (S-03)
- Path traversal, symlink, acesso absoluto fora de workspace e names inesperados são recusados; output path com write fences.
- Revision mismatch entre atualização humana e agente deve retornar CONFLICT sem sobrescrever silenciosamente.
- Renderer/LLM/CLI não pode declarar efeito `VERIFIED`; só receipt real do efeito owner + readback/contrato de verificação.
- Abrir/renderizar artefato real após export; arquivo existir/exit 0 sozinho **não** prova qualidade ou correção.
- Undo só após operação com registro e referência de revision, sem extrapolar além do suporte do editor.

### Supply-chain, licença e reprodutibilidade (S-04)
- Pin SHA/versão, license/notice e hash de pacote por engine/skill/MCP; nenhum `latest` implícito em produção.
- O Penpot AI Kit não herda automaticamente MPL do Penpot core; kit separado é CC-BY-4.0 na metadata do repositório (confirmar artefatos/fontes no ref). Remotion usa termos próprios.
- Inventariar licenças de assets, fonts, codecs, marcas e export; decisão por forma de uso e distribuição.
- Referência pode ser `FACT` no upstream e `NV` para integração local; nunca classificar `NV` como ausência.
- H-079/required CI, seam audit e drift snapshot são obrigatórios. Não rodar `npm audit fix --force` como solução automática de vulnerabilidades.

### Aprendizagem e qualidade (S-05)
- Negative replay e contrafactuais devem ocorrer em ambiente isolado, não adulterando projeto vivo do usuário.
- Capabilities sob fingerprints reais: dependency/provider/version/schema/owner/workspace/scope/output contract.
- `Cost per Verified Outcome` e LLM-call reduction são **métricas experimentais**, não autorização para enfraquecer proof nem requisito de melhoria estatística a cada run.
- Critérios subjetivos (beleza, composição, branding) podem requerer aceitação humana; render válido não prova estética.

## Portões de promoção e rollout

1. **PR por unidade** com feature flag desabilitada por padrão até proof real; dependências opcionais não são hard dependency de instalação.
2. **Qualificação base**: H-079 aprovado, pinned upstream, CI/release blockers classificados; não usar apenas testes de uma branch antiga.
3. **Owner regressions**: executar suites exatas do subsistema impactado e Desktop/Electron onde a UI foi alterada. Se check exigido falhar, sinalizar BLOCKED.
4. **Finale**: comparar build/code no HEAD exato; atualizar `UPSTREAM_DELTA.md` e seam registry se tocar seam real; snapshots de drift; documentar os resultados no journal.
5. **Sem promoção** quando faltar prova externa, segurança, licença, compatibilidade Windows ou branch review.

## Modelo de evidência por tarefa

```text
ID: CW-xx / T-yyy
Baseline: main SHA; upstream pin SHA; gate outcome
Env: Windows version; Python/Node/Electron; engine SHA; sandbox/profile
Intent/authority: op_id; run_id; confirmation decision
Inputs: source paths + hashes (sem dados sensíveis)
Operation: adapter/API/CLI/MCP action; args sem segredos
Expected: filesystem/model/scene/browser revision and media specs
Actual: owner receipt, readback, artifact path/hash, ffprobe/media data, screenshot ref
Negative controls: expected error and observed no-effect
Tests: exact command, pass/fail, CI URL
Classification: NOT_RUN | UNIT_PASS | INTEGRATION_PASS | E2E_PASS | QUALIFIED | BLOCKED
Next action and rollback: ...
```
