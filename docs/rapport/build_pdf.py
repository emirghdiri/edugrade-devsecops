"""Génère docs/rapport/EduGrade_Rapport_DevSecOps.pdf.

Usage : .venv/bin/python docs/rapport/build_pdf.py   (Playwright + pypdf)

  1. cover.html  -> page de garde, sans en-tête ni numéro ;
  2. rapport.html -> corps, premier rendu pour localiser la page de chaque titre ;
  3. numéros de page inscrits dans le sommaire, second rendu ;
  4. assemblage page de garde + corps.
"""

from __future__ import annotations

import io
import re
import unicodedata
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).resolve().parent
OUT = HERE / "EduGrade_Rapport_DevSecOps.pdf"
MARGIN = {"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"}
FONT = "font-family:'DejaVu Sans',sans-serif;font-size:7.4pt;color:#5b6475;width:100%;padding:0 18mm;display:flex;justify-content:space-between"
HEADER = f"""<div style="{FONT}"><span>EduGrade — Rapport de projet DevSecOps</span><span>TEK-UP University · ING-5-SSIR</span></div>"""
FOOTER = f"""<div style="{FONT}"><span>Sécurisation de bout en bout d'une application web</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>"""


def norm(text: str) -> str:
    # NFKC décompose les ligatures typographiques (ﬁ, ﬃ…) produites par la police.
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", "", text).lower()


def render_body(page) -> bytes:
    return page.pdf(format="A4", print_background=True, display_header_footer=True,
                    header_template=HEADER, footer_template=FOOTER, margin=MARGIN)


def locate(pdf_bytes: bytes, titles: list[tuple[str, str]], start: int) -> dict[str, int]:
    pages = [norm(p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf_bytes)).pages]
    found, cursor = {}, start
    for ref, title in titles:
        key = norm(title)
        for i in range(cursor, len(pages)):
            if key in pages[i]:
                found[ref] = i + 1  # numérotation du corps (le résumé est la page 1)
                cursor = i
                break
    return found


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        cover = browser.new_page()
        cover.goto((HERE / "cover.html").as_uri(), wait_until="load")
        cover_pdf = cover.pdf(format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})

        body = browser.new_page()
        body.goto((HERE / "rapport.html").as_uri(), wait_until="load")
        body.wait_for_timeout(1000)
        # Texte à localiser, dans l'ordre du sommaire : « Chapitre N » + titre pour
        # un chapitre, « N.M » + titre pour une section (évite les homonymes, par
        # exemple « Infrastructure as Code » cité dans un tableau du chapitre 1).
        titles = body.evaluate("""() => [...document.querySelectorAll('.toc .pg')].map(el => {
            const h = document.getElementById(el.dataset.ref);
            const scope = h.parentElement.classList.contains('chapter-head') ? h.parentElement : h;
            return [el.dataset.ref, scope.textContent.trim()];
        })""")
        first = render_body(body)
        start = 3  # après le résumé, le sommaire et le début de la liste des abréviations
        pages = locate(first, titles, start - 1)
        missing = [ref for ref, _ in titles if ref not in pages]
        if missing:
            raise SystemExit(f"titres introuvables dans le PDF : {missing}")
        body.evaluate("(pages) => document.querySelectorAll('.toc .pg').forEach(el => el.textContent = pages[el.dataset.ref])", pages)
        final = render_body(body)
        browser.close()

    writer = PdfWriter()
    for src in (cover_pdf, final):
        for p in PdfReader(io.BytesIO(src)).pages:
            writer.add_page(p)
    writer.add_metadata({"/Title": "EduGrade — Rapport de projet DevSecOps",
                         "/Author": "A. Ghdiri, A. Cheikhrouhou, O. Ben Othmen, N. Hadhri",
                         "/Subject": "Module DevSecOps — TEK-UP University"})
    with open(OUT, "wb") as fh:
        writer.write(fh)
    print(f"PDF : {OUT} ({len(writer.pages)} pages)")
    print("sommaire :", ", ".join(f"{r}={p}" for r, p in pages.items()))


if __name__ == "__main__":
    main()
