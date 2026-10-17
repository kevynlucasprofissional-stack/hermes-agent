"""Two conservative lifecycle adapters for the existing Workstation boundary.

No independent browser, agent, session or authority owner is created here.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from .catalog import (Destination, get_destination, match_navigation, match_trello_read,
                      match_instagram_read, match_whatsapp_read, match_chatgpt_read,
                      InstagramReadIntent, WhatsAppReadIntent, ChatGPTReadIntent)
from .engine import navigate

_LOG = logging.getLogger(__name__)


def prepare_user_navigation(envelope: Any) -> str | None:
    """Only an authenticated user-origin turn may enter the automatic fast path."""
    if envelope is None:
        return None
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    destination = match_navigation(getattr(envelope, "content", ""))
    return destination.key if destination is not None else None


def prepare_user_creative_app(envelope: Any) -> Any:
    """Parse only an authenticated human turn requesting PhotoCraft or EffectCraft."""
    if envelope is None:
        return None
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    from workstation.creative_web_app_spec import recognize_open_creative_app
    return recognize_open_creative_app(getattr(envelope, "content", ""))


def prepare_user_trello_read(envelope: Any):
    """Parse only an authenticated human-origin direct read of known ACIRV boards."""
    if envelope is None:
        return None
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    return match_trello_read(getattr(envelope, "content", ""))


def prepare_user_instagram_read(envelope: Any):
    """Parse only an authenticated human-origin direct read of Instagram."""
    if envelope is None:
        return None
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    return match_instagram_read(getattr(envelope, "content", ""))


def prepare_user_whatsapp_read(envelope: Any):
    """Parse only an authenticated human-origin direct read of WhatsApp."""
    if envelope is None:
        return None
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    return match_whatsapp_read(getattr(envelope, "content", ""))


def prepare_user_chatgpt_read(envelope: Any):
    """Parse only an authenticated human-origin direct read of ChatGPT."""
    if envelope is None:
        return None
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    return match_chatgpt_read(getattr(envelope, "content", ""))


def _resolve_trello_read(intent: Any):
    """GET only; the authenticated API read *is* the result, without LLM."""
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    from workstation.prefabs.trello import TrelloClient
    try:
        data = TrelloClient().board_cards(intent.board, search=intent.search, limit=30)
    except Exception as exc:
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=("N\u00e3o consegui consultar o Trello com a API autorizada. "
                            "Verifique TRELLO_API_KEY, TRELLO_TOKEN e permiss\u00f5es do quadro. "
                            "Nenhuma altera\u00e7\u00e3o foi realizada."),
            reason=f"prefab_trello_read_failed:{type(exc).__name__}", provider="hermes_prefabs")
    cards = data["cards"]
    default_name = "(sem t\u00edtulo)"
    items = [f"- {row.get('name') or default_name} — {row.get('shortUrl') or row.get('id')}"
             for row in cards]
    suffix = " (mostrando os 30 primeiros)" if data["truncated"] else ""
    response = (f"Consulta conclu\u00edda: {data['total_matches']} cards correspondentes no quadro "
                f"{intent.board}{suffix}." + ("\n" + "\n".join(items) if items else ""))
    return OperationalResolution(
        outcome=OperationalOutcome.SATISFIED, final_response=response,
        reason="prefab_trello_read_verified", provider="hermes_prefabs",
        details={"board": intent.board, "matched": data["total_matches"], "read_only": True})


def _resolve_instagram_read(intent: InstagramReadIntent):
    """Instagram reads via official API when authorized; browser fallback for profile."""
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    if intent.target == "feed":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response="Instagram feed leitura requer API oficial autorizada. Navegacao via browser nao implementada.",
            reason="prefab_instagram_feed_requires_api", provider="hermes_prefabs")
    if intent.target == "profile":
        # Browser navigation to profile
        return None  # Let navigation handle it
    if intent.target == "insights":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response="Instagram insights requerem API Graph autorizada (Business/Creator account). Nao implementado.",
            reason="prefab_instagram_insights_requires_api", provider="hermes_prefabs")
    return None


def _resolve_whatsapp_read(intent: WhatsAppReadIntent):
    """WhatsApp reads - authorized conversation scope only."""
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    if intent.scope == "conversation_list":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response="WhatsApp lista de conversas requer navegacao via browser autorizada. Nao implementado.",
            reason="prefab_whatsapp_conversation_list_not_implemented", provider="hermes_prefabs")
    if intent.scope == "conversation":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=f"WhatsApp conversa com {intent.contact} requer navegacao autorizada. Nao implementado.",
            reason="prefab_whatsapp_conversation_not_implemented", provider="hermes_prefabs")
    return None


def _resolve_chatgpt_read(intent: ChatGPTReadIntent):
    """ChatGPT reads - semantic editor location, no auto-send."""
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    if intent.scope == "history":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response="ChatGPT historico requer navegacao via browser. Nao implementado.",
            reason="prefab_chatgpt_history_not_implemented", provider="hermes_prefabs")
    if intent.scope == "search":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=f"ChatGPT busca por '{intent.query}' requer navegacao via browser. Nao implementado.",
            reason="prefab_chatgpt_search_not_implemented", provider="hermes_prefabs")
    return None


def _resolve_creative_app_open(app: Any, agent: Any, context: Any):
    """Launch or reuse managed creative web app and open in native Browser."""
    session = str(getattr(context, "session_id", "") or "")
    task = str(getattr(context, "task_id", "") or getattr(agent, "_canonical_work_task_id", "") or session)
    if not task or not session:
        return None
    valid = getattr(agent, "valid_tool_names", set())
    if "browser_navigate" not in valid or "browser_snapshot" not in valid:
        return None
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    from workstation.creative_web_service import open_and_verify_creative_web_app
    try:
        from workstation.integrations.hermes.scoped_execution import (
            workstation_scoped_execution, workstation_durable_dispatch)
        scoped = workstation_durable_dispatch(agent)
        with workstation_scoped_execution(agent, task, None):
            def dispatch(name: str, args: dict):
                return scoped(name, args, task, f"creative_{app.key}_" + uuid.uuid4().hex[:16])
            receipt = open_and_verify_creative_web_app(app, dispatch)
    except Exception as exc:  # health: allow BLE001 -- deliberate pre-LLM boundary handling dispatch failures cleanly as HANDOFF
        _LOG.warning("Creative web app dispatcher returned uncertain: %s", type(exc).__name__, exc_info=True)
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=f"Abertura de {app.label} solicitada, mas ocorreu um erro no despacho. Confira antes de tentar novamente.",
            reason="creative_app_dispatch_uncertain", provider="hermes_creative_web")

    if receipt.status == "verified":
        reused_msg = " (instancia reutilizada)" if receipt.reused else ""
        return OperationalResolution(
            outcome=OperationalOutcome.EXECUTED,
            final_response=f"{app.label} aberto e verificado no Browser nativo: {receipt.url}{reused_msg}.",
            reason=receipt.reason, provider="hermes_creative_web",
            details={"engine": app.key, "url": receipt.url, "reused": receipt.reused,
                     "verification": "independent_browser_snapshot"})
    if receipt.status == "missing_dist":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=(f"A distribuicao web oficial de {app.label} nao foi encontrada. "
                            f"Instale a versao web em ~/.hermes/workstation/creative/engines/{app.key}/web-dist "
                            f"ou defina HERMES_{app.key.upper()}_WEB_DIST."),
            reason="missing_prebuilt_web_dist", provider="hermes_creative_web",
            details={"engine": app.key, "verified": False})
    if receipt.status == "user_control_active":
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response="O controle humano esta ativo no navegador. Libere o controle antes de abrir pelo agente.",
            reason="user_control_active", provider="hermes_creative_web",
            details={"engine": app.key, "verified": False})
    if receipt.dispatch_attempted or receipt.status in {"uncertain", "failed"}:
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=(f"Solicitei a abertura de {app.label}, mas o estado final nao foi confirmado ({receipt.reason}). "
                            "Confira a aba antes de repetir a operacao."),
            reason=receipt.reason, provider="hermes_creative_web",
            details={"engine": app.key, "verified": False})
    return None


def maybe_resolve_navigation(context: Any):
    """One-shot fast path before System-2; uncertain dispatch NEVER falls through.

    The caller invokes this from workstation_operational_resolution. A stopped,
    untrusted, unsupported, or ambiguous request returns None without IO.
    """
    agent = getattr(context, "agent", None)
    if agent is None:
        return None
    key = getattr(agent, "_prefab_navigation_intent", None)
    trello_intent = getattr(agent, "_prefab_trello_read_intent", None)
    instagram_intent = getattr(agent, "_prefab_instagram_read_intent", None)
    whatsapp_intent = getattr(agent, "_prefab_whatsapp_read_intent", None)
    chatgpt_intent = getattr(agent, "_prefab_chatgpt_read_intent", None)
    creative_app_intent = getattr(agent, "_prefab_creative_app_intent", None)
    # Consume before touching IO, including on exceptions, so a second
    # resolution iteration cannot cause a duplicate browser dispatch.
    agent._prefab_trello_read_intent = None
    agent._prefab_instagram_read_intent = None
    agent._prefab_whatsapp_read_intent = None
    agent._prefab_chatgpt_read_intent = None
    agent._prefab_navigation_intent = None
    agent._prefab_creative_app_intent = None
    if not key and not any([trello_intent, instagram_intent, whatsapp_intent, chatgpt_intent, creative_app_intent]):
        return None
    if getattr(agent, "_interrupt_requested", False) or getattr(agent, "_tool_guardrail_halt_decision", None):
        return None
    # Handle creative web app open
    if creative_app_intent is not None and not key:
        return _resolve_creative_app_open(creative_app_intent, agent, context)
    # Handle read intents first (API-based, no browser dispatch)
    if trello_intent is not None and not key:
        return _resolve_trello_read(trello_intent)
    if instagram_intent is not None and not key:
        result = _resolve_instagram_read(instagram_intent)
        if result is not None:
            return result
    if whatsapp_intent is not None and not key:
        result = _resolve_whatsapp_read(whatsapp_intent)
        if result is not None:
            return result
    if chatgpt_intent is not None and not key:
        result = _resolve_chatgpt_read(chatgpt_intent)
        if result is not None:
            return result
    # Handle navigation
    try:
        target = get_destination(key)
    except ValueError:
        return None
    session = str(getattr(context, "session_id", "") or "")
    task = str(getattr(context, "task_id", "") or getattr(agent, "_canonical_work_task_id", "") or session)
    if not task or not session:
        return None
    # If tools are not available in this agent session, skip; don't invent a
    # privilege bypass or launch an unscoped HTTP/browser client.
    valid = getattr(agent, "valid_tool_names", set())
    if "browser_navigate" not in valid or "browser_snapshot" not in valid:
        return None
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    try:
        from workstation.integrations.hermes.scoped_execution import (
            workstation_scoped_execution, workstation_durable_dispatch)
        scoped = workstation_durable_dispatch(agent)
        with workstation_scoped_execution(agent, task, None):
            def dispatch(name: str, args: dict):
                return scoped(name, args, task, "prefab_" + uuid.uuid4().hex[:16])
            receipt = navigate(target, dispatch)
    except Exception as exc:
        _LOG.warning("Prefabricated navigation dispatcher returned uncertain: %s", type(exc).__name__)
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response="Navega\u00e7\u00e3o solicitada, mas n\u00e3o foi poss\u00edvel confirmar o resultado. Confira a aba antes de tentar novamente.",
            reason="prefab_dispatch_uncertain", provider="hermes_prefabs")
    if receipt.status == "verified":
        return OperationalResolution(
            outcome=OperationalOutcome.EXECUTED,
            final_response=f"P\u00e1gina aberta e endere\u00e7o confirmado: {target.title} ({target.url}).",
            reason="prefab_navigation_verified", provider="hermes_prefabs",
            details={"target_key": key, "verification": "independent_browser_snapshot"})
    if receipt.dispatch_attempted:
        return OperationalResolution(
            outcome=OperationalOutcome.HANDOFF,
            final_response=(f"Solicitei a abertura de {target.title}, mas o estado final n\u00e3o foi confirmado. "
                            "Confira a aba antes de repetir a opera\u00e7\u00e3o."),
            reason=receipt.reason, provider="hermes_prefabs",
            details={"target_key": key, "verified": False})
    return None