# Vulnérabilités volontaires — EduGrade `v0.1-vulnerable`

Ce document recense les failles **introduites volontairement** dans la version
`v0.1-vulnerable` d'EduGrade, à des fins pédagogiques. Chaque faille est signalée
dans le code par un commentaire `VULN-<id> (volontaire, voir docs/VULNERABILITES.md)`
et a été introduite dans un commit dédié.

Toutes les données sont fictives. Les valeurs secrètes de V3 ne sont reproduites ni
ici ni dans les preuves (masquées `****MASQUÉ****`).

## Synthèse

| ID | Faille | Emplacement | OWASP Top 10 2021 | Détectée par | Preuve « avant » |
|----|--------|-------------|-------------------|--------------|------------------|
| V1 | IDOR sur les notes | `app/student.py:42-43` | A01 Broken Access Control | test pytest `tests/security/test_idor.py`, journaux | [26](preuves/captures/26-app-v1-idor-avant.png), [12](preuves/captures/12-pytest-securite-echec-attendu.png) |
| V2 | Injection SQL (recherche) | `app/teacher.py:20-22` | A03 Injection | Semgrep, Bandit, ZAP, test pytest `tests/security/test_sqli.py` | [27](preuves/captures/27-app-v2-sqli-tautologie-avant.png), [28](preuves/captures/28-app-v2-sqli-union-avant.png), [09](preuves/captures/09-semgrep.png), [10](preuves/captures/10-bandit.png) |
| V3 | Secrets écrits en dur | `app/config.py:22-24` | A07 Identification and Authentication Failures (CWE-798) | Gitleaks, Bandit | [07](preuves/captures/07-gitleaks-detect.png) |
| V4 | Dépendance vulnérable (PyYAML 5.3.1) | `requirements.txt:5-6`, utilisée dans `app/config.py:14-17` | A06 Vulnerable and Outdated Components | Trivy fs, Trivy image | [08](preuves/captures/08-trivy-fs.png), [17](preuves/captures/17-trivy-image.png) |
| Bonus 1 | En-têtes de sécurité absents | `docker/nginx.conf:4`, `app/__init__.py:66` | A05 Security Misconfiguration | ZAP baseline | [30](preuves/captures/30-app-b1-entetes-avant.png) |
| Bonus 2 | XSS réfléchi | `app/templates/teacher/students.html:45-46` | A03 Injection (CWE-79) | Semgrep, ZAP | [29](preuves/captures/29-app-b2-xss-avant.png), [09](preuves/captures/09-semgrep.png) |

La faille V5 (mauvaise configuration IaC du cluster) relève de la Partie 2.

---

## V1 — IDOR (Insecure Direct Object Reference)

- **Emplacement** : `app/student.py:42-43`, route `GET /grades/<student_id>`.
- **Cause** : la route est protégée par `@login_required` uniquement. Elle ne vérifie
  pas que l'étudiant connecté est le propriétaire des notes demandées
  (`session["user_id"] == student_id`). L'identifiant est un entier séquentiel,
  donc trivial à énumérer.
