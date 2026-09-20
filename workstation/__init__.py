"""Hermes Workstation downstream integration contracts.

Importing the Workstation product package is an explicit bootstrap boundary.
Normal Hermes code does not import it. Required supervision therefore fails
closed, while callers that deliberately request degraded mode get an observable
status instead of a swallowed exception.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

__version__ = "0.1.0-dev"
logger = logging.getLogger(__name__)

AdapterMode = Literal["disabled", "degraded", "required"]


@dataclass(frozen=True)
class AdapterBootstrapStatus:
    mode: AdapterMode
    installed: bool
    error: Optional[str] = None


_adapter_bootstrap_status = AdapterBootstrapStatus(mode="disabled", installed=False)


def bootstrap_workstation_adapter(mode: AdapterMode = "required") -> AdapterBootstrapStatus:
    """Install first-party supervision with explicit disabled/degraded/required truth."""
    global _adapter_bootstrap_status
    if mode == "disabled":
        _adapter_bootstrap_status = AdapterBootstrapStatus(mode=mode, installed=False)
        return _adapter_bootstrap_status
    try:
        from workstation.integrations.hermes.adapter import install_workstation_adapter
        install_workstation_adapter()
    except Exception as exc:
        _adapter_bootstrap_status = AdapterBootstrapStatus(
            mode=mode, installed=False, error=f"{type(exc).__name__}: {exc}",
        )
        logger.exception("Workstation adapter bootstrap failed in %s mode", mode)
        if mode == "required":
            raise RuntimeError("required Workstation supervision failed to initialize") from exc
        return _adapter_bootstrap_status
    _adapter_bootstrap_status = AdapterBootstrapStatus(mode=mode, installed=True)
    return _adapter_bootstrap_status


def workstation_adapter_status() -> AdapterBootstrapStatus:
    return _adapter_bootstrap_status


# Importing this product package opts into required Workstation supervision.
bootstrap_workstation_adapter("required")
