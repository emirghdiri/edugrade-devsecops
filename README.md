# EduGrade — DevSecOps

Portail web de gestion de notes servant de support au projet DevSecOps du module
ING-5-SSIR : application volontairement vulnérable, conteneurs durcis, Terraform,
pipeline de sécurité bloquant, Kubernetes (k3s) durci, DAST et détection.

> **Avertissement** : la version taguée `v0.1-vulnerable` contient des failles
> **volontaires** (voir [`docs/VULNERABILITES.md`](docs/VULNERABILITES.md)).
> Ne l'exposez jamais en dehors d'un poste de test. Toutes les données (noms,
> e-mails, notes, secrets) sont **fictives**.

## Fonctionnalités

| Rôle | Fonctionnalités |
|------|-----------------|
| Étudiant | Connexion ; consultation de ses notes (matière, note, date) |
| Enseignant | Connexion ; liste des étudiants ; recherche par nom ; ajout et modification de notes |

Les rôles sont contrôlés côté serveur. Les journaux applicatifs sont émis en JSON
sur la sortie standard (`login_success`, `login_failed`, `access_denied`,
`suspicious_input`, `grade_created`, `grade_updated`).

## Architecture

```
Navigateur ──HTTP:8080──▶ frontend (Nginx, non-root)
                              │  réseau « frontend »
                              ▼
                          backend (Flask + Gunicorn, UID 10001)
                              │  réseau « backend » (interne, sans accès extérieur)
                              ▼
                          db (PostgreSQL 16, volume persistant)
```

- **Backend** : Python 3.12, Flask (application factory, blueprints `auth`,
  `student`, `teacher`), psycopg 3, templates Jinja.
- **Frontend** : Nginx en reverse proxy (`nginxinc/nginx-unprivileged`).
- **Base** : PostgreSQL 16, tables `users` et `grades`, données de démonstration
  chargées au démarrage (`app/seed.py`).
- **Infrastructure** : le dépôt GitHub lui-même (branches, protection de `main`,
  collaboratrice, secrets Actions) est déclaré dans `terraform/github/`.

## Démarrage local (Docker Compose)

Prérequis : Docker et Docker Compose.

```bash
cp .env.example .env          # puis remplacer les valeurs factices
docker compose up -d --build
docker compose ps             # les trois services doivent être « healthy »
```

Application : <http://localhost:8080>

### Comptes de démonstration (fictifs)

Le mot de passe de chaque compte est son **prénom en minuscules sans accent suivi
de `2026`** (exemple : `lina2026`).

| Rôle | E-mail |
|------|--------|
| Enseignante | `claire.dubois@edugrade.test` |
| Enseignant | `karim.haddad@edugrade.test` |
| Étudiante | `lina.bensalah@edugrade.test` |
| Étudiant | `youssef.trabelsi@edugrade.test` |
| Étudiante | `sarah.martin@edugrade.test` |
| Étudiant | `omar.jaziri@edugrade.test` |
| Étudiante | `emma.lefevre@edugrade.test` |
| Étudiant | `mehdi.gharbi@edugrade.test` |

Arrêt : `docker compose down` (ajouter `-v` pour supprimer la base).

## Développement et tests

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

scripts/test_db.sh start           # PostgreSQL de test sur le port 5433
pytest -m "not security"           # tests fonctionnels
pytest -m security                 # tests de sécurité (échouent sur v0.1-vulnerable)
scripts/test_db.sh stop
```

Les tests marqués `security` vérifient l'absence d'IDOR et d'injection SQL : ils
échouent tant que les failles volontaires V1 et V2 sont présentes et sont activés
après leur correction.

## Preuves

Les preuves (journaux de commandes et captures) sont rangées dans
[`docs/preuves/`](docs/preuves/INDEX.md).

- `scripts/capture_cmd.sh <NN-description> '<commande>'` : exécute une commande,
  enregistre sa sortie (jetons masqués) et la rend en PNG façon terminal.
- `scripts/capture_app.py` : parcourt l'application avec Playwright (headless,
  1280x800) et capture les pages et les démonstrations de failles.

### Captures

Les captures utilisent Chromium via Playwright :

```bash
.venv/bin/python -m playwright install chromium
sudo .venv/bin/python -m playwright install-deps chromium
```

Sans accès `sudo`, les bibliothèques manquantes (NSS, NSPR, ALSA) peuvent être
extraites des paquets Ubuntu dans `~/.local/lib/playwright-deps` :
`scripts/capture_cmd.sh` et `scripts/capture_app.py` les utilisent automatiquement.

## Structure du dépôt

```
edugrade-devsecops/
├── app/                 # Flask : blueprints, templates Jinja, journaux JSON
├── tests/               # pytest : fonctionnels + tests/security
├── docker/              # Dockerfile, nginx.conf, entrypoint
├── docker-compose.yml
├── terraform/
│   └── github/          # dépôt, branches, protection, collaboratrice, secrets
├── k8s/                 # manifestes de l'application (Partie 2)
├── policies/            # règles Kyverno, Semgrep, Falco (Partie 2)
├── .github/workflows/   # pipeline CI/CD (Partie 2)
├── scripts/             # outils de capture et base de test
└── docs/                # failles, preuves, politique de blocage
```

## Organisation Git

- `main` : protégée, ne reçoit que des Pull Requests relues et vertes.
- `develop` : intégration ; toutes les branches de travail en partent et y
  reviennent par Pull Request.
- `feature/<sujet>` pour le travail, `fix/<faille>` pour les corrections.
- Tags : `v0.1-vulnerable` (avant correction), `v1.0-secure` (final).

## Membres

| Membre | Partie |
|--------|--------|
| Amir Ghdiri | Partie 1 : fondations, Terraform GitHub, application vulnérable, Docker |
| Arij Cheikhrouhou | Partie 2 : chaîne de sécurité CI/CD, déploiement k3s, DAST, observabilité |
