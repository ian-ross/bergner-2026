#!/usr/bin/env python
"""Inspect saved publisher HTML for extractable article structure.

Safe to re-run. Writes JSON/text summaries into sources/extracted/raw/.
"""
from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[3]
HTML = REPO_ROOT / "sources" / "original" / "bergner-spichtinger-2026.html"
OUT = REPO_ROOT / "sources" / "extracted" / "raw"


def text(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split())


def meta(soup: BeautifulSoup, name: str) -> list[str]:
    return [tag.get("content", "") for tag in soup.find_all("meta", attrs={"name": name})]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(HTML.read_text(errors="replace"), "lxml")

    equation_like = []
    for idx, tag in enumerate(soup.find_all(["div", "section", "table", "span", "p"]), start=1):
        classes = " ".join(tag.get("class", []))
        if any(token in classes.lower() for token in ["disp-formula", "equation", "formula"]):
            equation_like.append({
                "index": idx,
                "name": tag.name,
                "id": tag.get("id"),
                "class": classes,
                "text": text(tag)[:2000],
                "math_count": len(tag.find_all("math")),
            })

    figures = []
    for idx, fig in enumerate(soup.find_all("figure"), start=1):
        images = [img.get("src") for img in fig.find_all("img")]
        figures.append({"index": idx, "id": fig.get("id"), "images": images, "caption": text(fig)[:2000]})

    tables = []
    for idx, tbl in enumerate(soup.find_all("table"), start=1):
        tables.append({"index": idx, "id": tbl.get("id"), "class": " ".join(tbl.get("class", [])), "text": text(tbl)[:4000]})

    headings = [{"name": h.name, "id": h.get("id"), "text": text(h)} for h in soup.find_all(["h1", "h2", "h3", "h4"])]

    summary = {
        "html_file": str(HTML.relative_to(REPO_ROOT)),
        "title_tag": text(soup.title) if soup.title else None,
        "citation_title": meta(soup, "citation_title"),
        "citation_author": meta(soup, "citation_author"),
        "citation_publication_date": meta(soup, "citation_publication_date"),
        "citation_journal_title": meta(soup, "citation_journal_title"),
        "citation_doi": meta(soup, "citation_doi"),
        "citation_pdf_url": meta(soup, "citation_pdf_url"),
        "math_tags": len(soup.find_all("math")),
        "mathjax_mentions": HTML.read_text(errors="replace").lower().count("mathjax"),
        "equation_like_blocks": len(equation_like),
        "figures": len(figures),
        "tables": len(tables),
        "headings": headings,
        "equation_like": equation_like,
        "figures_detail": figures,
        "tables_detail": tables,
    }

    (OUT / "html_inspection.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (OUT / "equation_blocks.txt").write_text("\n\n".join(
        f"[{item['index']}] id={item['id']} class={item['class']} math_count={item['math_count']}\n{item['text']}"
        for item in equation_like
    ))
    print(json.dumps({k: summary[k] for k in ["citation_title", "citation_author", "math_tags", "equation_like_blocks", "figures", "tables"]}, indent=2))


if __name__ == "__main__":
    main()
