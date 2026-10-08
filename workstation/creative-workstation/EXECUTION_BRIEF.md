# CW — Execution Brief (entrada compacta para coding agents)

## Correção da porta de entrada (2026-10-08)

**Primeira ação agora é R1 (perfil CI Laya), não uma segunda auditoria CW-01.** A CW-01 foi concluída como diagnóstico BLOCKED; [reparo e qualificação R1–R5](BASELINE_UNBLOCK_EXECUTION_2026-10-08.md) é o handoff autoritativo para a próxima IA. Trabalhar a partir do SHA atual (verificar), não assumir que `PR #52` foi merged. R1 edita apenas o workflow omitindo o extra `workstation-laya`, faz as provas de instalação/proveniência e a CI exata. R2 segurança npm, R3 upstream-first H-079, R4 P0 e produto permanecem separadas; CW-02 depende de todas as qualificações aplicáveis. Este parágrafo atualiza a orientação histórica “comece na CW-01” abaixo sem eliminar os registros de auditoria.

**Estado em 2026-10-08:** documentos, não runtime. **Prioridade efetiva:** `workstation/ROADMAP.md` e gates atuais; CW-P0 não substitui H-079/H-080/KI-024. **Referência desta iniciativa:** [README](README.md) → [plano](IMPLEMENTATION_PLAN.md) → [matriz de aprovação](VERIFICATION_MATRIX.md).

## Contrato em 12 linhas

1. **Objetivo:** projetos editáveis pelo humano e pelo agente; assets finais verificáveis e capacidades futuras certificadas.
2. **Superfícies P0 futuras:** Penpot web/MCP oficial, Three.js editor/bridge restrita e Remotion Studio/CLI (após licença); FFmpeg motor de render; Inkscape/Blender opcional.
3. **É uma extensão, não outro Hermes:** não duplicar SessionDB, Kanban, TaskRun, BrowserTask, Auth/Policy, ArtifactStore, Journal, Experience Compiler ou registry.
4. **Upstream-first antes de código:** ler AGENTS aplicáveis e `workstation/context/README.md`, cumprir leituras mandatórias/H-079, pinar SHA, obter baseline admissível.
5. **Bloqueios:** classificar segurança H-080A/H-080B, KI-024 e CI required; se vermelho, limitar-se a investigação/documentos, não implementar produto.
6. **Ordem física:** CW-01 preflight → CW-02 contratos mínimos → CW-03A React/SVG + preview Chromium + PNG → CW-03B FFmpeg → CW-03C Remotion **somente se licença permitir**.
7. **Depois:** CW-04 Penpot e CW-05 Three.js em PRs independentes. CW-06 Inkscape/Blender opt-in. CW-07 reuso certificado, quando já houver execução real verificada.
8. **Operações:** API/código/CLI/MCP tipados antes de mouse; browser é superfície humana; não usar JS arbitrário com privilégios.
9. **Projeto fonte:** formato nativo + assets + revisões/hashes + manifest de referências, sem conversão sem perdas presumida.
10. **Segurança:** instalação explícita, sandbox, env allowlist, rede loopback, path scope, confirmação para efeitos, no secret logs, no retry cego.
11. **Proof:** efeito externo readback + oracle adequado, testes positivos/negativos, restart, revisão concorrente, compatibilidade Windows/Electron, CI HEAD exato.
12. **Entrega:** PR pequeno, sem merge automático; documentar SHA, testes reais, recebimentos e bloqueios; nunca mudar status para VERIFIED por ter apenas escrito código.

## Primeira unidade de trabalho — AGORA R1

Não implementar “Penpot + Remotion + Three” de uma vez. A auditoria CW-01 terminou BLOCKED. Na próxima execução:
1. confirmar SHA e PRs atuais, obedecer leituras mandatórias e preflight H-079;
2. corrigir em **PR isolado** a omissão de `--extra workstation-laya` no job `contracts` de `.github/workflows/workstation-ci.yml`, sem afrouxar testes;
3. obter prova locked install + Laya import/proveniência + Workstation/contracts/regressões antes puladas + CI no HEAD exato;
4. seguir R2 audit npm em PR independente; R3 qualificação H-079 Stage A; R4 segurança voz/Electron/bootstrap; preservar documentação de blocos não liberados;
5. liberar CW-02 somente com baseline H-079 admissível e gates aplicáveis verdes; caso contrário continuar apenas investigação/reparos permitidos e reportar bloqueio.

Sequência completa: [BASELINE_UNBLOCK_EXECUTION_2026-10-08.md](BASELINE_UNBLOCK_EXECUTION_2026-10-08.md) e [IMPLEMENTER_PROMPT.md](IMPLEMENTER_PROMPT.md). Sem merge automático.

## Distinção entre documentos

| Necessidade | Leia |
| --- | --- |
| Instrução de um parágrafo para começar | [IMPLEMENTER_PROMPT.md](IMPLEMENTER_PROMPT.md) |
| Entrega atual e gate | Este briefing + [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) seção da fase |
| Conjunto de testes por fase | [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) |
| Integração de engine e licença | [INTEGRATIONS.md](INTEGRATIONS.md) |
| Estado/owner real | Código atual, arquivos `AGENTS.md`, contexto obrigatório e `CURRENT_STATE.md` |
| Debates originais | [research/](research/) somente se houver dúvida histórica, não como entrada de todas as execuções |

**Política de leitura:** este resumo não autoriza pular nenhuma leitura obrigatória de `AGENTS.md` / `workstation/context/README.md`; use índices/headings e intervalos para ler **outra** documentação por demanda, sem despejar históricos inteiros no contexto.
