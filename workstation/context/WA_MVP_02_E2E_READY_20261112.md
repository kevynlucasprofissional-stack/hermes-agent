# WA-MVP-02 — Canário E2E real no Hermes Desktop

Preparação: 12/11/2026. Documento operacional, não autorização de envio.

## Pré-checagem concluída

- Checkout: C:\Github\hermes-agent; main; HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e; 574 entradas dirty/untracked. Preservar tudo.
- Contato: +55 64 9247-0988 (Você), declarado pelo usu?rio como a pr?pria conta conectada, ainda n?o confirmado nativamente; recipient_ref {"source":"hermes_local","contact_id":1}; número autorizado +55 64 9247-0988, sem corrigir ou acrescentar dígitos.
- Busca local do nome retornou 1 referência correta, sem telefone na resposta.
- Registry em processo Python novo: whatsapp_find_contacts (read-only), whatsapp_send_message (mutation), whatsapp_register_contact (mutation).
- Banco de controle: contato user_requested_unverified e 0 envios registrados.
- Os processos Electron e backend iniciaram ANTES das últimas mudanças de código. É necessária uma atualização MANUAL da instância para garantir que a TaskRun nova carregue as ferramentas. Não executar restart automático.
- E2E, approval ONCE e recibo real ainda não foram observados.

## PROMPT PARA COLAR EM UMA NOVA TASKRUN DO HERMES

**MISSÃO WA-MVP-02 — Homologação E2E, um envio WhatsApp**

Execute este teste como uma única TaskRun real do Hermes Work, dentro do Desktop e exclusivamente com sua BrowserTask nativa autenticada. Não use CDP externo, porta 9222, scripts, terminal para controlar WhatsApp, clipboard, navegador alheio ou mouse/teclado global. Não faça restart, reset, stash, checkout, commit ou push. Não inicie campanhas.

### Destinatário e mensagem literais

Nome: +55 64 9247-0988 (Você).
Referência: {"source":"hermes_local","contact_id":1}.
Número completo esperado no painel e no cartão de aprovação: +55 64 9247-0988.
Mensagem EXATA, sem prefixos ou sufixos:

WA-OPC-011 QA 20261112 — teste individual do Hermes Work — autorização única.

### Fluxo obrigatório

1. Carregue a skill whatsapp-native-operator na versão atual. Verifique que whatsapp_find_contacts e whatsapp_send_message estão disponíveis de fato NESTA TaskRun, não somente no código-fonte. Se estiverem ausentes, pare em HOLD.
2. Identifique sua TaskRun, sessão e BrowserTask próprias. Confirme que WhatsApp Web está autenticado no Chromium nativo vinculado a elas. Não utilize aba de outra execução.
3. Execute whatsapp_find_contacts(source="hermes_local", query="Você"). Confirme resultado único com a referência exata hermes_local/1. Não substitua por outro contato de nome parecido.
4. ESTE E UM TESTE DE MENSAGEM PARA SI MESMO: o destino deve ser a propria conta autenticada, identificada como Você no WhatsApp. Na MESMA BrowserTask, verifique a identidade e autoria da propria conta; se nao houver prova nativa ou os numeros divergirem, HOLD. O cadastro local e o deeplink nao sao prova.
5. O cadastro continua PENDING_NATIVE_VERIFICATION. Confirme que o numero do PERFIL AUTENTICADO e do auto-chat no painel do WhatsApp correspondem exatamente a +55 64 9247-0988. Se a plataforma rejeitar ou nao permitir confirmar o numero, HOLD; nao complete nem substitua digitos.
6. Prepare whatsapp_send_message com recipient_ref={"source":"hermes_local","contact_id":1}, message="WA-OPC-011 QA 20261112 — teste individual do Hermes Work — autorização única.", verify_delivery=true.
7. A tool DEVE apresentar cartão nativo autenticado com nome, NÚMERO INTEGRAL, corpo EXATO da mensagem, TaskRun e operação. Só a escolha HUMANA ONCE nesse cartão autoriza continuar. ESTE PROMPT NÃO É AUTORIZAÇÃO. Se a aprovação ONCE não aparecer, for negada ou não for autenticada, pare sem enviar.
8. Após ONCE, revalide número integral no painel, autoria, contexto BrowserTask e corpo. Faça NO MÁXIMO um clique de enviar. Conversa inicialmente sem mensagens anteriores é válida se a inspeção completa do inventário indicar zero; nunca trate falha de leitura como lista vazia.
9. Antes/depois: verifique exatamente uma bolha nova, ID novo, corpo exato, autor próprio e ACK da mesma bolha. Registre o estado real: OBSERVED, UNCERTAIN, REVIEW_REQUIRED ou FAILED. OBSERVED do DOM não equivale a CONFIRMED por servidor.
10. Verifique log persistente de operation_id, TaskRun/run_id, message_digest, approval_fingerprint e resultado. O cadastro local só pode ser promovido com recibo causal válido. Não exponha dados privados no relatório.
11. Se o efeito for incerto, NÃO tente enviar novamente, NÃO crie outro operation_id, NÃO repita via outra ferramenta. Reconciliar/ler antes de qualquer ação futura. Não abrir campanhas.

### Aceite e relatório

Aceite apenas com TaskRun/BrowserTask autênticas, destinatário correto, UMA aprovação humana ONCE, no máximo UM clique, recibo causal íntegro e log persistente correlacionado.

Entregue no Hermes um resumo factual com: ferramentas disponíveis, TaskRun válida, contato correto, aprovação ONCE sim/não, contagem de cliques, estado/erro, recibo causal, persistência e promoção do cadastro. Se algum gate falhar, HOLD e requisito exato faltante. Sem E2E real, não declarar homologação concluída. Registrar no contexto existente sem substituir alterações de terceiros.

### Restrições

A autorização de preparar o ensaio não é autorização de enviar. Não repetir envios incertos, não simular gateway, não inventar logs e não declarar CONFIRMED a partir de uma bolha OBSERVED.
