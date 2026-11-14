# Hermes WhatsApp — plano de execução e prompts WA-MVP-01..05
Data de preparação: 12/11/2026. **Atualização em 13/11/2026: WA-MVP-01 concluída localmente; WA-MVP-02 em andamento, TaskRun automática funcional, envio real ainda NÃO homologado; WA-MVP-03..05 pendentes.** As seções anteriores à 13 são histórico. A seção 13 é a referência operacional atual.

## 0. Decisão e escopo
Objetivo: enviar campanhas autorizadas, inclusive quatro etapas e foto/legenda, no browser nativo do Hermes, com identidade correta, evidência por efeito, retomada e espera de 60 s entre destinatários; eliminar microorquestração pela LLM. Não prometer prazo máximo absoluto nem contornar bloqueios/limites legítimos do WhatsApp. A meta normal de 40 contatos é 45–50 min, a demonstrar.

Fonte primária da auditoria: workstation/dogfood/dados/Sessões Hermes/01-WhatsApp-e-Campanhas/abrir-whatsapp-6-20261110.json. Consolidação: workstation/dogfood/dados/Relatório de sessões de IA/02_WhatsApp/relatorio-auditoria-hermes-whatsapp-20261111.md e workstation/context/WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md. Não reinvestigar as 88 sessões indiscriminadamente.

**Constatações conferidas em código (12/11):**
- tools/browser_tool.py registra whatsapp_find_contacts, whatsapp_read_messages, whatsapp_batch_preview e whatsapp_send_message. Não há ferramenta model-facing de início de campanha completa.
- tools/browser_workstation.py contém whatsapp_send_message, whatsapp_batch_send, whatsapp_batch_control, whatsapp_send_attachment, browser_file_upload e browser_wait_for_ready. O defeito inicial de persist=persist indefinido em whatsapp_batch_control foi corrigido em WA-MVP-01 (seção 8).
- workstation/integrations/hermes/whatsapp_batch_executor.py contém job/item SQLite, next_allowed_at, bloqueio de sending/uncertain, texto por item, preview e hash que só considera um texto por destinatário. O defeito inicial do preview que ignorava step_code foi corrigido em WA-MVP-01 (seção 8); o executor multietapa continua pendente.
- whatsapp_batch_approve retorna HUMAN_APPROVAL_ATTESTATION_REQUIRED intencionalmente. O emissor host de aprovação individual existe em workstation/integrations/hermes/whatsapp_human_approval.py; a autorização de manifesto de campanha ainda não existe.
- workstation/integrations/hermes/whatsapp_browser_executor.py, whatsapp_native_send_bridge.py, whatsapp_causal_receipt.py e whatsapp_native_schema_probe.py oferecem primitivas de identidade/evidência. O estado OBSERVED de DOM não é confirmação independente do servidor. Não converter OBSERVED em CONFIRMED sem prova adequada.
- whatsapp_batch_send atual usa loop síncrono com time.sleep (até 1 s por polling), portanto next_allowed_at sozinho NÃO demonstra sobrevivência a timeout de ferramenta, reinício do gateway ou perda de TaskRun. rate_limit_delay_seconds padrão = 3 s em chamadas novas/de resume; a política de 60 s precisa persistir como atributo do job.
- scripts/mark_sent.py da campanha ACIRV está desativado; 160 registros sent históricos não possuem ID estruturado. Preservar esses dados, sem reclassificação retroativa automática.
- apps/desktop/electron/workstation-browser-runtime.ts já trata stale_or_unknown_ref e NOT_DISPATCHED. Não reimplementar a solução histórica sem regressão atual.

**Verificação executada nesta preparação:** python -m pytest -q -p no:cacheprovider workstation/tests/test_whatsapp_batch_runner_runtime.py workstation/tests/test_whatsapp_batch_step_integrity.py workstation/tests/test_whatsapp_human_approval.py — **15 passed** (Windows, PYTHONDONTWRITEBYTECODE=1). Isso é teste local, NÃO prova de envio. Nenhum código operacional foi modificado.

**Integridade do workspace:** C:\Github\hermes-agent, branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e na inspeção; **563 entradas dirty/untracked**. AGENTS.md e workstation/AGENTS.md dizem que hooks/claims históricos estão aposentados: conferir escritores ativos e não supor lock. Não fazer reset/stash/checkout/commit/push/restart sem autorização. O plano é arquivo novo para não sobrescrever documentos já modificados por outros agentes. No início de cada execução revalidar HEAD, arquivos-alvo, owner e git diff; não exigir Stage A/upstream sync.

**Padrão de trabalho:** seguir Superpowers (diagnóstico específico, RED, fix mínimo, GREEN, prova real) e community-agent-workflows/ECC quando disponíveis, sem ampliar escopo. Preservar Security/BrowserTask admission, TaskRun canônica, host approval, escopo de perfil, PII, opt-out, dados e regras de toolsets. Testes em SQLite temporário. Não chamar CDP externo/9222, browser_exec, clipboard, teclado global ou script legado como fallback. Não colocar números completos ou corpo sensível em logs da LLM. Não executar envios reais sem aprovação específica na UI do Hermes.

## 1. Mapa de dependências
- **01 — Correções locais e contrato de estados**: independente de envio real; primeiro porque corrige defeito conhecido e evita falsas conclusões.
- **02 — Canário individual real WA-OPC-011**: depende de disponibilidade do Desktop e de um contato existente consentido escolhido pelo usuário; não depende do trabalho de campanha 03/04. Gate obrigatório para abrir envios da etapa 05.
- **03 — Manifesto imutável e aprovação humana host para campanha**: depende do contrato seguro de 01; implementação read-only e UI do grant podem avançar sem envio real; ativação depende da prova 02.
- **04 — Orquestração multietapa com mídia/recibos**: depende de 01 + 03; preservar estados e não publicar start desprotegido.
- **05 — Supervisor durável, medição e homologação progressiva**: depende de 02 + 03 + 04; aprovação explícita em cada expansão (2 → 5 → 40 contatos), não a aprovação deste documento.

O ponto de parada de qualquer etapa é uma falha material reproduzível ou ausência de autoridade legítima; entregar exatamente o próximo prompt de retomada, com evidência e arquivos, sem fingir conclusão.

## 2. Referências exatas
- tools/browser_workstation.py: whatsapp_batch_control (~2181), whatsapp_batch_send (~2054), whatsapp_send_message (~1847), whatsapp_send_attachment (~2362).
- tools/browser_tool.py: handlers/catalogo WhatsApp (~1766–1936); tools/whatsapp_catalog_adapter.py (source alias read-only).
- workstation/integrations/hermes/whatsapp_batch_executor.py: _has_verified_send_evidence (~69), init_batch_tables (~92), _validate_recipient_preflight (~158), compute_batch_manifest_hash (~194), whatsapp_batch_preview (~220), whatsapp_batch_approve (~343), whatsapp_batch_send (~529), whatsapp_batch_resume (~958), _record_campaign_send_mirrored (~986).
- workstation/integrations/hermes/whatsapp_browser_executor.py: whatsapp_send_message (~556) e whatsapp_send_attachment (~1193).
- workstation/integrations/hermes/whatsapp_human_approval.py: request_exact_send_approval; whatsapp_native_send_bridge.py: native_send_once.
- workstation/task_compiler.py: current_work_execution_identity e DurableBatchRunner (reuso a avaliar por contrato, sem presumir background lifetime).
- workstation/prefabs/whatsapp_campaign.py: prévia/planejamento OPC-001.
- apps/desktop/electron/workstation-browser-runtime.ts: BrowserTask/NOT_DISPATCHED; NÃO alterar por padrão.
- workstation/tests/test_whatsapp_batch_runner_runtime.py, test_whatsapp_batch_step_integrity.py, test_whatsapp_batch_executor.py, test_whatsapp_human_approval.py, test_whatsapp_causal_receipt.py e test_whatsapp_taskrun_binding.py.
- workstation/context/WA_OPC011_HERMES_REAL_TEST_20261112.md: roteiro de canário real já preparado.
- workstation/context/README.md, DEVELOPMENT_GATES.md, engineering-journal/CURRENT.md: documentação canônica; todos já modificados no checkout durante esta preparação, não sobrescrever sem coordenação.

