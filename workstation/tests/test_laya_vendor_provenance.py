"""Test Laya vendoring and strict provenance verification.

Proves:
- import laya resolves exclusively to workstation/third_party/laya.
- strict provenance check enforces path matching and lock parity.
- external/global rogue imports are strictly rejected in strict mode.
"""
from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest

from workstation.system1.provenance import (
    get_laya_provenance,
    verify_laya_provenance,
    LayaProvenance,
)


def test_laya_vendor_provenance_success():
    """Verify that current environment resolves Laya from the vendored subtree."""
    prov = get_laya_provenance()
    assert prov.provider == "laya"
    assert prov.is_vendored is True
    assert prov.source_bytes_verified
    assert prov.laya_version == "0.3.23"
    assert prov.lock_sha == "4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c"

    # Strict verification must succeed
    assert verify_laya_provenance(strict=True) is True


def test_laya_vendor_provenance_rejects_external_path():
    """Strict verification must fail-closed if laya resolves outside third_party."""
    with patch("workstation.system1.provenance.get_laya_provenance") as mock_prov:
        mock_prov.return_value = LayaProvenance(
            provider="laya",
            source_path="/usr/local/lib/python3.11/site-packages/laya/__init__.py",
            laya_version="0.3.23",
            laya_source_sha="external-sha",
            lock_sha="4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c",
            is_vendored=False,
            device="cpu",
        )

        with pytest.raises(RuntimeError, match="Laya provenance violation"):
            verify_laya_provenance(strict=True)

        # In non-strict mode it returns False rather than raising
        assert verify_laya_provenance(strict=False) is False


def test_laya_vendor_provenance_rejects_version_mismatch():
    """Strict verification must reject unapproved version drift."""
    with patch("workstation.system1.provenance.get_laya_provenance") as mock_prov:
        mock_prov.return_value = LayaProvenance(
            provider="laya",
            source_path="c:/Github/hermes-agent/workstation/third_party/laya/laya/__init__.py",
            laya_version="0.4.0",
            laya_source_sha="4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c",
            lock_sha="4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c",
            is_vendored=True,
            device="cpu",
        )

        with pytest.raises(RuntimeError, match="Version mismatch"):
            verify_laya_provenance(strict=True)


def test_external_module_injection_is_rejected(monkeypatch, tmp_path):
    from types import ModuleType
    rogue = ModuleType("laya")
    rogue.__file__ = str(tmp_path / "laya" / "__init__.py")
    rogue.__version__ = "0.3.23"
    monkeypatch.setitem(sys.modules, "laya", rogue)
    with pytest.raises(RuntimeError, match="provenance violation"):
        verify_laya_provenance()


def test_changed_imported_bytes_are_rejected(monkeypatch, tmp_path):
    import shutil
    from types import ModuleType
    from workstation.system1.provenance import EXPECTED_SUBTREE_DIR
    shutil.copytree(EXPECTED_SUBTREE_DIR / "laya", tmp_path / "laya")
    (tmp_path / "laya" / "router.py").write_text("# changed runtime")
    module = ModuleType("laya")
    module.__file__ = str(tmp_path / "laya" / "__init__.py")
    module.__version__ = "0.3.23"
    monkeypatch.setitem(sys.modules, "laya", module)
    with pytest.raises(RuntimeError, match="provenance violation"):
        verify_laya_provenance()
