# Comparação Cruzada: Browser-Memory x Lattice x Hermes Work

## 1. Visão Geral Comparativa
Comparação das três abordagens de memória procedural e representação espacial de interfaces web:
- **Browser-Memory:** Destilação de sequências de cliques em procedimentos reutilizáveis com trava de domínio (`origin-lock`).
- **Lattice:** Modelagem da página web como um grafo de UI com emissão de deltas espaciais.
- **Hermes Work:** `ExperienceCompiler` e `OperationalCapabilityRegistry` com verificação formal de pré/pós-condições.

## 2. Síntese
O Hermes Work possui o sistema de compilação mais rigoroso, mas é frequentemente restrito demais para páginas web dinâmicas. O `browser-memory` demonstra como simplificar a parametrização de rastros e o `Lattice` demonstra como compactar a representação da interface através de grafos espaciais.
