#!/usr/bin/env python
"""Extract text from the source PDF with pdftotext, if available."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF = REPO_ROOT / "sources" / "original" / "bergner-spichtinger-2026.pdf"
OUT = REPO_ROOT / "sources" / "extracted" / "raw"


def main() -> None:
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext not found on PATH")
    OUT.mkdir(parents=True, exist_ok=True)
    for mode, flag in [("layout", "-layout"), ("raw", "-raw")]:
        target = OUT / f"bergner-spichtinger-2026.{mode}.txt"
        subprocess.run(["pdftotext", flag, str(PDF), str(target)], check=True)
        print(f"wrote {target.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
