"""Hermes Workstation Prefabricated Operational Capabilities.

This package provides pre-compiled, auditable navigation and read-only operation
recipes for known destinations (Trello, Instagram, WhatsApp, ChatGPT, etc.).
"""
from __future__ import annotations

from .catalog import DESTINATIONS, Destination, get_destination, match_navigation, match_trello_read
from .engine import NavigationReceipt, navigate
from .integration import (
    maybe_resolve_navigation,
    prepare_user_navigation,
    prepare_user_trello_read,
    prepare_user_creative_app,
)
from .trello import Credential, TrelloAccessError, TrelloClient, sha256_text
from .offline import html_fingerprint, session_fingerprint
from .seeding import seed_discovered

__all__ = [
    "DESTINATIONS",
    "Credential",
    "Destination",
    "NavigationReceipt",
    "TrelloAccessError",
    "TrelloClient",
    "get_destination",
    "html_fingerprint",
    "match_navigation",
    "match_trello_read",
    "maybe_resolve_navigation",
    "navigate",
    "prepare_user_creative_app",
    "prepare_user_navigation",
    "prepare_user_trello_read",
    "seed_discovered",
    "session_fingerprint",
    "sha256_text",
]