# Inserções prontas para a documentação canônica — 25/10/2026

**Estado:** NOT_APPLIED / OWNERSHIP_HOLD. Estes trechos atualizam diretrizes e podem ser inseridos pelo **owner efetivo**, depois de liberar os claims. Nenhum script desta etapa modifica os arquivos canônicos reivindicados. Referência: `QUALITY_GATES_IMPLEMENTATION_2026-10-25.md` + `QUALITY_REFERENCE_PATCHES_2026-10-25.md`.

## Arquivo 1 — `workstation/ROADMAP.md` (inserir no topo após título)

### Quality Closure Q1–Q7 — 25/10/2026 (PLANNED, NOT RELEASE)

O `main@f1d5ab2f` passou `npm run typecheck --workspace apps/desktop` (exit 0): os seis erros TS do diagnóstico de 23/10 não estão reproduzíveis; não refazer correções já aplicadas. Trabalhos de qualidade, em ordem: Q1 guards/autoridade Browser; Q2 medição de economia de tokens pós-projeção; Q3 Modo Aprender E2E real; Q4 Site Ops single mutating executor; Q5 fechamento M3 causal WhatsApp e só então M4–M6; Q6 EmailBatch/Gmail; Q7 startup P50/P95 e attach. Q4/Q5 permanecem HOLD enquanto claims e gates nativos estiverem abertos. Exigir RED→GREEN, Stage A/exceção escopada, owner próprio e distinção entre código presente, teste sintético, E2E e release. Fonte executável: [Plano Q1–Q7](context/QUALITY_GATES_IMPLEMENTATION_2026-10-25.md).

## Arquivo 2 — `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`

### 25/10/2026 — Inteligência operacional e qualidade

Não duplicar autoridades: `workstation_routed_browser_handler` define navegação nativa vs fallback; `_dispatch` já tem `_validate_navigation`, vínculo TaskRun, lease, observabilidade, redaction e projeção. O `GuardRegistry` experimental é async e o `binding_guard` não distingue read-only/legado; ligar indiscriminadamente ao caminho síncrono pode ser regressão. Pré-condições novas precisam de RED real e adaptação mínima aos contratos existentes. Token estimate é métrica aproximada **do payload do modelo**, não faturamento; manter payload addressable, sem PII na telemetria. Modo Aprender tem correlação `ownerTaskId → task.sessionHost → storedSessionId` presente, mas ainda exige prova nativa da pergunta e dos frames. M3 WhatsApp: GREEN sintético não supre metadados nativos/ACK, sem retry após efeito incerto. Fonte: [Plano Q1–Q7](QUALITY_GATES_IMPLEMENTATION_2026-10-25.md).

## Arquivo 3 — `workstation/context/engineering-journal/CURRENT.md`

### 25/10/2026 — Auditoria de planejamento Q1–Q7 (DOC-ONLY; NOT TARGET IMPLEMENTATION)

HEAD `main@f1d5ab2f` observado; working tree compartilhada suja, claims de M3, Site Ops e docs centrais ativos. Novo typecheck Desktop PASS exit 0, portanto seis erros TypeScript do snapshot 23/10 encerrados como não reproduzíveis no HEAD; nenhuma mudança runtime aplicada. GuardRegistry/TokenEstimate do BrowserOS presentes mas integração efetiva não comprovada; Browser nativo já tem mecanismos autoritativos, evitar duplicidade. Criados plano [QUALITY_GATES_IMPLEMENTATION_2026-10-25.md](../QUALITY_GATES_IMPLEMENTATION_2026-10-25.md) e snippets [QUALITY_REFERENCE_PATCHES_2026-10-25.md](../QUALITY_REFERENCE_PATCHES_2026-10-25.md), com Q1–Q7 e HOLD de Stage A/ownership. Execução futura sempre requer gate separado, tests RED→GREEN e qualificação nativa; sem send, merge, commit ou push nesta preparação.

## Arquivo 4 — `workstation/context/CURRENT_STATE.md` (entrada sucinta)

**Q1–Q7 25/10:** plano e patches documentais preparados. Typecheck Desktop passou. Runtime de guards/estimativa de tokens não foi considerado integrado sem prova. Aprender não ganhou E2E pela simples presença de IDs. Site Ops e WhatsApp M3–M6 continuam dependentes dos claims e evidências nativas. Nenhum status de release mudou por este plano.

## Regras para aplicação posterior

1. Revalidar `git status --short`, HEAD, `multi_agent_coordination.py status` antes de tocar nos quatro arquivos; não liberar claims de outro agente.
2. A inserção deve preservar o cabeçalho, histórico e status existentes; se o owner já inseriu informação equivalente, **reconciliar** em vez de duplicar.
3. Nunca transformar trecho NOT_APPLIED em conclusão de implementação.
4. Registrar diff e caminhos no journal, com autor e prova do merge quando ocorrer.