## 3. Patch cirúrgico preparado e aplicado em WA-MVP-01
Correção mínima, **APLICADA** (ver seção 8): em tools/browser_workstation.py, no ramo action == "resume" da função whatsapp_batch_control:
~~~diff
@@
         return whatsapp_batch_resume(
             job_id=job_id,
             browser_navigate=_nav,
             browser_snapshot=_snap,
             browser_click=_click,
             task_id=task_id,
             session_id=session_id,
             db_path=db_path,
-            persist=persist,
         )
~~~
A assinatura atual de whatsapp_batch_resume não aceita persist. Logo é seguro remover o argumento, mas confirmar novamente assinatura/diff antes de aplicar.

Teste RED pronto para acrescentar a workstation/tests/test_whatsapp_batch_runner_runtime.py (sem disparos):
~~~python
def test_workstation_batch_resume_does_not_pass_undefined_persist(monkeypatch):
    from tools import browser_workstation
    from workstation.integrations.hermes import whatsapp_batch_executor as batch

    observed = []

    def fake_resume(*, job_id, browser_navigate, browser_snapshot,
                    browser_click, task_id, session_id, db_path):
        observed.append((job_id, task_id, session_id, db_path))
        return {"status": "PAUSED", "job_id": job_id}

    monkeypatch.setattr(batch, "whatsapp_batch_resume", fake_resume)
    result = browser_workstation.whatsapp_batch_control(
        job_id="synthetic-job", action="resume",
        task_id="task", session_id="session", db_path="synthetic.sqlite",
    )
    assert result == {"status": "PAUSED", "job_id": "synthetic-job"}
    assert observed == [("synthetic-job", "task", "session", "synthetic.sqlite")]
~~~
A execução antes do patch deve reproduzir NameError; depois, GREEN. Não é necessário inicializar WhatsApp ou tocar em banco real.

## 4. Sequência de prompts prontos para o implementador

### PROMPT 01 — WA-MVP-01 | corrigir retomada e estado por etapa (sem envios)

~~~text
MISSÃO WA-MVP-01 — Corrigir wrapper de retomada e preservar elegibilidade por etapa

Trabalhe em C:\Github\hermes-agent, branch canônica main; baseline observado no planejamento HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, mas confirme o HEAD atual. O checkout compartilhado tinha 563 entradas dirty/untracked. NÃO resetar, stash, trocar branch, commit, push, reiniciar ou sobrescrever trabalho de outros agentes. Verificar owner e diff real dos arquivos antes de editar. Stage A/upstream sync não é pré-requisito; seguir AGENTS.md, workstation/AGENTS.md, tools/AGENTS.md e workstation/context/DEVELOPMENT_GATES.md. Superpowers e community-agent-workflows quando disponíveis, aplicados proporcionalmente.

OBJETIVO: corrigir falha reproduzível do resume e prevenir que a prévia de campanha ignore passos ainda pendentes. Não executar envios reais.

INSPEÇÃO JÁ FEITA: tools/browser_workstation.py::whatsapp_batch_control passa persist=persist indefinido ao whatsapp_batch_resume, cuja assinatura não aceita esse argumento. workstation/integrations/hermes/whatsapp_batch_executor.py::whatsapp_batch_preview atualmente reúne already_sent_contacts sem considerar step_code. Isso é perigoso para quatro etapas; não converter históricos livres em comprovantes válidos. O batch contém next_allowed_at e proteção contra sending/uncertain; preservar.

IMPLEMENTAR:
1. Abrir apenas arquivos relevantes e o git diff dos mesmos. Se o problema ainda existir, aplicar a remoção cirúrgica de persist=persist conforme seção 3 de workstation/context/WHATSAPP_EXECUTION_PLAN_20261112.md. Adicionar teste RED para o ramo resume (teste completo já preparado na seção 3), depois GREEN; não chamar browser real.
2. Ajustar preview/seleção de elegibilidade para chave (campaign_id, contact_id, step_code), quando uma etapa estiver especificada. Para a futura execução multietapa, não tomar "qualquer etapa enviada" como exclusão do contato inteiro. Nunca reinterpretar prova legada textual como confirmação independente; preservá-la e sinalizar legacy_unverified em relatório. Se o escopo atual do preview não permite multietapa, corrigir pelo menos o caso step_code e documentar o restante como requisito do prompt 04.
3. Criar testes com SQLite temporário: contato com wa_01 sent e wa_02 pending → wa_02 elegível; wa_01 não reenviada; wa_02 uncertain bloqueada; contato opt-out excluído; sem vazamento de telefone em resposta model-facing. Preservar nomes públicos de tools, migrações forward-only e tabelas existentes.
4. Corrigir apenas defeitos verificados. Não habilitar início de lote. Nenhuma chamada model-facing pode fornecer db_path/telefone nem contornar autorização.

VERIFICAÇÃO: python -m pytest -q -p no:cacheprovider workstation/tests/test_whatsapp_batch_runner_runtime.py workstation/tests/test_whatsapp_batch_step_integrity.py workstation/tests/test_whatsapp_batch_executor.py; também testes novos. Executar sem bytecode/cache quando possível. Validar diff sintático e status. Se testes existentes dependem intencionalmente de contrato legado, analisar a divergência em vez de relaxar os controles.

ACEITE: resume não levanta NameError; elegibilidade correta por etapa; uncertainty não causa reenvio; nenhum dado real alterado; regressões focadas GREEN. Registre arquivos, testes exatos, decisões, pendências em contexto/jornal existentes somente após verificar writers. Relate implementação versus verificação real. Se bloqueado, entregue UM prompt de retomada com o próximo defeito concreto.
~~~

### PROMPT 02 — WA-MVP-02 | HISTÓRICO OBSOLETO — NÃO EXECUTAR (usar seção 13)

~~~text
MISSÃO WA-MVP-02 — Homologar WhatsApp individual no Hermes real (WA-OPC-011)

Repositório C:\Github\hermes-agent; manter main e todos os dirty files. Não reset/stash/checkout/commit/push/restart sem autorização. Contexto canônico: workstation/context/WA_OPC011_HERMES_REAL_TEST_20261112.md e WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md. Consulte também AGENTS.md e regras de BrowserTask. Não investigar histórico amplo novamente.

OBJETIVO: provar o caminho Desktop real da tool whatsapp_send_message, com whatsapp_find_contacts, TaskRun própria, identidade completa no navegador nativo, autorização humana gateway ONCE, efeito e log estruturado. Há implementação de aprovação individual em whatsapp_human_approval.py, sender em tools/browser_workstation.py e bridge/receipt em workstation/integrations/hermes/whatsapp_native_send_bridge.py e whatsapp_causal_receipt.py. Os 218 testes historicamente reportados não substituem E2E. O estado OBSERVED da bolha não equivale a confirmação independente do servidor.

