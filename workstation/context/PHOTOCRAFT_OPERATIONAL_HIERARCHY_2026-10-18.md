# PhotoCraft Operational Hierarchy (P05 — 2026-10-18)

**STATUS: DOCUMENTO OPERACIONAL VIGENTE; NOT RELEASE.**

## Problema e Motivação

O controle do Canvas do PhotoCraft provocava investigação longa e dependência desnecessária de scripts Python improvisados. Orientações antigas confundiam fechar um documento, fechar uma aba e encerrar o processo do servidor. Este documento estabelece a hierarquia canônica de operações.

## Hierarquia de Controle (ordem obrigatória)

1. **Fast path para abrir/focar o aplicativo existente.**
   - `workstation/prefabs/integration.py::prepare_user_creative_app` reconhece comandos pontuais ("Abra o PhotoCraft").
   - `workstation/creative_web_service.py::launch_creative_web_app` reutiliza instâncias ativas e saudáveis via `ProcessRegistry`.
   - Nunca reinicia o servidor se a instância já está verificada (`status="verified"`).

2. **Operações tipadas do Browser.**
   - `tools/browser_workstation.py` é a única rota para ações no Browser nativo.
   - Ações disponíveis: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_fill`, `browser_extract_items`.
   - Todas as chamadas passam por lease humano (`BrowserControlLeaseManager.assert_action_allowed`).

3. **Controles DOM acessíveis.**
   - Preferir seletores CSS estáveis e atributos ARIA sobre coordenadas.
   - `browser_extract_items` para leitura estruturada de painéis e menus.
   - `browser_click` com seletor, nunca com `(x, y)` absoluto salvo fallback justificado.

4. **Observação visual e interação sobre Canvas quando não houver semântica DOM.**
   - Canvas WebGL/Shadow DOM fechado não expõe nós ao DOM principal.
   - `browser_snapshot` para readback visual independente.
   - Interação via coordenadas normalizadas somente quando documentado como limitação conhecida (HLM-KI-10).
   - Registrar dificuldade, estratégia usada, readback e resultado como experiência de aprendizagem.

5. **Scripts auxiliares somente como fallback justificado.**
   - Proibido criar executores novos ou promover JavaScript livre como capacidade genérica.
   - Scripts existentes em `workstation/scripts/` são autorizados apenas para instalação e health check.
   - Qualquer script ad-hoc deve ser registrado como known issue com plano de remoção.

## Invariantes de Segurança

- **Owner e human lease preservados:** nenhuma ação automatizada sobrescreve edições humanas detectadas no readback.
- **Estado do documento:** fechamento de documento ≠ fechamento de aba ≠ encerramento do servidor.
  - "Fecha o documento" → ação DOM no editor (Ctrl+W ou menu File > Close).
  - "Fecha a aba" → `browser_close_tab` (se disponível) ou navegação para about:blank.
  - "Encerra o PhotoCraft" → `process_registry.terminate` com graceful shutdown.
- **Loopback only:** todas as URLs são `http://127.0.0.1:<port>` validadas por `matches_managed_loopback_url`.
- **Nonce HMAC:** verificação de prontidão via `X-Hermes-Creative-Nonce` em cada launch.

## Integração com Creative Preflight (P05)

- O módulo `workstation/creative_preflight.py` identifica tarefas de design que precisam de dimensões antes de abrir o PhotoCraft.
- Comandos pontuais ("Abra o PhotoCraft") bypassam o preflight via `_BYPASS_PATTERNS`.
- Respostas de formato são persistidas na TaskRun atual (`task_context`), não em memória permanente.
- Dimensões explícitas no pedido ("1080×1440") bypassam a pergunta.

## Limitações Conhecidas

- Shadow DOM fechado e buffers WebGL não expõem seletores DOM (HLM-KI-10).
- Observação visual é limitada a snapshots estáticos; animações contínuas requerem captura de vídeo (D-049A / HLM-KI-09).
- Coordenação entre múltiplas abas do mesmo motor não é suportada; uma instância = uma aba ativa.

## Referências

- Decisão D-046: integração por necessidade demonstrada, baixo acoplamento primeiro.
- Decisão CW-047: implementação operacional PhotoCraft/EffectCraft.
- Known Issue HLM-KI-10: isolamento de Shadow DOM e nós WebGL.
- Módulo `workstation/creative_preflight.py`: preflight mínimo de parâmetros criativos.