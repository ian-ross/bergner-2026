#!/usr/bin/env python
"""Build/update a coarse source extraction manifest from inspected artifacts."""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "sources" / "extracted" / "provenance.yaml"

MANIFEST = {
    "paper": {
        "title": "Ice clouds as nonlinear oscillators",
        "authors": ["Hannah Bergner", "Peter Spichtinger"],
        "year": 2026,
        "journal": "Chaos: An Interdisciplinary Journal of Nonlinear Science",
        "doi": "10.1063/5.0297531",
    },
    "sources": {
        "publisher_html": {
            "source_file": "sources/original/bergner-spichtinger-2026.html",
            "ancillary_files": "sources/original/bergner-spichtinger-2026_files/",
            "role": "primary semantic source for equations, section text, captions, and figures",
            "quality": "high for equation discovery: saved publisher HTML includes MathML/MathJax and equation-like display blocks",
        },
        "pdf": {
            "source_file": "sources/original/bergner-spichtinger-2026.pdf",
            "role": "visual ground truth and fallback prose source",
            "quality": "born-digital PDF; pdftotext output useful for prose but math must be checked",
        },
    },
    "tools": {
        "pdftotext": {
            "commands": [
                "pdftotext -layout bergner-spichtinger-2026.pdf sources/extracted/raw/bergner-spichtinger-2026.layout.txt",
                "pdftotext -raw bergner-spichtinger-2026.pdf sources/extracted/raw/bergner-spichtinger-2026.raw.txt",
            ]
        },
        "episodes/001-figure4-time-series/scripts/inspect_html.py": {
            "outputs": ["sources/extracted/raw/html_inspection.json", "sources/extracted/raw/equation_blocks.txt"]
        },
    },
    "equations": {
        "article_display_equations": {
            "source": "publisher_html",
            "source_file": "sources/original/bergner-spichtinger-2026.html",
            "paper_location": "throughout article; see sources/extracted/raw/equation_blocks.txt",
            "extraction_method": "BeautifulSoup discovery of publisher display-formula/equation blocks containing MathML/MathJax",
            "used_extract": "raw",
            "manually_checked_against_rendered_source": False,
            "confidence": "medium",
            "notes": "HTML has semantic math, but Phase 1 only performed spot inspection; model-critical equations must be checked against rendered HTML/PDF before Phase 2 implementation.",
        }
    },
    "tables": {},
    "figures": {
        "article_figures": {
            "source": "publisher_html ancillary files",
            "data_available": False,
            "reproduction_plan": "Use paper captions and displayed JPEGs as visual targets; no underlying figure data identified in saved files during Phase 1.",
        }
    },
    "cloud_or_api_tools_used": False,
}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(MANIFEST, sort_keys=False, allow_unicode=True))
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