- **Impact** : tout étudiant connecté lit les notes (et l'e-mail) de n'importe quel
  autre étudiant : atteinte à la confidentialité. Aucun événement `access_denied`
  n'est journalisé, la tentative passe inaperçue.
- **OWASP** : A01:2021 Broken Access Control (CWE-639).
- **Reproduire** :
  1. Se connecter en tant que `lina.bensalah@edugrade.test` / `lina2026`.
  2. « Mes notes » ouvre `/grades/3` (son propre identifiant).
  3. Ouvrir `/grades/4` : les notes de Youssef Trabelsi s'affichent (HTTP 200).
  ```bash
  pytest -m security tests/security/test_idor.py   # échoue sur v0.1-vulnerable
  ```
- **Détection** : ZAP détecte mal ce type de faille ; elle est prouvée par le test
  scripté `tests/security/test_idor.py` rejoué avant et après correction, et par
  l'absence puis la présence de l'événement `access_denied` dans les journaux.
- **Preuve avant** : [26-app-v1-idor-avant.png](preuves/captures/26-app-v1-idor-avant.png),
  [logs/26-app-v1-idor-avant.txt](preuves/logs/26-app-v1-idor-avant.txt),
  [12-pytest-securite-echec-attendu.png](preuves/captures/12-pytest-securite-echec-attendu.png).
- **Correctif** : _à venir (branche `fix/idor`)_ — contrôle d'appartenance côté
  serveur (403 + journal `access_denied`), l'enseignant gardant l'accès à tous.
- **Preuve après** : _à venir_.

## V2 — Injection SQL dans la recherche d'étudiants

- **Emplacement** : `app/teacher.py:20-22`, fonction `search_students`, route
  `GET /teacher/students?q=`.
- **Cause** : le terme saisi est inséré dans la requête par f-string
  (`... WHERE role = 'student' AND name ILIKE '%{term}%'`) au lieu d'être passé
  en paramètre lié.
- **Impact** : un enseignant (ou un attaquant ayant volé sa session) contourne le
  filtre et lit des données arbitraires de la base, par exemple les hachages de
  mots de passe de tous les comptes via `UNION` ; selon les droits du compte
  PostgreSQL, modification ou destruction de données. L'événement
  `suspicious_input` est bien journalisé, mais la requête est exécutée.
- **OWASP** : A03:2021 Injection (CWE-89).
- **Reproduire** (connecté en enseignant `claire.dubois@edugrade.test` / `claire2026`) :
  - `q = ' OR '1'='1` → les 6 étudiants sont renvoyés au lieu de 0 ;
  - `q = %' UNION SELECT id, name, password_hash FROM users --` → 14 lignes, dont les
    8 hachages scrypt des comptes (colonne « E-mail »).
  ```bash
  pytest -m security tests/security/test_sqli.py   # échoue sur v0.1-vulnerable
  ```
- **Détection** : Semgrep (`formatted-sql-query`, `sqlalchemy-execute-raw-query`),
  Bandit (B608), ZAP (scan actif), test `tests/security/test_sqli.py`.
- **Preuve avant** : [27-app-v2-sqli-tautologie-avant.png](preuves/captures/27-app-v2-sqli-tautologie-avant.png),
  [28-app-v2-sqli-union-avant.png](preuves/captures/28-app-v2-sqli-union-avant.png),
  [logs/27-app-v2-sqli-avant.txt](preuves/logs/27-app-v2-sqli-avant.txt),
  [09-semgrep.png](preuves/captures/09-semgrep.png), [10-bandit.png](preuves/captures/10-bandit.png).
- **Correctif** : _à venir (branche `fix/sqli`)_ — requête paramétrée
  (`ILIKE %s` + paramètre), le journal `suspicious_input` restant actif.
- **Preuve après** : _à venir_.

## V3 — Secrets écrits en dur

- **Emplacement** : `app/config.py:22-24` (constantes `SECRET_KEY` et `DB_PASSWORD`).
- **Cause** : la clé de signature des sessions Flask est une constante du code (la
  variable d'environnement est ignorée) et le mot de passe PostgreSQL a une valeur
  par défaut écrite en dur. Les deux valeurs sont dans l'historique git.
- **Impact** : quiconque lit le dépôt (public) peut forger un cookie de session
  signé et usurper n'importe quel compte, y compris enseignant ; le mot de passe de
  base est réutilisable si la variable d'environnement n'est pas fournie. Le retrait
  du code ne suffit pas : la valeur reste dans l'historique.
- **OWASP** : A07:2021 Identification and Authentication Failures (CWE-798,
  identifiants en dur) ; également A02 (clé cryptographique exposée).
- **Reproduire** : `gitleaks detect --source . --redact -v` → 2 fuites
  `generic-api-key` dans `app/config.py`.
- **Détection** : Gitleaks (bloquant dans le pipeline), Bandit (B105).
- **Preuve avant** : [07-gitleaks-detect.png](preuves/captures/07-gitleaks-detect.png),
  [10-bandit.png](preuves/captures/10-bandit.png).
- **Correctif** : relève de la Partie 2 — remplacer la valeur (rotation), lire
  `SECRET_KEY` depuis l'environnement (GitHub Secret `APP_SECRET_KEY`, Secret
  Kubernetes), purger l'historique (`git filter-repo`) puis vérifier que Gitleaks
  ne détecte plus rien.

## V4 — Dépendance ancienne et vulnérable : PyYAML 5.3.1

- **Emplacement** : `requirements.txt:5-6` (`PyYAML==5.3.1`) ; la bibliothèque est
  réellement utilisée par `app/config.py:14-17` (`yaml.full_load`) pour charger
  `app/settings.yaml` (liste des matières).
- **Cause** : version épinglée ancienne, non mise à jour.
- **Impact** : CVE-2020-14343 (CRITICAL, CVSS 9.8) — exécution de code arbitraire
  lors du chargement d'un YAML malveillant avec `full_load` / `FullLoader`
  (correctif incomplet de CVE-2020-1747). Ici le fichier chargé est local et sous
  contrôle de l'équipe, ce qui limite l'exploitabilité ; le risque devient direct
  si un YAML d'origine externe est un jour chargé. La vulnérabilité est embarquée
  dans l'image publiée.
- **OWASP** : A06:2021 Vulnerable and Outdated Components.
- **Reproduire** : `trivy fs --scanners vuln --severity HIGH,CRITICAL .` →
  `PyYAML 5.3.1 CVE-2020-14343 CRITICAL, corrigée en 5.4`.
- **Détection** : Trivy fs (dépendances), Trivy image (image construite).
- **Preuve avant** : [08-trivy-fs.png](preuves/captures/08-trivy-fs.png),
  [17-trivy-image.png](preuves/captures/17-trivy-image.png).
- **Correctif** : relève de la Partie 2 — mise à jour vers une version corrigée
  (PyYAML ≥ 5.4, idéalement 6.x) et `yaml.safe_load`.

## Bonus 1 — En-têtes de sécurité HTTP absents

- **Emplacement** : `docker/nginx.conf:4` (reverse proxy) et `app/__init__.py:66`
  (Flask) : aucun des deux n'ajoute d'en-tête de sécurité.
- **Cause** : configuration par défaut, sans `Content-Security-Policy`,
  `X-Frame-Options`, `X-Content-Type-Options` ni `Referrer-Policy`.
- **Impact** : aucune défense en profondeur côté navigateur : le XSS (Bonus 2)
  n'est pas freiné par une CSP, l'application peut être intégrée dans une iframe
  (clickjacking), le navigateur peut deviner les types MIME, l'URL complète
  (avec le terme recherché) fuit dans l'en-tête `Referer`.
- **OWASP** : A05:2021 Security Misconfiguration.
- **Reproduire** : `curl -sI http://localhost:8080/login` → seuls `Server`,
  `Content-Type`, `Content-Length`, `Vary`, `Date`, `Connection`.
- **Détection** : ZAP baseline (alertes « CSP Header Not Set », « Missing
  Anti-clickjacking Header », « X-Content-Type-Options Header Missing »).
- **Preuve avant** : [30-app-b1-entetes-avant.png](preuves/captures/30-app-b1-entetes-avant.png),
  [logs/30-app-b1-entetes-avant.txt](preuves/logs/30-app-b1-entetes-avant.txt).
- **Correctif** : _à venir (branche `fix/security-headers`)_ — en-têtes ajoutés dans
  Nginx (`add_header ... always`).
- **Preuve après** : _à venir_.

## Bonus 2 — XSS réfléchi dans la recherche

- **Emplacement** : `app/templates/teacher/students.html:45-46`.
- **Cause** : le terme recherché est réaffiché avec le filtre Jinja `|safe`, qui
  désactive l'échappement automatique.
- **Impact** : un lien piégé (`/teacher/students?q=<script>…</script>`) envoyé à un
  enseignant exécute du JavaScript dans sa session : actions en son nom (ajout ou
  modification de notes, le jeton CSRF étant lisible dans la page), défiguration,
  hameçonnage. Le cookie de session est `HttpOnly` et ne peut pas être lu
  directement.
- **OWASP** : A03:2021 Injection (CWE-79, Cross-Site Scripting).
- **Reproduire** : connecté en enseignant, ouvrir
  ``/teacher/students?q=<script>document.body.insertAdjacentHTML(`afterbegin`,`<b>XSS</b>`)</script>``
  → le script s'exécute (bannière rouge dans la capture).
- **Détection** : Semgrep (`template-unescaped-with-safe`), ZAP (scan actif,
  « Cross Site Scripting (Reflected) ») ; `suspicious_input` (motif `script_tag`)
  dans les journaux.
- **Preuve avant** : [29-app-b2-xss-avant.png](preuves/captures/29-app-b2-xss-avant.png),
  [logs/29-app-b2-xss-avant.txt](preuves/logs/29-app-b2-xss-avant.txt),
  [09-semgrep.png](preuves/captures/09-semgrep.png).
- **Correctif** : _à venir (branche `fix/xss`)_ — supprimer `|safe` (échappement
  Jinja par défaut).
- **Preuve après** : _à venir_.
