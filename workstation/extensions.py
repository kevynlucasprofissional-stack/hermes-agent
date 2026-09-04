from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Optional
import urllib.request
import zipfile

from hermes_constants import get_hermes_home

_log = logging.getLogger(__name__)

def get_extensions_dir() -> Path:
    """Resolve directory for installed Chrome extensions."""
    d = get_hermes_home() / "workstation" / "extensions"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ChromeExtensionManager:
    """Manager for discovering, downloading, unpacking and maintaining Chrome extensions."""

    CHROME_UPDATE_URL = (
        "https://clients2.google.com/service/update2/crx"
        "?response=redirect&prodversion=128.0.0.0&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc"
    )

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or get_extensions_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.storage_dir / "extensions.json"

    def extract_extension_id(self, input_str: str) -> str:
        """Extract a 32-character Chrome extension ID from a URL or raw ID string."""
        s = input_str.strip()
        # Direct 32-char ID
        if re.match(r"^[a-p]{32}$", s, re.IGNORECASE):
            return s.lower()

        # Match from webstore URL (e.g. /detail/.../cjpalhdlnbpafiamejdnhcphjbkeiagm)
        match = re.search(r"([a-p]{32})(?:[/?&#]|$)", s, re.IGNORECASE)
        if match:
            return match.group(1).lower()

        raise ValueError(f"Invalid Chrome Web Store extension ID or URL: '{input_str}'")

    def unpack_crx(self, crx_bytes: bytes, dest_dir: Path) -> Path:
        """Unpack CRX package by locating the underlying ZIP stream."""
        if not crx_bytes.startswith(b"Cr24"):
            raise ValueError("Not a valid CRX format (missing Cr24 magic signature)")

        # In both CRX2 and CRX3, the archive payload is a standard ZIP starting with PK\x03\x04
        zip_offset = crx_bytes.find(b"PK\x03\x04")
        if zip_offset == -1:
            raise ValueError("Failed to locate ZIP payload inside CRX archive")

        zip_data = crx_bytes[zip_offset:]
        dest_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            z.extractall(dest_dir)

        return dest_dir

    def download_crx(self, ext_id: str) -> bytes:
        """Download .crx bytes directly from Google Web Store update endpoint."""
        url = self.CHROME_UPDATE_URL.format(ext_id=ext_id)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return resp.read()

    def get_manifest(self, ext_dir: Path) -> dict[str, Any]:
        """Read and parse extension manifest.json."""
        manifest_path = ext_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {ext_dir}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_file.exists():
            return {"extensions": {}}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"extensions": {}}

    def _save_registry(self, data: dict[str, Any]) -> None:
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def install_from_bytes(self, ext_id: str, crx_bytes: bytes) -> dict[str, Any]:
        """Install extension from raw CRX bytes (useful for offline/tests)."""
        target_dir = self.storage_dir / ext_id
        self.unpack_crx(crx_bytes, target_dir)
        manifest = self.get_manifest(target_dir)

        name = manifest.get("name", ext_id)
        # Handle localized message __MSG_name__ fallback
        if name.startswith("__MSG_"):
            name = ext_id

        entry = {
            "id": ext_id,
            "name": name,
            "version": manifest.get("version", "1.0.0"),
            "description": manifest.get("description", ""),
            "path": str(target_dir),
            "enabled": True,
            "permissions": manifest.get("permissions", []),
            "options_page": manifest.get("options_page") or manifest.get("options_ui", {}).get("page"),
        }

        reg = self._load_registry()
        reg["extensions"][ext_id] = entry
        self._save_registry(reg)
        return entry

    def install_extension(self, identifier_or_url: str) -> dict[str, Any]:
        """Download, unpack and register a Chrome extension from webstore URL or ID."""
        ext_id = self.extract_extension_id(identifier_or_url)
        crx_bytes = self.download_crx(ext_id)
        return self.install_from_bytes(ext_id, crx_bytes)

    def list_installed_extensions(self) -> list[dict[str, Any]]:
        """List all registered extensions."""
        reg = self._load_registry()
        return list(reg.get("extensions", {}).values())

    def uninstall_extension(self, ext_id: str) -> bool:
        """Remove extension from disk and registry."""
        clean_id = ext_id.lower().strip()
        reg = self._load_registry()
        if clean_id not in reg.get("extensions", {}):
            return False

        del reg["extensions"][clean_id]
        self._save_registry(reg)

        target_dir = self.storage_dir / clean_id
        if target_dir.exists():
            import shutil
            shutil.rmtree(target_dir, ignore_errors=True)
        return True

    def get_options_url(self, ext_id: str) -> str | None:
        """Get the options page URL if declared in manifest."""
        clean_id = ext_id.lower().strip()
        reg = self._load_registry()
        ext = reg.get("extensions", {}).get(clean_id)
        if not ext:
            return None
        opt = ext.get("options_page")
        if opt:
            return f"chrome-extension://{clean_id}/{opt}"
        return f"chrome-extension://{clean_id}/options.html"
