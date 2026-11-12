"""Capture le tableau de bord « Sécurité EduGrade » et la liste des alertes Grafana.

Usage : GRAFANA_PASSWORD=... python scripts/capture_grafana.py <dossier de sortie> <préfixe>
Grafana doit être joignable sur http://localhost:3000 (port-forward).
Le mot de passe est lu dans l'environnement, jamais affiché.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"


def main() -> None:
    out, prefix = Path(sys.argv[1]), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, locale="fr-FR")
        page.set_default_timeout(120_000)
        page.goto(f"{BASE}/login", wait_until="domcontentloaded")
        page.fill("input[name=user]", "admin")
        page.fill("input[name=password]", os.environ["GRAFANA_PASSWORD"])
        page.click("button[type=submit]")
        page.wait_for_url(lambda u: "/login" not in u, timeout=30_000)

        # Grafana charge ses bundles JS lentement à travers le port-forward :
        # on attend un texte du contenu, pas un délai fixe.
        # Sans « kiosk » (les panneaux y sont rendus paresseusement) ; on laisse
        # le temps aux requêtes Loki de revenir avant la capture.
        page.goto(f"{BASE}/d/edugrade-securite?orgId=1&from=now-1h&to=now", timeout=120_000)
        page.get_by_text("Journal des événements de sécurité").first.wait_for(timeout=120_000)
        page.wait_for_timeout(45_000)
        page.screenshot(path=str(out / f"{prefix}-grafana-tableau-de-bord.png"), full_page=True)

        page.goto(f"{BASE}/alerting/list?search=EduGrade&view=list", timeout=120_000)
        page.get_by_text("Force brute").first.wait_for(timeout=120_000)
        page.wait_for_timeout(4000)
        page.screenshot(path=str(out / f"{prefix}-grafana-alertes.png"), full_page=True)
        browser.close()
    print("captures Grafana enregistrées")


if __name__ == "__main__":
    main()
