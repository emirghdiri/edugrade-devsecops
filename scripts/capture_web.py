"""Capture une page web publique (par exemple un run GitHub Actions) en PNG.

Usage : python scripts/capture_web.py <url> <sortie.png> [--full] [--selector CSS]

Playwright headless, 1440x900, aucune session ni jeton : seules les pages
publiques sont capturées. Mêmes bibliothèques Chromium que render_terminal.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("out")
    parser.add_argument("--full", action="store_true", help="page entière")
    parser.add_argument("--selector", help="ne capturer que cet élément")
    parser.add_argument("--wait", type=int, default=2500, help="attente après chargement (ms)")
    args = parser.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="fr-FR", color_scheme="light")
        # « load » puis attente fixe : certaines pages (GitHub) gardent des
        # connexions ouvertes et n'atteignent jamais « networkidle ».
        page.goto(args.url, wait_until="load", timeout=120_000)
        page.wait_for_timeout(args.wait)
        if args.selector:
            page.locator(args.selector).first.screenshot(path=args.out)
        else:
            page.screenshot(path=args.out, full_page=args.full)
        browser.close()
    print(f"capture : {args.out}")


if __name__ == "__main__":
    main()
