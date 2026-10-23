# Hermes Deep Map — Prompt Autossuficiente

## Objetivo
Mapear recursivamente TODOS os elementos interativos do Hermes Desktop Workstation, 
clicando em cada botão/painel, registrando o que aparece, e seguindo navegações até 
cobrir 100% dos módulos e sub-telas. O resultado final é um mapa JSON completo em 
`workstation/dogfood/artifacts/hermes-complete-map.json`.

## Skills Obrigatórias
- `/hermes-work-control` — CDP navigation, batch scripts, interface map
- `/long-horizon-prompting-agent-skills-for-context-engineering` — contexto persistente entre sessões

## Comandos Disponíveis
```bash
# Inicializar mapeamento do zero
node apps/desktop/scripts/hermes-deep-map.mjs init

# Ver progresso atual
node apps/desktop/scripts/hermes-deep-map.mjs status

# Continuar do último ponto (próximo módulo pendente)
node apps/desktop/scripts/hermes-deep-map.mjs continue

# Mapear módulo específico
node apps/desktop/scripts/hermes-deep-map.mjs module <name>
# Módulos válidos: workstation, capabilities, messaging, artifacts, scheduled, vault, kanban
```

## Critérios de Aceite
1. **Cobertura:** Todos os 7 módulos listados em `pendingModules` devem estar em `completedModules`
2. **Profundidade:** Cada módulo deve ter `mainScreen` + todos `subScreens` acessíveis via nav triggers
3. **Elementos:** Cada screen mapeada deve conter lista completa de elementos interativos visíveis
4. **Navegação:** Cada `navTrigger` identificado deve ter sido clicado e seu resultado registrado
5. **Estado:** `deep-map-state.json` deve ter `pendingModules: []` ao final
6. **Mapa:** `hermes-complete-map.json` deve ser JSON válido com estrutura consistente

## Regras de Loop
- Execute `status` primeiro para saber onde está
- Se `pendingModules` não estiver vazio, execute `continue` ou `module <next>`
- Após cada módulo, execute `status` novamente para confirmar progresso
- Se um módulo falhar, registre o erro e tente o próximo; volte aos falhos depois
- NÃO repita módulos já em `completedModules`
- Quando `pendingModules` estiver vazio E todos tiverem subScreens mapeadas → COMPLETE

## Regras de Meta
- **Não mapeie sessão list:** botões de sessão mudam sempre; foque em estrutura fixa
- **Batch-first:** use sempre `hermes-deep-map.mjs`, nunca `eval.mjs` individual
- **AI Control:** verifique antes de cada run; se false, peça Ctrl+Shift+A
- **Timeout:** cada módulo pode levar 30-90s; use timeout generoso
- **Resiliência:** se CDP falhar, reconecte e continue do estado salvo

## Prompt de Continuação (copie e cole na próxima sessão)

```
Continuar o mapeamento profundo do Hermes Desktop.

1. Carregue /hermes-work-control
2. Verifique AI Control: node apps/desktop/scripts/eval.mjs "window.__hermesAiControlActive"
3. Cheque progresso: node apps/desktop/scripts/hermes-deep-map.mjs status
4. Se pendingModules não vazio: node apps/desktop/scripts/hermes-deep-map.mjs continue
5. Repita 3-4 até pendingModules estar vazio
6. Valide critérios de aceite lendo hermes-complete-map.json
7. Se completo, gere resumo executivo do mapa
8. Se incompleto, me dê novo prompt de continuação com estado atual

Arquivos de estado:
- workstation/dogfood/artifacts/deep-map-state.json
- workstation/dogfood/artifacts/hermes-complete-map.json
Script: apps/desktop/scripts/hermes-deep-map.mjs
```

## Estrutura de Saída Esperada
```json
{
  "version": "1.0",
  "generatedAt": "ISO-8601",
  "modules": {
    "<moduleName>": {
      "displayName": "...",
      "mainScreen": { "elements": [...], "structure": {...} },
      "subScreens": [
        { "trigger": {...}, "screen": { "elements": [...], "structure": {...} } }
      ],
      "navigationTargets": [...]
    }
  }
}
```