PRÉ-REQUISITO MATERIAL: o usuário deve escolher um contato existente, consentido e inequívoco, e APROVAR EXPLICITAMENTE um único envio no cartão host. Este texto NÃO constitui autorização de envio. Se não houver contato, AI Control/TaskRun, source alias acirv_contacts ou cartão autenticado, parar em HOLD e relatar exatamente o requisito faltante; não substituir por número fictício nem fazer envio alternativo.

EXECUÇÃO:
1. Inspecionar status atual, schema Desktop de whatsapp_find_contacts/whatsapp_send_message, skill whatsapp-native-operator e BrowserTask autenticada da própria TaskRun. Não usar CDP externo, porta 9222, clipboard, Browser Exec externo ou mouse/teclado global.
2. Reproduzir o roteiro de workstation/context/WA_OPC011_HERMES_REAL_TEST_20261112.md com nome/teste definido pelo usuário e mensagem literal daquele arquivo, ou outra aprovada especificamente na UI. Confirmar autoria do auto-chat na mesma BrowserTask, resolver referência privada e verificar destino completo.
3. Exibir ao usuário o destinatário e texto integrais no cartão nativo de aprovação; somente choice once vale. Máximo um clique em enviar, sem novos operation_id para tentar novamente. Relacionar antes/depois, ID novo, corpo, autor, destino e ACK da mesma bolha, persistindo operation_id, TaskRun, hash do texto e approval_fingerprint sem revelar PII.
4. Se o runtime falhar, diagnosticar o defeito específico, corrigir com RED/GREEN e repetir APENAS após nova autorização humana e reconciliação de qualquer efeito incerto. Não inferir que falha de timeout significa mensagem não enviada.

VALIDAÇÃO: testes locais de test_whatsapp_human_approval.py, test_whatsapp_taskrun_binding.py, test_whatsapp_causal_receipt.py, test_whatsapp_browser_executor.py e, indispensavelmente, um fluxo real autorizado. Diferenciar OBSERVED/UNCERTAIN/REVIEW_REQUIRED/FAILED; não declarar CONFIRMED sem evidência independente válida.

ACEITE: uma operação aprovada via host, destino correto, nenhum clique duplicado, recibo causal íntegro, log consistente e relato do grau de prova. Se teste não autorizado, registrar HOLD e entregar prompt de retomada; não liberar campanhas nem contar como E2E aprovado. Registrar execução factual em jornal/contrato existente.
~~~

### PROMPT 03 — WA-MVP-03 | manifesto completo e aprovação host do lote

~~~text
MISSÃO WA-MVP-03 — Aprovação humana vinculada a manifesto imutável de campanha

Continue em C:\Github\hermes-agent/main, preservando o checkout dirty compartilhado e trabalho paralelo. Leia AGENTS.md, workstation/AGENTS.md, tools/AGENTS.md e workstation/context/WHATSAPP_EXECUTION_PLAN_20261112.md. Revalidar arquivos e owners antes de alterações. Não fazer reset/stash/commit/push/restart; Stage A opcional. NÃO executar campanha real nesta etapa.

OBJETIVO: tornar possível ao host humano aprovar UM manifesto exato de campanha (não 160 cliques), sem permitir ao modelo mintar tokens, fornecer números completos, alterar destinatários ou burlar as admissões do BrowserTask.

ESTADO COMPROVADO: whatsapp_batch_approve() em workstation/integrations/hermes/whatsapp_batch_executor.py retorna HUMAN_APPROVAL_ATTESTATION_REQUIRED. O emissor humano individual request_exact_send_approval em whatsapp_human_approval.py autentica uma operação once e exige TaskRun ativa. compute_batch_manifest_hash hoje inclui um texto por destinatário; NÃO inclui quatro etapas/mídia e não serve como assinatura definitiva do novo lote. whatsapp_batch_preview é read-only e não autoriza envio. Model-facing tool whatsapp_batch_preview já existe em tools/browser_tool.py e whatsapp_catalog_adapter.py.

IMPLEMENTAÇÃO:
1. Reutilizar a fila de aprovação autenticada do gateway/host e o contexto current_work_execution_identity; criar operação estritamente host-owned de aprovação once para manifesto versionado. Vínculo mínimo: profile/source alias confiável, campanha, lista exata de recipient_ref resolvidos privadamente (e respectivas identidades), ordem e step_code de TODOS os blocos, corpo final renderizado por contato, hash SHA-256 de cada mídia + tipo/legenda, intervalo aprovado >=60 s quando solicitado, TaskRun e run_id, expiração/revogação e nonce/operation_id. Serialização canônica estável com hash reproduzível. Capturar aprovação depois de exibir os detalhes íntegros no host, não apenas resumo; a LLM recebe somente contagens e hash opaco.
2. Qualquer mudança em destinatário, etapa, mídia, corpo, sequência, intervalo ou estado de opt-out invalida a parte afetada antes do efeito; comportamento mais restritivo (HOLD geral) é aceito no MVP. Proibir bypass via require_approval=False, aprovação default, CLI interno ou approval_token controlado pelo modelo. O registro de autorização deve ser imutável e atestado pelo host; não reutilizar livremente approved_by.
3. Interface model-facing mínima: preview/solicitar-aprovação/status usando alias + campaign_slug/versão. Nunca aceitar db_path, números, recipients array, approval_token, ou message_body arbitrários. Início de envio permanece indisponível até WA-MVP-04/05 com gates efetivos.
4. Integrar com tables/schemas existentes via migrações forward-only, evitando DB paralelo e reparo retroativo de históricos. Opt-out, autorização do usuário e disponibilidade de BrowserTask devem falhar fechado.

TESTES: RED/GREEN para aprovação once real versus sessão/always/denial/timeout, hash divergente, alteração de mídia/legenda, rota/owner/run incorreto, token de modelo, TOCTOU entre preview e envio, dupla utilização, expiração e perda da UI. Testes temporários; validar que nenhum caso negativo aciona browser_click. Rodar suites atuais de aprovação e batch.

ACEITE: uma aprovação host validamente vinculada a todos os elementos da campanha e nenhuma forma de iniciar envio com manifesto não aprovado; zero envio real nesta etapa. Documentar contrato, migrations, resultados e limites nos arquivos canônicos após coordenação. Relatar alterações, testes, pendências. Se houver opção tecnicamente superior no host já existente, adotá-la com justificativa e mesma segurança.
~~~

### PROMPT 04 — WA-MVP-04 | executor de quatro etapas e foto/legenda

~~~text
MISSÃO WA-MVP-04 — Concluir executor WhatsApp multietapa com mídia sobre BrowserTask existente

Projeto C:\Github\hermes-agent/main. Preservar todo WIP (baseline histórico f1d5ab2f03 não é ordem de rollback). Arquivos de referência: workstation/context/WHATSAPP_EXECUTION_PLAN_20261112.md, WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md, WA_OPC011_HERMES_REAL_TEST_20261112.md. Ler AGENTS e gates do Workstation. Superpowers RED/GREEN e community-agent-workflows onde disponíveis. Sem envio a terceiros nesta etapa sem nova aprovação humana explícita.

