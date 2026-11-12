"""Génère docs/rapport/EduGrade_Rapport_DevSecOps.pdf à partir de rapport.html.

Usage : .venv/bin/python docs/rapport/build_pdf.py
Rendu Chromium (Playwright) : A4, en-tête et pied de page avec pagination.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "rapport.html"
OUT = HERE / "EduGrade_Rapport_DevSecOps.pdf"

HEADER = """<div style="font-size:7.5pt;color:#5b6475;width:100%;padding:0 16mm;
  display:flex;justify-content:space-between;font-family:'DejaVu Sans',sans-serif">
  <span>EduGrade — Rapport de projet DevSecOps</span><span>TEK-UP University · ING-5-SSIR</span></div>"""
FOOTER = """<div style="font-size:7.5pt;color:#5b6475;width:100%;padding:0 16mm;
  display:flex;justify-content:space-between;font-family:'DejaVu Sans',sans-serif">
  <span>A. Ghdiri · A. Cheikhrouhou · O. Ben Othmen · N. Hadhri</span>
  <span>Page <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>"""


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(SRC.as_uri(), wait_until="load")
        page.wait_for_timeout(1500)
        page.pdf(
            path=str(OUT),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=HEADER,
            footer_template=FOOTER,
            margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
            prefer_css_page_size=False,
        )
        browser.close()
    print(f"PDF : {OUT}")


if __name__ == "__main__":
    main()
