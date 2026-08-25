from __future__ import annotations

import argparse
from pathlib import Path


class CompatError(RuntimeError):
    pass


OLD = """    try {\n      entry.view.webContents.close()\n    } catch {\n      try {\n        entry.view.webContents.destroy()\n      } catch {\n        // Already gone.\n      }\n    }\n"""

NEW = """    if (!entry.view.webContents.isDestroyed()) {\n      entry.view.webContents.close()\n    }\n"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    target = args.root.resolve() / "apps" / "desktop" / "electron" / "workstation-browser-runtime.ts"
    if not target.exists():
        raise CompatError(f"Workstation Electron runtime not found: {target}")

    text = target.read_text(encoding="utf-8")
    if NEW in text:
        print("OK: Electron WebContents lifecycle compatibility already applied.")
        return 0

    count = text.count(OLD)
    if count != 1:
        raise CompatError(f"Expected one WebContents.destroy compatibility anchor, found {count}")

    target.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
    print("Applied Electron WebContents lifecycle compatibility fix.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompatError as exc:
        raise SystemExit(f"ERROR: {exc}")