OBJETIVO: tornar uma campanha nativa em sequência determinística por destinatário: resolver recipient_ref, verificar número completo da conversa, enviar wa_01/wa_02/wa_03/wa_04 conforme manifesto, incluir foto e legenda no passo que a prevê, capturar evidência individual de cada efeito, gravar checkpoints e parar em incerteza. O modelo não chama browser_console por mensagem e não opera o relógio.

ESTADO: workstation/integrations/hermes/whatsapp_batch_executor.py possui job SQLite/next_allowed_at/status mas uma mensagem de texto por item; whatsapp_browser_executor.py oferece texto e whatsapp_send_attachment separado; whatsapp_native_send_bridge.py e whatsapp_causal_receipt.py implementam parte das verificações; tools/browser_workstation.py expõe adaptadores nativos. A prova real do passo individual vem da missão 02. Não usar a antiga função de batch diretamente como caminho model-facing para burlar consentimento/aprovação.

IMPLEMENTAÇÃO:
1. Adaptar o executor existente (não escrever outro browser ou banco) para identidade durável de operação (job_id, campaign_id, enrollment/contact_id, step_code, template_version, operation_id) e prova por step. Escolher mínima migração forward-only de itens/etapas: nenhuma confirmação genérica do contato antes de todas as etapas exigidas; ao retomar, consultar apenas etapas incompletas. Aprovação do manifesto da missão 03 é pré-condição obrigatória para cada fronteira de efeito.
2. Em cada conversa aberta via navegação nativa, esperar readiness por condição (sem sleep LLM), comparar identidade completa de destinatário da fonte segura com o painel/compositor, revalidar antes de cada send. Referências DOM devem ser obtidas logo antes da ação; stale ref ou página em transição não autorizam clique em elemento antigo. Não depender do nome exibido, últimos quatro dígitos nem DOM virtualizado como identificador imutável.
3. Para mídia usar somente browser_file_upload com grant nativo task/run/origin; conferir preview de FOTO (não sticker), MIME/extensão/caminho autorizado, hash e legenda do manifesto, só então executar UM clique. Nova bolha/ID, autor próprio, destino e conteúdo/tipo vinculados ao mesmo operation_id. Seleção/preview/clique isolados não certificam envio. Validar texto e imagem separadamente por etapa.
4. Persistir estado semanticamente honesto: prepared/sending/observed/confirmed/uncertain/failed/skipped compatibilizados com schema existente. OBSERVED = recibo causal de UI, nunca afirmar independent server CONFIRMED se não houver tal prova. Em dúvida, bloqueio por contato ou campanha antes de nova ação externa; nunca reenvio cego. Não importar evidência livre do legado nem revogar os 160 sent históricos.
5. Expor uma interface mínima de início/estado/pausa SOMENTE depois de verificar aprovação e lineage no host; a LLM passa referências opacas. Se autorizações ou recibos não são suficientes, retornar HOLD concreto, sem criar bypass.
6. Reutilizar Prefab/TaskCompiler quando preservar BrowserTask ownership, sem nova arquitetura multiagente nem JavaScript longo na página atravessando navegação.

TESTES: em fixtures temporárias reais do contrato nativo, verificar destino correto, destinatário trocado durante navegação, dois contatos com mesmo nome, template editado após aprovação, foto versus sticker, falha de upload, incerteza após clique, ACK de mensagem anterior, etapa duplicada, opt-out, job interrompido entre dois passos e retomada que NÃO repete o primeiro. Executar suites focadas existentes e novas. Quando houver autorização, canário controlado com NO MÁXIMO dois destinatários para verificar mídia/etapas; sem autorização, só teste sintético e status HOLD.

ACEITE: quatro etapas/mídia versionadas por contato no executor, nenhuma decisão LLM por microação, nenhuma possibilidade de enviar para destino/manifesto divergente, recebimentos persistidos e nenhum envio duplicado sob falha. Não declarar '40/40' sem nível de evidência coerente. Registrar arquivos, testes, desvios, riscos e bloqueios.
~~~

### PROMPT 05 — WA-MVP-05 | supervisor durável e homologação progressiva 2→5→40

~~~text
MISSÃO WA-MVP-05 — Comprovar continuidade, 60 segundos e throughput real do Hermes WhatsApp

C:\Github\hermes-agent/main. Revalidar o estado atual, preservar todos os dirty files e contratos TaskRun/BrowserTask/host approval. Base técnica: workstation/context/WHATSAPP_EXECUTION_PLAN_20261112.md e resultados objetivos das missões 01–04. Não refazer investigação histórica; não dar Stage A como gate. Sem reset/stash/commit/push/restart automático.

OBJETIVO: uma campanha de 40 contatos e quatro etapas com foto não pode depender de uma chamada LLM por passo ou de uma ferramenta síncrona cujo timeout encerra o worker. Aguardar >=60 segundos DEPOIS de terminar o último passo de A e ANTES de começar a primeira ação de envio de B, com 39 intervalos em 40 contatos; incluir preparo/identidade no tempo medido e não antecipar o envio. Entrega normal desejada ~45–50 min, somente se comportamento real permitir.

PONTO CRÍTICO: whatsapp_batch_executor.py::whatsapp_batch_send hoje é um loop síncrono com time.sleep; next_allowed_at é persistido, mas isso não prova que a execução longa sobreviva ao gateway, ao timeout de ferramenta ou à troca de TaskRun. rate_limit_delay_seconds tem default 3 s no novo job e no resume; não confiar no parâmetro não persistido para preservar o contrato de 60 s. Há DurableBatchRunner em workstation/task_compiler.py; primeiro verificar suas garantias de ownership/lifetime e reaproveitar somente se suportar os efeitos externos com lineage. Caso contrário, implementar o menor supervisor durável host-owned usando as filas e o SQLite existentes, sem daemon/CDP externo.

IMPLEMENTAÇÃO:
1. Persistir no job o intervalo aprovado e a âncora de conclusão do destinatário; o resume lê a política GRAVADA no job, nunca default=3 ou input do modelo. Não iniciar B antes do prazo; permitir atraso mas nunca reduzir pausa. Timer sem LLM, monitorável por status.
2. Fazer execução em unidades duráveis suficientemente curtas para não expirar o owner, com TaskRun/capability e BrowserTask estáveis. Pausa/cancelamento humanos têm efeito sem perder trilha; reinício do processo exige reconciliação de sending/uncertain antes de qualquer avanço. Uma operação pós-click com resultado desconhecido não pode ser repetida, mesmo se cronômetro venceu. Falha de rede/limite legítimo da plataforma retorna backoff ou HOLD, não contorno.
3. Telemetria enxuta por recipient/step: timestamps de preparação, preview, primeiro e último clique, recibo, cooldown, espera de browser, retries seguros apenas pré-dispatch, tempo de intervenção humana e código de causa (MODEL_RATE_LIMIT, MODEL_CONTEXT_COMPACTION, BROWSER_TIMEOUT, WHATSAPP_THROTTLE, AUTHORITY_HOLD, USER_PAUSE, NETWORK_ERROR). Não usar tokens_estimated sintéticos como faturamento. Retornar status compacto, sem PII.
4. Provar offline com relógio controlado: 60 s persistentes entre A/B, restart antes/depois do prazo, pausa/cancelamento, dois processos concorrentes, lease/taskrun revogado, reentrada em sending/uncertain, cold restart, dom stale e mudança de manifesto.
5. Homologação real progressiva e AUTORIZADA: primeiro 2 contatos consentidos com 60 s, depois 5. Só se ambos concluírem com prova de destinatário/steps/mídia, ausência de duplicação, nenhum bypass e medidas concretas, propor lote de 40 à aprovação explícita do usuário no host. O próprio prompt nunca autoriza 40 disparos. Não adivinhar contatos, não ignorar opt-outs e não tentar vencer rate limits.
6. Medir tempo por destinatário, 39 intervalos, taxa de HOLD, llm_turns_per_recipient, chamadas de ferramentas, duração total, evidência por etapa. O caminho feliz deve ter zero turnos LLM por destinatário; a LLM só configura e lida com exceções. Registrar limite de plataforma como restrição legítima se ocorrer.

