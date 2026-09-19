"""Hermes Workstation downstream integration contracts."""

__version__ = "0.1.0-dev"

try:
    from workstation.integrations.hermes.adapter import install_workstation_adapter

    install_workstation_adapter()
except Exception:
    pass
