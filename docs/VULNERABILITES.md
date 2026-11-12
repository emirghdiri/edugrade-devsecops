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
| Bonus 1 | En-têtes de sécurité absents | `docker/nginx.conf:4`, `app/__init__.py:64` | A05 Security Misconfiguration | ZAP baseline | [30](preuves/captures/30-app-b1-entetes-avant.png) |
| Bonus 2 | XSS réfléchi | `app/templates/teacher/students.html:45-46` | A03 Injection (CWE-79) | Semgrep, ZAP | [29](preuves/captures/29-app-b2-xss-avant.png), [09](preuves/captures/09-semgrep.png) |
| V5 | NetworkPolicy trop permissive (sortie Internet du backend) | `terraform/cluster/network.tf` (policy `backend`) | A05 Security Misconfiguration | Trivy config (KUBE-0002), test de segmentation | [preuves 9x](preuves/corrvulnecicd/INDEX.md) |

La faille V5 (mauvaise configuration IaC du cluster) est introduite en Partie 2, dans
`terraform/cluster/`.

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
- **Correctif** : fait (branche `fix/idor`) — `app/student.py` : si le rôle est étudiant et que `student_id` n'est pas le sien, réponse **403** et événement `access_denied` (`reason=owner`) ; enseignants et administrateur gardent l'accès à tous les étudiants.
- **Preuve après** : job CI `security-tests` : `tests/security/test_idor.py` vert ; voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md).

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
  - `q = %' UNION SELECT id, name, password_hash FROM users --` → 15 lignes, dont les
    9 hachages scrypt de tous les comptes, administrateur compris (colonne « E-mail »).
  ```bash
  pytest -m security tests/security/test_sqli.py   # échoue sur v0.1-vulnerable
  ```
- **Détection** : Semgrep (`formatted-sql-query`, `sqlalchemy-execute-raw-query`),
  Bandit (B608), ZAP (scan actif), test `tests/security/test_sqli.py`.
- **Preuve avant** : [27-app-v2-sqli-tautologie-avant.png](preuves/captures/27-app-v2-sqli-tautologie-avant.png),
  [28-app-v2-sqli-union-avant.png](preuves/captures/28-app-v2-sqli-union-avant.png),
  [logs/27-app-v2-sqli-avant.txt](preuves/logs/27-app-v2-sqli-avant.txt),
  [09-semgrep.png](preuves/captures/09-semgrep.png), [10-bandit.png](preuves/captures/10-bandit.png).
- **Correctif** : fait (branche `fix/sqli`) — `app/teacher.py` : requête paramétrée (`ILIKE %s` + paramètre lié), jokers LIKE échappés ; l'événement `suspicious_input` reste journalisé.
- **Preuve après** : jobs CI `security-tests` (`tests/security/test_sqli.py` vert), `sast` (plus de constat Semgrep ERROR) et `dast` (plus d'alerte ZAP « SQL Injection ») ; voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md).

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
- **Correctif** : fait (branche `fix/secrets`) — `app/config.py` ne contient plus aucun secret : `SECRET_KEY` et `POSTGRES_PASSWORD` viennent uniquement de l'environnement (`.env`, GitHub Secrets `APP_SECRET_KEY` / `POSTGRES_PASSWORD`, Secret Kubernetes) et l'application refuse de démarrer sans `SECRET_KEY`. **Rotation** : les anciennes valeurs ne sont plus utilisées nulle part ; un cookie forgé avec l'ancienne clé est refusé (preuve 70). **Historique** : non réécrit (`main` interdit le force push) ; exception Gitleaks limitée aux deux empreintes exactes du commit `f78fd00` (`.gitleaksignore`), justifiée dans `docs/POLITIQUE_BLOCAGE.md`.
- **Preuve après** : job CI `secrets` (Gitleaks) vert ; preuve 70 : cookie forgé avec l'ancienne clé → HTTP 302 vers `/login` ; voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md).

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
- **Correctif** : fait (branche `fix/pyyaml`) — `requirements.txt` : `PyYAML==6.0.3` ; `app/config.py` : `yaml.safe_load` au lieu de `yaml.full_load` (aucune construction d'objet Python, même si un YAML externe était chargé un jour).
- **Preuve après** : jobs CI `dependencies` (Trivy fs) et `image` (Trivy image) : plus de CVE-2020-14343 ; voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md).

## V5 — NetworkPolicy trop permissive : sortie Internet du backend

- **Emplacement** : `terraform/cluster/network.tf`, ressource
  `kubernetes_network_policy.backend`, bloc `egress` vers `ip_block 0.0.0.0/0`.
- **Cause** : en plus du flux légitime backend → db:5432, la politique ouvre la
  sortie du backend vers **toute adresse IP** (« pour les mises à jour »). Elle
  annule l'effet du `default-deny-all` pour le composant le plus exposé.
- **Impact** : un backend compromis (injection SQL V2, clé de session V3,
  dépendance vulnérable V4) peut **exfiltrer** la base ou ouvrir un canal de
  commande vers l'extérieur ; la segmentation ne limite plus la fuite.
- **OWASP** : A05:2021 Security Misconfiguration (CWE-284, contrôle d'accès réseau).
- **Reproduire** :
  ```bash
  trivy config --severity HIGH,CRITICAL terraform/cluster   # KUBE-0002 (HIGH)
  scripts/k8s_segmentation_test.sh                          # backend -> 1.1.1.1:443 autorisé
  ```
- **Détection** : job CI `iac` (Trivy config, règle KUBE-0002 « Network policy
  allows unrestricted egress to any IP address ») ; test de segmentation.
  Limite constatée : la règle n'examine que le **premier** bloc `egress` ; placé
  en second, le même bloc passe inaperçu. D'où la défense en profondeur (test de
  segmentation exécuté sur le cluster réel).
- **Preuve avant** : voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md), section k3s.
- **Correctif** : _à venir (branche `fix/v5-egress`)_ — suppression du bloc
  `0.0.0.0/0` : le backend ne sort plus que vers la base (et le DNS).
- **Preuve après** : _à venir_.

## Bonus 1 — En-têtes de sécurité HTTP absents

- **Emplacement** : `docker/nginx.conf:4` (reverse proxy) et `app/__init__.py:64`
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
- **Correctif** : fait (branche `fix/security-headers`) — `docker/nginx.conf` : `add_header ... always` pour Content-Security-Policy stricte (pas de script, pas de style en ligne, `frame-ancestors 'none'`), X-Frame-Options `DENY`, X-Content-Type-Options `nosniff`, Referrer-Policy `no-referrer`, Permissions-Policy, Cross-Origin-Opener/Resource/Embedder-Policy. Vérifié sans violation CSP dans Chromium. HSTS sera posé là où TLS est terminé (Ingress k3s).
- **Preuve après** : job CI `dast` : plus d'alerte ZAP « CSP Header Not Set », « Missing Anti-clickjacking Header », « X-Content-Type-Options Header Missing » ; voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md).

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
- **Correctif** : fait (branche `fix/xss`) — suppression du filtre `|safe` dans `app/templates/teacher/students.html` : l'échappement automatique de Jinja s'applique ; test de non-régression `tests/security/test_xss.py`.
- **Preuve après** : jobs CI `dast` (plus d'alerte ZAP « Cross Site Scripting »), `sast` (plus de `template-unescaped-with-safe`) et `security-tests` ; voir [corrvulnecicd](preuves/corrvulnecicd/INDEX.md).