VERIFICAÇÃO: executar suites Python focadas e regressões de BrowserTask/admission afetadas, testes reais de 2 e 5 somente com autorização; capturar recibos/resultados agregados. Para 40 contatos: cenário normal T = 39 min + soma dos tempos dos 40 contatos + preparo/recovery. 40×15 s produz ~49 min antes do preparo. Não prometer SLA absoluto e não sacrificar correção para cumprir prazo.

ACEITE: demonstração do worker durável e recuperação sem efeitos duplicados; intervalo >=60s provado entre destinatários; identidade e recibos por etapa coerentes; comparativo operacional antes/depois com fontes reais; sem microorquestração LLM no caminho feliz. Se homologação de 40 não foi autorizada, declarar explicitamente 'implementado/testado até 2/5, lote 40 não executado', não 'concluído'. Registrar resultados e um prompt de retomada objetivo se faltar qualquer gate.
~~~

## 5. Critérios de avanço e reversão
- 01 → 02: teste de wrapper GREEN e política por step demonstrada em SQLite temporário.
- 02 → 03/04 ativação: um envio individual a contato de teste consentido, com cartão host once, identidade exata e recibo causal (não inflar OBSERVED). Se não houver autorização, 03 pode ser desenvolvido sem habilitar envio; 04 permanece sem disparos.
- 03 → 04: hash do manifesto completo com mídia; alteração de qualquer elemento invalida grant; negativas não fazem browser_click.
- 04 → 05: executor multietapa e preview de foto demonstrados, bloqueio em uncertain e retomada sem duplicar.
- 05: provas 2 e 5; expansão a 40 só com autorização nova. Meta 45–50 min não demonstrada até lote real.
- Reversão sem dados perdidos: recurso de início de lote continua DISABLED/HOLD até qualificação; migrações aditivas/forward-only, backup transacional do SQLite de controle antes de migração; em regressão, desabilitar execução nova e preservar receipts/uncertain (nunca resetar histórico). Scripts legados permanecem desativados.

## 6. Registro a exigir após cada missão
Atualizar documentos canônicos pertinentes APÓS checar writers atuais: workstation/context/WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md e engineering-journal/CURRENT.md; se necessário README/KNOWN_ISSUES. Informar HEAD e dirty state, arquivos realmente alterados, comportamento implementado, testes RED/GREEN, prova em runtime versus mocks, envio real versus HOLD, regressões, riscos e a única próxima ação. Não confundir documento, build, teste sintético e execução funcional.

**Preparação desta etapa:** relatório/plano gerado, patch e teste propostos; nenhuma ferramenta de envio executada; nenhum código de produção aplicado; não há autorização nova de disparos.

## 7. Verificação complementar após preparar o plano (12/11)
- **Reprodução isolada e sem envio**: chamada a tools.browser_workstation.whatsapp_batch_control(action="resume") com whatsapp_batch_resume substituída por stub gerou exatamente NameError: name 'persist' is not defined. O patch da seção 3 NÃO foi aplicado; o teste proposto é RED.
- **Reprodução isolada com SQLite sintético**: histórico wa_01=sent e pedido de preview para wa_02 resultou eligible_count=0, excluded_count=1, ALREADY_SENT=1. Essa é uma evidência direta de que o preview atual exclui etapa diferente indevidamente; nenhuma base ACIRV foi alterada.
- O teste sintético encontrou lock transitório no arquivo SQLite temporário durante remoção no Windows. O diretório de teste foi removido após o término do processo. Isso **não** prova vazamento persistente no produto; investigar fechamento de conexões apenas se reaparecer nos testes da missão 01.
- Revalidação documental: 5 prompts completos, 7 blocos de código delimitados, caminho e HEAD conferidos. Não houve execução de WhatsApp, migração de dados nem teste E2E nesta preparação.

## 8. Execução efetiva WA-MVP-01 — 12/11/2026

**Status:** IMPLEMENTADA E VERIFICADA LOCALMENTE. NÃO É HOMOLOGAÇÃO DE ENVIO REAL. As missões WA-MVP-02..05 permanecem pendentes.

**Arquivos efetivamente modificados:**
- tools/browser_workstation.py: remoção única de `persist=persist` no ramo `whatsapp_batch_control(action="resume")`. Não mexeu nos outros usos legítimos de `persist`.
- workstation/integrations/hermes/whatsapp_batch_executor.py: preview considera `campaign_id + contact_id + step_code` quando `step_code` fornecido; registros sem etapa (`NULL`, vazia ou coluna ausente) produzem `LEGACY_STEP_UNKNOWN`; falha de consulta histórica produz `HISTORY_UNAVAILABLE`; `uncertain/sending` tem precedência sobre `sent`; linhas `sent` sem recibo causal estruturado ficam excluídas do reenvio mas são contabilizadas em `legacy_unverified_count`. Sem `step_code`, mantém interpretação ampla de legado. Nenhuma migração de schema.
- workstation/tests/test_whatsapp_batch_preview_steps.py: 9 novos testes para wrapper, duas etapas, reenvio, incerteza, opt-out, privacidade, histórico sem coluna, `NULL`/vazio e falha de consulta.

**Evidência RED antes da correção:** os 6 testes originais produziram 5 falhas e 1 sucesso; o caso `step_code = ''` foi adicionado depois e reproduziu 1 falha antes da correção cirúrgica. O wrapper reproduziu exatamente `NameError: name 'persist' is not defined`; a prévia de `wa_02` retornava `ALREADY_SENT` por causa de `wa_01`.

**Evidência GREEN após correção:** `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` nos arquivos `workstation/tests/test_whatsapp_batch_preview_steps.py`, `test_whatsapp_batch_runner_runtime.py`, `test_whatsapp_batch_step_integrity.py`, `test_whatsapp_batch_executor.py`, `test_whatsapp_operational_readonly.py`, `test_whatsapp_recipient_resolution.py`, `test_whatsapp_human_approval.py` e `test_whatsapp_taskrun_binding.py` => **83 passed em 14,40 s**, exit 0. `ruff check --ignore UP012` nos 3 arquivos afetados => **All checks passed**, exit 0. Sem `--ignore`, Ruff informa somente uma regra `UP012` histórica na linha aproximada 860 do executor, não relacionada a esta missão; não foi corrigida fora do escopo. `git diff --check -- tools/browser_workstation.py` => exit 0. Sintaxe Python validada.

