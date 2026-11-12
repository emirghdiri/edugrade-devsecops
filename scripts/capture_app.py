"""Captures de l'application EduGrade avec Playwright (headless, 1280x800).

Usage :
    python scripts/capture_app.py [--base-url http://localhost:8080] [--phase avant|apres]

Prérequis : l'application tourne (docker compose up -d) avec les données de démonstration.
Produit docs/preuves/captures/<NN>-app-<sujet>-<phase>.png et un journal
docs/preuves/logs/<NN>-app-<sujet>-<phase>.txt pour les démonstrations de failles.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = ROOT / "docs" / "preuves" / "captures"
LOGS = ROOT / "docs" / "preuves" / "logs"

# Bibliothèques de Chromium extraites sans sudo (voir README, section « Captures »).
_deps = Path(os.environ.get("PLAYWRIGHT_DEPS_DIR", Path.home() / ".local/lib/playwright-deps"))
if _deps.is_dir() and str(_deps) not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{_deps}:{_deps}/nss:" + os.environ.get("LD_LIBRARY_PATH", "")
    os.execv(sys.executable, [sys.executable, *sys.argv])  # relance avec le bon chemin

from playwright.sync_api import Browser, Page, sync_playwright  # noqa: E402

ADMIN = ("nadia.mansour@edugrade.test", "nadia2026")
TEACHER = ("claire.dubois@edugrade.test", "claire2026")
STUDENT = ("lina.bensalah@edugrade.test", "lina2026")
VICTIM = "Youssef Trabelsi"

SQLI_TAUTOLOGY = "' OR '1'='1"
SQLI_UNION = "%' UNION SELECT id, name, password_hash FROM users --"
XSS_PAYLOAD = (
    "<script>document.body.insertAdjacentHTML(`afterbegin`,"
    "`<div id=\"xss-proof\" style=\"background:#b00020;color:#fff;padding:14px 20px;font:600 16px system-ui\">"
    "XSS exécuté : script injecté via le paramètre q (domaine ${location.host})</div>`)</script>"
)
SECURITY_HEADERS = [
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "strict-transport-security",
    "permissions-policy",
]


class Recorder:
    def __init__(self, phase: str) -> None:
        self.phase = phase
        self.files: list[str] = []
        CAPTURES.mkdir(parents=True, exist_ok=True)
        LOGS.mkdir(parents=True, exist_ok=True)

    def name(self, num: int, topic: str) -> str:
        return f"{num:02d}-app-{topic}-{self.phase}"

    def shot(self, page: Page, num: int, topic: str) -> None:
        path = CAPTURES / f"{self.name(num, topic)}.png"
        page.screenshot(path=str(path), full_page=True)
        self.files.append(str(path.relative_to(ROOT)))
        print(f"capture : {path.relative_to(ROOT)}")

    def log(self, num: int, topic: str, lines: list[str]) -> None:
        path = LOGS / f"{self.name(num, topic)}.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.files.append(str(path.relative_to(ROOT)))


def login(browser: Browser, base: str, creds: tuple[str, str]) -> Page:
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, locale="fr-FR")
    page = ctx.new_page()
    page.goto(f"{base}/login")
    page.fill("#email", creds[0])
    page.fill("#password", creds[1])
    page.click("main form.form button[type=submit]")
    page.wait_for_load_state("networkidle")
    return page


def search(page: Page, base: str, term: str):
    return page.goto(f"{base}/teacher/students?q={quote(term, safe='')}")


def rows(page: Page) -> int:
    return page.locator('[data-testid="student-row"]').count()


def student_ids(page: Page, base: str) -> dict[str, int]:
    page.goto(f"{base}/teacher/students")
    ids: dict[str, int] = {}
    for row in page.locator('[data-testid="student-row"]').all():
        name = row.locator('[data-testid="student-name"]').inner_text().strip()
        href = row.locator("a", has_text="Voir les notes").get_attribute("href") or ""
        ids[name] = int(re.search(r"/grades/(\d+)", href).group(1))
    return ids


def mask_cookies(headers: dict[str, str]) -> dict[str, str]:
    """Le cookie de session ne doit jamais figurer dans une preuve : on garde nom et attributs."""
    out = dict(headers)
    if "set-cookie" in out:
        out["set-cookie"] = re.sub(r"^([^=]+)=[^;]*", r"\1=****MASQUÉ****", out["set-cookie"], flags=re.M)
    return out


def headers_page(page: Page, url: str, status: int, headers: dict[str, str]) -> None:
    present = {k.lower(): v for k, v in headers.items()}
    rows_html = "".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td><code>{html.escape(v)}</code></td></tr>"
        for k, v in sorted(present.items())
    )
    checks = "".join(
        f"<tr class=\"{'ok' if h in present else 'ko'}\"><td><code>{h}</code></td>"
        f"<td>{'PRÉSENT' if h in present else 'ABSENT'}</td></tr>"
        for h in SECURITY_HEADERS
    )
    page.set_content(
        f"""<!doctype html><html lang="fr"><meta charset="utf-8"><style>
        body{{font:15px system-ui;margin:28px;color:#1f2933;background:#f5f7fb}}
        h1{{font-size:22px}} table{{border-collapse:collapse;background:#fff;margin:10px 0 26px;min-width:640px}}
        td,th{{border:1px solid #e2e8f0;padding:8px 12px;text-align:left}}
        .ok td:last-child{{color:#046c4e;font-weight:700}} .ko td:last-child{{color:#c81e1e;font-weight:700}}
        code{{font-size:13px}}</style>
        <h1>En-têtes de réponse HTTP — {html.escape(url)} (HTTP {status})</h1>
        <h2>En-têtes de sécurité attendus</h2><table><tr><th>En-tête</th><th>État</th></tr>{checks}</table>
        <h2>En-têtes reçus</h2><table><tr><th>Nom</th><th>Valeur</th></tr>{rows_html}</table></html>"""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Captures de l'application EduGrade")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--phase", choices=["avant", "apres"], default="avant")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    rec = Recorder(args.phase)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 20 — page de connexion
        anon = browser.new_context(viewport={"width": 1280, "height": 800}, locale="fr-FR").new_page()
        anon.goto(f"{base}/login")
        rec.shot(anon, 20, "connexion")

        # Enseignante : liste, recherche, ajout de note
        teacher = login(browser, base, TEACHER)
        ids = student_ids(teacher, base)
        rec.shot(teacher, 22, "enseignant-liste")
        search(teacher, base, "Martin")
        rec.shot(teacher, 23, "recherche")

        sarah = ids["Sarah Martin"]
        teacher.goto(f"{base}/teacher/grades/new?student_id={sarah}")
        teacher.select_option("#subject", "Systèmes")
        teacher.fill("#value", "16.5")
        teacher.fill("#date", "2026-11-10")
        teacher.locator("#date").evaluate("el => el.blur()")
        rec.shot(teacher, 24, "ajout-note-formulaire")
        teacher.click("main form.form button[type=submit]")  # pas le bouton Déconnexion de l'en-tête
        teacher.wait_for_load_state("networkidle")
        rec.shot(teacher, 25, "ajout-note-resultat")

        # Étudiante : ses notes, puis V1 (IDOR) sur les notes d'un autre étudiant
        student = login(browser, base, STUDENT)
        student.click("nav >> text=Mes notes")
        student.wait_for_load_state("networkidle")
        rec.shot(student, 21, "etudiant-mes-notes")

        victim_url = f"{base}/grades/{ids[VICTIM]}"
        resp = student.goto(victim_url)
        rec.shot(student, 26, "v1-idor")
        rec.log(26, "v1-idor", [
            f"# V1 IDOR — connectée en tant que {STUDENT[0]} (étudiante)",
            f"GET {victim_url}  -> HTTP {resp.status}",
            f"Notes de « {VICTIM} » affichées : {'OUI' if VICTIM in student.content() else 'NON'}",
        ])

        # V2 — injection SQL dans la recherche enseignant
        resp = search(teacher, base, SQLI_TAUTOLOGY)
        n_taut = rows(teacher)
        rec.shot(teacher, 27, "v2-sqli-tautologie")
        resp2 = search(teacher, base, SQLI_UNION)
        hashes = re.findall(r"(?:scrypt|pbkdf2)[^<\s]{0,12}", teacher.content())
        rec.shot(teacher, 28, "v2-sqli-union")
        rec.log(27, "v2-sqli", [
            "# V2 injection SQL — recherche enseignant /teacher/students?q=",
            f"q = {SQLI_TAUTOLOGY!r}  -> HTTP {resp.status}, lignes renvoyées : {n_taut}",
            f"q = {SQLI_UNION!r}  -> HTTP {resp2.status}, lignes renvoyées : {rows(teacher)}",
            f"Hachages de mots de passe visibles : {len(hashes)} (préfixes : {sorted(set(h.split('$')[0] for h in hashes))})",
        ])

        # Bonus 2 — XSS réfléchi
        dialogs: list[str] = []
        teacher.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        search(teacher, base, XSS_PAYLOAD)
        executed = teacher.locator("#xss-proof").count() > 0
        rec.shot(teacher, 29, "b2-xss")
        rec.log(29, "b2-xss", [
            "# Bonus 2 XSS réfléchi — /teacher/students?q=<script>…</script>",
            f"Script injecté exécuté dans la page : {'OUI' if executed else 'NON'}",
        ])

        # Bonus 1 — en-têtes de sécurité
        resp = anon.goto(f"{base}/login")
        headers = mask_cookies(resp.all_headers())
        headers_page(anon, f"{base}/login", resp.status, headers)
        rec.shot(anon, 30, "b1-entetes")
        rec.log(30, "b1-entetes", [f"# Bonus 1 — en-têtes de GET {base}/login (HTTP {resp.status})"]
                + [f"{k}: {v}" for k, v in sorted(headers.items())]
                + ["", "# En-têtes de sécurité"]
                + [f"{h}: {'PRÉSENT' if h in headers else 'ABSENT'}" for h in SECURITY_HEADERS])

        # Gestion (après les démonstrations, pour ne pas modifier les chiffres des failles)
        # Administrateur : création d'un compte enseignant puis liste des comptes
        admin = login(browser, base, ADMIN)
        admin.goto(f"{base}/admin/users/new?role=teacher")
        admin.fill("#name", "Samir Ayari")
        admin.fill("#email", f"samir.ayari.{args.phase}@edugrade.test")
        admin.fill("#password", "samir-initial-1")
        rec.shot(admin, 32, "admin-ajout-utilisateur")
        admin.click("main form.form button[type=submit]")
        admin.wait_for_load_state("networkidle")
        rec.shot(admin, 31, "admin-utilisateurs")

        # Enseignante : ajout d'une matière, puis confirmation de suppression d'une note
        teacher.goto(f"{base}/teacher/subjects")
        teacher.fill("#name", "Sécurité des applications")
        teacher.click("main form.inline-form button[type=submit]")
        teacher.wait_for_load_state("networkidle")
        rec.shot(teacher, 33, "matieres")
        teacher.goto(f"{base}/grades/{sarah}")
        teacher.locator('[data-testid="delete-grade"]').first.click()
        teacher.wait_for_load_state("networkidle")
        rec.shot(teacher, 34, "suppression-note-confirmation")

        browser.close()

    print(f"{len(rec.files)} fichiers produits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
