"""Rend un journal texte en image PNG façon terminal (Playwright, headless).

Usage : python scripts/render_terminal.py <journal.txt> <sortie.png> [titre]
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

MAX_LINES = 400  # au-delà, la sortie est tronquée (le journal .txt reste complet)

TEMPLATE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<style>
  body {{ margin: 0; background: #1e1f22; }}
  .win {{ display: inline-block; min-width: 900px; max-width: 1400px;
          background: #0d1117; border-radius: 8px; margin: 16px;
          box-shadow: 0 6px 24px rgba(0,0,0,.5); overflow: hidden; }}
  .bar {{ background: #2d333b; padding: 8px 12px; display: flex; gap: 8px;
          align-items: center; font: 13px system-ui, sans-serif; color: #adbac7; }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
  .title {{ margin-left: 12px; }}
  pre {{ margin: 0; padding: 14px 18px; color: #d1d7e0; white-space: pre-wrap;
         word-break: break-all;
         font: 13px/1.45 "DejaVu Sans Mono", "Liberation Mono", monospace; }}
  .meta {{ color: #768390; }}
  .cmd {{ color: #6cb6ff; font-weight: bold; }}
  .rc0 {{ color: #57ab5a; }}
  .rcx {{ color: #e5534b; }}
</style></head>
<body><div class="win" id="win">
  <div class="bar">
    <span class="dot" style="background:#ff5f56"></span>
    <span class="dot" style="background:#ffbd2e"></span>
    <span class="dot" style="background:#27c93f"></span>
    <span class="title">{title}</span>
  </div>
  <pre>{body}</pre>
</div></body></html>
"""


def colorize(line: str) -> str:
    esc = html.escape(line)
    if line.startswith("# "):
        return f'<span class="meta">{esc}</span>'
    if line.startswith("$ "):
        return f'<span class="cmd">{esc}</span>'
    if line.startswith("[code de retour"):
        cls = "rc0" if line.strip().endswith(": 0]") else "rcx"
        return f'<span class="{cls}">{esc}</span>'
    return esc


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else src.stem

    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > MAX_LINES:
        hidden = len(lines) - MAX_LINES
        lines = lines[: MAX_LINES - 1] + [f"… ({hidden} lignes tronquées, voir {src.name})", lines[-1]]

    page_html = TEMPLATE.format(title=html.escape(title), body="\n".join(colorize(l) for l in lines))

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 800}, device_scale_factor=1)
            page.set_content(page_html)
            page.locator("#win").screenshot(path=str(dst))
            browser.close()
    except Exception as exc:  # noqa: BLE001 - message court, le journal .txt reste la preuve
        first = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        print(f"rendu PNG impossible : {first}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