**Limites e preservação:** nenhum envio real; nenhum navegador WhatsApp acionado; nenhum dado ACIRV de produção alterado; SQLite somente temporário nos testes. Sem commit, push, reset, stash, checkout, restart ou alteração de autoridade. Branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e` na verificação. Os arquivos-fonte envolvidos já eram dirty/untracked antes da missão, preservados em edição cirúrgica. O journal comum `workstation/context/engineering-journal/CURRENT.md` estava dirty no checkout e havia processos de outros agentes; não foi regravado para evitar colisão. Este registro foi acrescentado ao documento de contexto preparado por esta mesma missão.

**Próximo gate:** WA-MVP-02, canário individual real do WhatsApp, depende de contato consentido e aprovação humana autenticada na interface. WA-MVP-03/04 permanecem sem grant de campanha, a execução do batch não foi habilitada. Histórico `legacy_unverified` não implica entrega comprovada nem autoriza reenvio automático.

## 9. Execução WA-MVP-02 — verificação local e bloqueio de homologação (12/11/2026)

**Estado: HOLD — destinatário de teste não resolvido; E2E real não executado.** O usuário autorizou nesta conversa usar o seu auto-chat WhatsApp, telefone terminado em **0988**, exclusivamente para o teste individual. Essa autorização de intenção não substitui a aprovação humana autenticada `once` na interface do Hermes nem muda os contratos do produto.

- Repositório `C:\Github\hermes-agent`, `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 567 entradas dirty/untracked na verificação. Não houve reset, stash, checkout, commit, push ou restart.
- Hermes Desktop Electron e backend `hermes serve` observados entre os processos; `whatsapp-native-operator` v0.1.0 localizado em `%LOCALAPPDATA%\hermes\skills\whatsapp-native-operator\SKILL.md`. Schemas de `whatsapp_find_contacts` e `whatsapp_send_message` presentes no código `tools/browser_tool.py`; **isso não comprova a exposição dessas tools em uma TaskRun do Hermes real**.
- Fonte autorizada `acirv_contacts` presente no perfil e SQLite acessível. Inspeção **somente leitura**, com URI `mode=ro` e `PRAGMA query_only=ON`, pesquisou o sufixo completo do telefone informado nas colunas `phone_raw`, `phone_number`, `whatsapp_id`, além de `display_name` relacionado a auto-chat. Resultado: **0 registros candidatos**. Não foi possível produzir `recipient_ref` confiável; enviar por número bruto violaria o contrato da tool.
- Controle em `%LOCALAPPDATA%\hermes\whatsapp_send_control.sqlite`, consulta estritamente read-only: tabela `whatsapp_send_logs`, **0 registros**. Nenhum envio ou grant realizado.
- Regressão executada em Windows, `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` nos arquivos `workstation/tests/test_whatsapp_human_approval.py`, `test_whatsapp_taskrun_binding.py`, `test_whatsapp_causal_receipt.py`, `test_whatsapp_browser_executor.py`: **71 passed em 11,05 s**, exit 0. Não houve teste nativo E2E.
- **Não verificados**: TaskRun específica do Hermes para esse teste, BrowserTask autenticada com auto-chat aberto, cartão de aprovação nativo, escolha humana `once`, clique de envio, bolha nova, ACK e recibo causal real. Não declarar `OBSERVED` nem `CONFIRMED`.

**Desbloqueio mínimo:** fornecer/selecionar um contato existente e consentido que conste da fonte `acirv_contacts` com identidade inequívoca **ou**, em missão separada e com autorização explícita, disponibilizar o auto-chat na fonte confiável sem violar proveniência/permissões; **não criar contato artificial nem alterar base por este plano**. Confirmar ainda que o número de teste está correto. Depois, executar o roteiro original `workstation/context/WA_OPC011_HERMES_REAL_TEST_20261112.md` **dentro de uma nova TaskRun do Hermes**, obtendo aprovação `once` no host antes de qualquer clique. Um erro de resultado incerto exige conciliação, nunca retry cego.

Nenhum código do Hermes, banco real, skill, permissão ou dado de contatos foi alterado nesta fase. O jornal de engenharia compartilhado permaneceu intocado por estar dirty e potencialmente em uso. Campanhas continuam HOLD.

## 10. WA-MVP-02 — tentativa de retomada com contato "Kevyn ACIRV" (12/11/2026)

**Resultado: HOLD antes do envio; causa confirmada = lacuna de descoberta/resolução do próprio Hermes.** O usuário autorizou especificamente o destinatário nomeado `Kevyn ACIRV` e reiterou que o número fornecido anteriormente deveria poder ser aproveitado. A autorização no chat não substitui o cartão host `once`. Não foi feita chamada à ferramenta mutadora ou ao WhatsApp.

