# CW — Execution Brief (entrada compacta para coding agents)

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

## Primeira unidade de trabalho

Não implementar "Penpot + Remotion + Three" de uma vez. Na primeira execução:
1. verificar se a fundação documental foi integrada ao baseline atual ou permanece no PR #50;
2. cumprir upstream-first e gates obrigatórios;
3. identificar, em código, os owners já capazes de executar/projetar uma capability criativa;
4. entregar somente **CW-01** (diagnóstico e plano de arquivos) se existir bloqueio;
5. se os gates permitirem, prosseguir até a menor entrega da **CW-02** em branch separada, com testes de contrato e prova de processo fake (sem instalar terceiros);
6. reportar status e parada. A próxima unidade é CW-03A.

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
