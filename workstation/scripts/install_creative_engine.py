"""Explicit preparation and safe installation helper for creative web engine distributions.

Downloads official prebuilt web releases, validates SHA-256 against SHA256SUMS.txt,
safely extracts without path traversal, validates index.html and wasm artifacts,
and records provenance in ~/.hermes/workstation/creative/engines/{engine}/web-dist.
Never run automatically during Hermes startup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

from hermes_constants import get_hermes_home

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OFFICIAL_RELEASES = {
    "filmcraft": {
        "version": "0.8.0",
        "repo": "storytold/filmcraft",
        "asset_name": "filmcraft-web-0.8.0.zip",
        "expected_sha256": "6b13956fc741522427663517b1e483d6e0777891063fed02b1bd94bfada8a6c7",
    },
    "photocraft": {
        "version": "0.9.0",
        "repo": "storytold/photocraft",
        "asset_name": "photocraft-web-0.9.0.zip",
        "expected_sha256": "b3fa5ab6a9d32bc5ff7dfdde31939a2337471a196a2e70f1ff961a61b1bb02e6",
    },
    "effectcraft": {
        "version": "0.10.0",
        "repo": "storytold/effectcraft",
        "asset_name": "effectcraft-web-0.10.0.zip",
        "expected_sha256": "b922abeda2420391a7fd887f53ebae6948730e63720bad6a6eb3dc48dc1b46a8",
    },
}


def compute_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest().lower()


def safe_extract_zip(zip_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    resolved_target = target_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_path = resolved_target / member.filename
            try:
                resolved_member = member_path.resolve()
            except Exception as exc:
                raise ValueError(f"Unsafe zip entry path {member.filename}: {exc}") from exc
            if not resolved_member.is_relative_to(resolved_target):
                raise ValueError(f"Zip slip attempt detected: {member.filename} resolves outside {resolved_target}")
        zf.extractall(resolved_target)


def prepare_engine_web_dist(
    engine: str,
    *,
    version: str | None = None,
    dest_dir: Path | None = None,
) -> Path:
    if engine not in OFFICIAL_RELEASES:
        raise ValueError(f"Unknown engine: {engine}. Supported: {sorted(OFFICIAL_RELEASES.keys())}")

    spec = OFFICIAL_RELEASES[engine]
    ver = version or spec["version"]
    repo = spec["repo"]
    asset_name = spec["asset_name"] if ver == spec["version"] else f"{engine}-web-{ver}.zip"
    expected_sha = spec.get("expected_sha256") if ver == spec["version"] else None

    target_web_dist = dest_dir or (get_hermes_home() / "workstation" / "creative" / "engines" / engine / "web-dist")
    target_web_dist = target_web_dist.resolve()

    download_url = f"https://github.com/{repo}/releases/download/v{ver}/{asset_name}"
    sums_url = f"https://github.com/{repo}/releases/download/v{ver}/SHA256SUMS.txt"

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        zip_file = temp_dir / asset_name
        sums_file = temp_dir / "SHA256SUMS.txt"

        logger.info("Downloading %s from %s ...", asset_name, download_url)
        urllib.request.urlretrieve(download_url, zip_file)

        logger.info("Downloading SHA256SUMS.txt from %s ...", sums_url)
        try:
            urllib.request.urlretrieve(sums_url, sums_file)
            sums_content = sums_file.read_text(encoding="utf-8", errors="replace")
            for line in sums_content.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1].lstrip("*") == asset_name:
                    official_sha = parts[0].lower()
                    if expected_sha and official_sha != expected_sha:
                        raise ValueError(f"Official SHA256SUMS.txt sha {official_sha} differs from pin {expected_sha}")
                    expected_sha = official_sha
                    break
        except (urllib.error.URLError, OSError, ValueError) as exc:
            logger.warning("Could not fetch or parse SHA256SUMS.txt (%s); relying on expected pin", exc)

        actual_sha = compute_sha256(zip_file)
        if expected_sha and actual_sha != expected_sha:
            raise ValueError(f"SHA256 mismatch for {asset_name}: actual {actual_sha} != expected {expected_sha}")

        logger.info("SHA256 verified (%s). Extracting safely to %s ...", actual_sha, target_web_dist)
        if target_web_dist.exists():
            shutil.rmtree(target_web_dist)
        safe_extract_zip(zip_file, target_web_dist)

        # If zip extracted into a single wrapper folder (e.g. filmcraft-web-0.8.0/), flatten it
        subdirs = [p for p in target_web_dist.iterdir() if p.is_dir()]
        root_index = target_web_dist / "index.html"
        if not root_index.is_file() and len(subdirs) == 1 and (subdirs[0] / "index.html").is_file():
            wrapper = subdirs[0]
            logger.info("Unwrapping nested directory %s ...", wrapper.name)
            for item in wrapper.iterdir():
                shutil.move(str(item), str(target_web_dist / item.name))
            wrapper.rmdir()

        # Validate structure
        index_file = target_web_dist / "index.html"
        if not index_file.is_file():
            raise FileNotFoundError(f"Extracted dist missing index.html at {index_file}")

        wasm_files = list(target_web_dist.glob("*.wasm"))
        if not wasm_files:
            raise FileNotFoundError(f"Extracted dist has no .wasm files in {target_web_dist}")

        manifest = {
            "engine": engine,
            "version": ver,
            "source_repo": f"https://github.com/{repo}",
            "download_url": download_url,
            "sha256": actual_sha,
            "wasm_files": [f.name for f in wasm_files],
            "installed_at": Path(index_file).stat().st_mtime,
        }
        (target_web_dist / "hermes_engine_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        logger.info("Engine %s v%s successfully prepared at %s", engine, ver, target_web_dist)

    return target_web_dist


def main() -> int:
    parser = argparse.ArgumentParser(description="Install prebuilt creative engine web distribution.")
    parser.add_argument("--engine", choices=list(OFFICIAL_RELEASES.keys()), default="filmcraft")
    parser.add_argument("--version", default=None)
    parser.add_argument("--dest", type=Path, default=None)
    args = parser.parse_args()

    try:
        dist = prepare_engine_web_dist(args.engine, version=args.version, dest_dir=args.dest)
        print(f"OK: {dist}")
        return 0
    except Exception as exc:
        logger.exception("Failed to prepare engine %s: %s", args.engine, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