**Verificações atuais, sem alteração de dados:**
- `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 567 entradas dirty/untracked; nenhum reset/stash/checkout/commit/push/restart.
- `_configured_sources()` retorna um único alias: `acirv_contacts`. A fonte está legível; consulta direta SQLite exclusivamente `mode=ro` + `PRAGMA query_only=ON`.
- Pesquisa por nome contendo `Kevyn`: **1 registro**, com outro nome de exibição e `recipient_ref` tecnicamente válido; porém seu telefone **não coincide** com o número anteriormente autorizado (terminação 0988) e seu rótulo **não** é `Kevyn ACIRV`. Pesquisa exata por `Kevyn ACIRV`: **0 registros**. Não tratar o registro distinto como destinatário autorizado.
- Já na tentativa anterior, pesquisa read-only do telefone autorizado na fonte: **0 candidatos**. Logo tanto nome quanto telefone não fornecem `recipient_ref` correspondente na fonte de confiança.
- Limitação comprovada: `tools/whatsapp_catalog_adapter.py::find_contacts_for_model` depende de `_read_only_source(alias)` e `contacts.display_name`; `whatsapp_recipient_resolution.resolve_recipient_reference` só aceita um `contact_id` da fonte. A interface model-facing `whatsapp_send_message` não recebe número bruto; não há no schema atual um fluxo de referência derivada de auto-chat autenticado. Essa é uma lacuna de produto, não uma falha do número autorizado pelo usuário.
- O último ensaio automatizado de 4 arquivos de envio individual terminou com **71 passed**. Nenhuma TaskRun real, BrowserTask autenticada, aprovação host ou evidência E2E foi produzida nesta retomada.

**Próxima correção mínima proposta, sem autorização para enfraquecer os controles:** implementar caminho específico de `self-chat` ou descoberta nativa verificada para o usuário autenticado, dentro da mesma TaskRun e BrowserTask, que produza uma referência opaca validada pelo host (sem alterar `acirv_contacts` nem aceitar número bruto model-facing). Validar identidade completa via DOM e proveniência, correspondência com nome/número autorizado, consentimento e cartão host `once` antes do único efeito. Se `Kevyn ACIRV` corresponder a terceiro ou ao registro divergente, exigir correspondência explícita e não inferir equivalência com o auto-chat. Preserve a implementação existente para contatos ACIRV. Criar testes RED/GREEN contra trocas de identidade, TaskRun, texto, número, origem e consentimento; nunca iniciar lote. Sem esse caminho ou uma referência existente exata e consentida, manter HOLD.

O jornal compartilhado `workstation/context/engineering-journal/CURRENT.md` permanece dirty e não foi regravado. Nenhuma prova simulada substitui envio real.


## 11. WA-MVP-02A — contatos externos, registro local e bloqueio do canário (12/11/2026)

**Implementação local concluída; envio E2E real PENDENTE DA TASKRUN/ONCE.** O usuário explicitamente retirou a regra de permitir apenas contatos de acirv_contacts: números não cadastrados, inclusive fornecidos por deeplink, devem poder entrar no fluxo e ser registrados na database. O backend jamais deve inferir identidade/consentimento a partir de nome parecido ou de um número isolado.

### Implementado nesta missão

- workstation/integrations/hermes/whatsapp_contact_intake.py **novo**: registro de destinatário externo explicitamente solicitado por telefone internacional ou deeplink de número sem texto, normalização, deduplicação, registro de proveniência pendente, validação conservadora de label/número e promoção condicionada a recibo DOM OBSERVED. Usa a tabela canonical contacts do mesmo banco de controle WhatsApp, sem criar outro arquivo DB. Não escreve em acirv_contacts.
- workstation/integrations/hermes/whatsapp_recipient_resolution.py: alias interno hermes_local deriva exclusivamente de control_db_path confiável. Resolve refs locais, valida dois campos telefônicos e estado/proveniência pending:numero antes de eventual @c.us verificado; mantém source ACIRV configurada como antes. Nome/número divergentes bloqueiam.
- tools/browser_tool.py + toolsets.py: whatsapp_register_contact model-facing MUTATION, TaskRun autenticada obrigatória, argumentos phone/display_name, resposta com recipient_ref sem retornar PII. Reutiliza whatsapp_find_contacts(source=hermes_local) para descobrir cadastrados. A tool whatsapp_send_message permanece responsável por pedir approval ONCE e pelo único efeito externo.
- tools/browser_workstation.py: após o executor nativo devolver OBSERVED, promoção da proveniência apenas para ref hermes_local e número coincidente. UNCERTAIN/REVIEW_REQUIRED/FAILED não promovem.
- workstation/integrations/hermes/whatsapp_native_send_bridge.py e whatsapp_causal_receipt.py: suportam conversa inicialmente vazia para contato novo, após painel de informações com número exato, compositor inspecionado e inventário válido; ainda exigem mensagem com ID novo, autor correto, corpo exato e ACK no mesmo ancestral após máximo de um clique. A variante de verificação de auto-chat do usuário não foi relaxada.
- workstation/integrations/hermes/whatsapp_human_approval.py: cartão de aprovação do HOST mostra número de destino COMPLETO e texto integral para decisão humana; descrições/logs model-facing continuam mascarados.
- skill local whatsapp-native-operator ampliada com o procedimento de novos contatos, histórico local, HOLD e uso de BrowserTask para descobrir números quando o pedido contém apenas nome.
- workstation/tests/test_whatsapp_contact_intake.py **novo**: cadastro persistente e idempotente; rejeição de números inválidos e deeplinks com texto/origem não confiável; privacidade; execução restrita a TaskRun; drifts bloqueados; sincronização de estado; descoberta local read-only; primeira mensagem em chat vazio com somente um clique simulado e recibo OBSERVED.

### Evidências e dados reais

- RED antes da implementação: 11 falhas por módulo/fluxo ausente; cenário de primeiro contato reproduziu 1 falha no executor antigo antes do clique. GREEN: **192 passed / 0 failed em 22,28 s**, todos os 14 arquivos de workstation/tests/test_whatsapp_*.py via python -m pytest -q -p no:cacheprovider, com PYTHONDONTWRITEBYTECODE=1 (exit 0).
- Ruff nos arquivos tocados, após corrigir comentário de teste: All checks passed (exit 0). git diff --check nos tracked editados: exit 0. Registro da tool em processo isolado: registry=True, ToolEffect.MUTATION, toolsets.desktop_ui=True. Isso não prova o carregamento no processo Hermes já em execução.
- **Única mutação factual fora de código/testes:** cadastro do contato de teste expressamente autorizado no banco control_db_path do usuário, com nome informado "Kevyn ACIRV", número exatamente informado em turno anterior (sem completar nono dígito); recipient_ref={"source":"hermes_local","contact_id":1}, phone_source=user_requested_unverified, estado PENDING_NATIVE_VERIFICATION. Consulta read-only real via whatsapp_find_contacts(source=hermes_local,query="Kevyn ACIRV") retornou 1 único registro com esse ref, sem número na resposta.
- Na conferência após registro: whatsapp_send_logs tinha **0 registros**, nenhuma mensagem enviada, nenhum grant gerado, nenhuma campanha iniciada. Conversão do esquema SQLite foi forward-only via init_whatsapp_control_tables já existente.
- Checkout preservado na branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e. Sem restart, reset, stash, checkout, commit ou push. Jornal shared CURRENT.md já dirty antes; intocado.

### Próxima verificação inegociável

Em uma nova TaskRun REAL do Hermes, carregar tools/skill atuais (se sessão existente não refletir mudança, pedir ao usuário reinicialização MANUAL, jamais reiniciar unilateralmente). Usar whatsapp_find_contacts(source=hermes_local,query="Kevyn ACIRV"), exigir ref hermes_local/1, verificar auto-chat/autoria na MESMA BrowserTask, submeter mensagem literal de WA_OPC011_HERMES_REAL_TEST_20261112.md a whatsapp_send_message. O host deve mostrar destinatário/número completo e texto, e o usuário deve selecionar ONCE. Só então navegar para o número aprovado e fazer no máximo um clique. Registrar log, receipt, operation_id/TaskRun e status verdadeiro. Proibido afirmar CONFIRMED sem confirmação independente do servidor ou reenviar resultado incerto. A autorização de cadastro e o texto da missão NÃO equivalem ao ONCE. Campanhas continuam HOLD.

**Limitações conhecidas:** nome sem número e ausente das duas bases depende de inspeção nativa autenticada do próprio Hermes; não há descoberta pelo WhatsApp real testada nesta rodada. Cadastro em contacts do banco de controle WhatsApp foi verificado, mas integração desse cadastro com outros painéis da Database/CRM não foi homologada. Não confundir 192 testes de unidade/simulação com um E2E de terceiro.

## 12. WA-MVP-02 — checagem das pré-condições para homologação real (12/11/2026)

**Estado: HOLD; E2E não realizado.** O acesso atual ao dispositivo tem terminal e arquivos, mas não oferece controle autorizado da interface de uma nova Work TaskRun do Hermes nem do cartão humano gateway ONCE. Proibido substituir o fluxo nativo por shell, CDP, clipboard, Browser Exec externo ou contexto artificial.

- Repositório C:\Github\hermes-agent, branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, 573 itens dirty/untracked na inspeção inicial. Nenhum reset, stash, checkout, commit, push ou restart.
- Verificação SQLite read-only: resolve_recipient_reference({source:hermes_local,contact_id:1}) corresponde ao nome Kevyn ACIRV e ao número autorizado pelo usuário. find_contacts_for_model(source=hermes_local,query=Kevyn ACIRV) retorna 1 referência sem telefone na resposta. Contato com proveniência user_requested_unverified.
- Banco de controle WhatsApp: whatsapp_send_logs = 0 registros. Nenhum clique, aprovação ONCE, envio, receipt nem mudança de status de contato.
- Electron PID 20980 iniciado 09:48:43 e backends Python PIDs 31944/26600 às 13:52:22; os arquivos alterados da WA-MVP-02A receberam modificações posteriores, aproximadamente 14:28–14:32. Não há prova de que o runtime carregou a nova tool; nenhum reinício foi feito.
- No terminal externo current_work_execution_identity() = None e gateway_approval_available() = False. Esses valores NÃO são prova sobre a UI de uma TaskRun autêntica do Hermes; apenas demonstram que o terminal externo não é uma TaskRun autorizada.
- Teste local atual, sem bytecode/cache: PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider workstation/tests/test_whatsapp_human_approval.py workstation/tests/test_whatsapp_taskrun_binding.py workstation/tests/test_whatsapp_causal_receipt.py workstation/tests/test_whatsapp_browser_executor.py workstation/tests/test_whatsapp_contact_intake.py => 92 passed em 14,03 s. Prova sintética, não E2E.

**Próxima ação:** usuário abrir NOVA TaskRun diretamente no Hermes Desktop, após atualizar a instância manualmente se necessário. Usar o procedimento atualizado em WA_OPC011_HERMES_REAL_TEST_20261112.md (seção ATUALIZAÇÃO WA-MVP-02A): skill, duas tools, contato hermes_local/1, auto-chat de própria BrowserTask, número completo no painel, mensagem literal, aprovação humana gateway ONCE, no máximo um clique. Registrar operação/TaskRun/hash/aprovação/recibo e estado real. Nunca reexecutar UNCERTAIN nem classificar DOM OBSERVED como servidor CONFIRMED.

Jornal compartilhado dirty permaneceu intocado; nenhum programa ou banco real foi modificado nesta verificação. Campanhas seguem HOLD.


## CORRECAO POSTERIOR ? ATENCAO: DESTINATARIO E A PROPRIA CONTA (12/11/2026)

Esta secao SUBSTITUI os prompts anteriores deste documento que nomeiam Kevyn ACIRV como destinatario. O usuario corrigiu a associacao: o numero +55 64 9247-0988 corresponde ao proprio perfil conectado ao WhatsApp Web, identificado na interface como Voce. Nao atribuir esse numero ao contato Kevyn ACIRV.

Registro local corrigido em contacts id=1 (mesma ref hermes_local/1), com display_name="+55 64 9247-0988 (Você)", phone_source=user_requested_unverified, sem promover verificacao ou executar envio. A consulta de descoberta correta e whatsapp_find_contacts(source="hermes_local",query="Você"), que retornou exatamente a referencia esperada.

O E2E agora e uma mensagem PARA SI MESMO, nao para contato ACIRV ou terceiro externo. Antes de solicitar ONCE, verifique no WhatsApp Web real que a conta autenticada e o auto-chat representam o mesmo numero completo. Se nao for possivel provar o numero no perfil e no painel, HOLD, sem envio. Todo o resto do contrato (nova TaskRun, BrowserTask vinculada, cartao humano ONCE, no maximo um clique, recibo causal, persistencia, sem repetir UNCERTAIN) continua obrigatorio.

PROMPT OPERACIONAL ATUALIZADO: workstation/context/WA_MVP_02_E2E_READY_20261112.md.
A atualizacao do label nao e confirmacao de identidade, nao prova runtime atualizado e nao e homologaçao E2E. Campanhas seguem HOLD.

## 13. ESTADO OPERACIONAL VIGENTE — WA-MVP-02 (13/11/2026)

Esta seção substitui os procedimentos anteriores de envio individual (especialmente PROMPT 02 e exigência ONCE). As seções 7–12 foram mantidas como histórico. Para campanhas WA-MVP-03..05, continuar exigindo autorização específica do manifesto, opt-out e prevenção de duplicidade.

**Status:** WA-MVP-01 concluída localmente; WA-MVP-02 em execução, não homologada; WA-MVP-03..05 pendentes.

**Destinatário:** o próprio WhatsApp Web +55 64 9247-0988 (Você), ref `{"source":"hermes_local","contact_id":1}`. Não corresponde ao antigo rótulo Kevyn ACIRV.

**Autonomia individual:** o usuário define destinatário e corpo uma única vez. `admitted_whatsapp_point_send` assume TaskRun automaticamente no dispatcher, sem cartão manual, menu de escolhas ou segunda aprovação ONCE. Preservar BrowserTask nativa e no máximo um clique de envio.

**Histórico real:** cinco registros em `whatsapp_send_logs`: IDs 1/2 `FAILED / CHAT_HEADER_NOT_UNIQUE`; IDs 3/4/5 `FAILED / CHAT_IDENTITY_UNVERIFIED`; todos antes de enviar (`sent=0`). A tentativa 5 usou TaskRun `t_3d38b8e8`, run `102`. Não há homologação real.

**DOM e código:** o cabeçalho do auto-chat pode não ter `data-chat-id`; título e número aparecem no chat, e `aria-label` do composer pode ser genérico. Mensagens podem omitir `data-recipient-id` e `data-direction`. O `whatsapp_native_send_bridge.py` possui ajustes e regressões para esses casos, mas a falha real ainda persiste. Testes verdes não comprovam entrega.

**Próxima ação:** inspecionar somente leitura o chat ATIVO na BrowserTask para localizar a divergência exata de `check_chat_identity()`. Corrigir o menor seletor/contrato necessário e testar positivamente o auto-chat e negativamente número divergente. Somente depois, executar novo canário único com texto NOVO definido no pedido ao Hermes, usando diretamente `whatsapp_send_message` com TaskRun automática. Não reutilizar operações anteriores.

**Aceite WA-MVP-02:** um clique no máximo, nova mensagem com ID e corpo exato, ACK causal, persistência e relato honesto (`OBSERVED` no DOM não equivale à confirmação independente de servidor). `UNCERTAIN` nunca deve ser repetido. Não ativar campanhas antes do E2E.

### 13.1. Progresso efetivo em 13/11/2026 — DOM real e correção de readiness

- Inspeção read-only pela BrowserTask da TaskRun 5 confirmou chat ativo do próprio usuário: `conversation-info-header` contém número completo e identificação de auto-chat; `cell-frame-title` aponta ao mesmo número; `conversation-compose-box-input` tem `aria-label` direcionado ao número; não há `data-chat-id` nesse cabeçalho. Nenhum envio foi realizado pela inspeção.
- A condição do código atual reconhece esses atributos depois que a interface termina de renderizar. Hipótese material para as falhas pré-clique repetidas: o WhatsApp finaliza navegação antes de renderizar a identidade, e a releitura única de 150 ms era insuficiente.
- Nova regressão `test_real_chat_header_can_take_three_native_reads_to_render` reproduziu `FAILED` com três leituras sem identidade. Correção mínima em `whatsapp_native_send_bridge.py`: espera de até 1 segundo, com polling de 100 ms somente em `CHAT_IDENTITY_UNVERIFIED`; chat divergente continua `FAILED` sem clique. Nenhuma espera extra no caminho feliz.
- Testes após correção: 18 focados aprovados; suíte WhatsApp completa **192 passed**; `git diff --check` dos arquivos rastreados sem erro material. Não é prova de envio E2E.
- Próximo passo: **reiniciar o Hermes Desktop para carregar o backend alterado** (sem interromper trabalhos concorrentes) e executar o texto único do arquivo `workstation/context/WA_MVP_02E_REAL_E2E_20261113.md` pela interface do próprio Hermes. Não executar por terminal externo.
- Estado final desta intervenção: `WA-MVP-02 = TESTES LOCAIS VERDES / E2E REAL PENDENTE`. Não houve clique de envio nesta intervenção, nem limpeza dos cinco logs históricos, nem liberação de campanhas.
