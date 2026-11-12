# Index des preuves — Partie 1

Chaque preuve est numérotée. Les journaux (`logs/*.txt`) contiennent la commande
exacte, sa sortie complète et son code de retour ; les captures (`captures/*.png`)
en sont le rendu « terminal » généré par `scripts/capture_cmd.sh`.
Les captures manuelles (pages web GitHub) sont à réaliser dans le navigateur et à
déposer sous le nom indiqué. Aucune valeur de secret ni jeton ne figure ici.

## Phase 0 — Prérequis

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| 00 | Versions des outils (git, gh, terraform, docker, python, gitleaks, trivy, semgrep, bandit, playwright) | [logs/00-prerequis.txt](logs/00-prerequis.txt) | [captures/00-prerequis.png](captures/00-prerequis.png) |

## Phase 1 — Dépôt créé par Terraform

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| 01 | `terraform init` : provider `integrations/github` 6.13.0 installé | [logs/01-terraform-init.txt](logs/01-terraform-init.txt) | [captures/01-terraform-init.png](captures/01-terraform-init.png) |
| 02 | `terraform fmt -check` : code formaté | [logs/02-terraform-fmt.txt](logs/02-terraform-fmt.txt) | [captures/02-terraform-fmt.png](captures/02-terraform-fmt.png) |
| 03 | `terraform validate` : configuration valide | [logs/03-terraform-validate.txt](logs/03-terraform-validate.txt) | [captures/03-terraform-validate.png](captures/03-terraform-validate.png) |
| 04 | `terraform plan` : 8 ressources à créer, secrets affichés `(sensitive value)` | [logs/04-terraform-plan.txt](logs/04-terraform-plan.txt) | [captures/04-terraform-plan.png](captures/04-terraform-plan.png) |
| 05 | `terraform apply` : 8 ressources créées, sorties sans secret | [logs/05-terraform-apply.txt](logs/05-terraform-apply.txt) | [captures/05-terraform-apply.png](captures/05-terraform-apply.png) |
| 06 | `git log --oneline --graph` : commits atomiques de la branche `feature/terraform-github` | [logs/06-git-log-terraform.txt](logs/06-git-log-terraform.txt) | [captures/06-git-log-terraform.png](captures/06-git-log-terraform.png) |

## Phases 3-4 — Application et failles volontaires (version vulnérable)

Les valeurs factices de V3 sont masquées (`****MASQUÉ****`) dans tous les journaux.

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| 07 | Gitleaks détecte V3 : 2 secrets (`generic-api-key`) dans `app/config.py` | [logs/07-gitleaks-detect.txt](logs/07-gitleaks-detect.txt) | [captures/07-gitleaks-detect.png](captures/07-gitleaks-detect.png) |
| 08 | Trivy fs détecte V4 : PyYAML 5.3.1, CVE-2020-14343 (CRITICAL, corrigée en 5.4) | [logs/08-trivy-fs.txt](logs/08-trivy-fs.txt) | [captures/08-trivy-fs.png](captures/08-trivy-fs.png) |
| 09 | Semgrep détecte V2 (`formatted-sql-query`, `sqlalchemy-execute-raw-query`) et Bonus 2 (`template-unescaped-with-safe`) | [logs/09-semgrep.txt](logs/09-semgrep.txt) | [captures/09-semgrep.png](captures/09-semgrep.png) |
| 10 | Bandit : V2 (B608) et V3 (B105) | [logs/10-bandit.txt](logs/10-bandit.txt) | [captures/10-bandit.png](captures/10-bandit.png) |
| 11 | pytest : 29 tests fonctionnels verts (connexion, rôles, notes, journaux, /healthz) | [logs/11-pytest-fonctionnels.txt](logs/11-pytest-fonctionnels.txt) | [captures/11-pytest-fonctionnels.png](captures/11-pytest-fonctionnels.png) |
| 12 | pytest `-m security` : 4 échecs attendus (V1 IDOR, V2 injection SQL) | [logs/12-pytest-securite-echec-attendu.txt](logs/12-pytest-securite-echec-attendu.txt) | [captures/12-pytest-securite-echec-attendu.png](captures/12-pytest-securite-echec-attendu.png) |

## Phase 5 — Docker

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| 13 | `docker compose up -d` : les trois services démarrent | [logs/13-docker-compose-up.txt](logs/13-docker-compose-up.txt) | [captures/13-docker-compose-up.png](captures/13-docker-compose-up.png) |
| 14 | `docker compose ps` : frontend, backend, db `healthy`, seul le port 8080 publié | [logs/14-docker-compose-ps.txt](logs/14-docker-compose-ps.txt) | [captures/14-docker-compose-ps.png](captures/14-docker-compose-ps.png) |
| 15 | `docker compose exec … id` : backend UID 10001, Nginx UID 101 (non-root) | [logs/15-docker-compose-exec-id.txt](logs/15-docker-compose-exec-id.txt) | [captures/15-docker-compose-exec-id.png](captures/15-docker-compose-exec-id.png) |
| 16 | `docker run … id` : image non-root (`User=10001:10001`), ni pip ni gcc embarqués | [logs/16-docker-run-id-nonroot.txt](logs/16-docker-run-id-nonroot.txt) | [captures/16-docker-run-id-nonroot.png](captures/16-docker-run-id-nonroot.png) |
| 17 | `trivy image` (rapport) : V4 dans l'image, HIGH de l'OS de base, aucun secret détecté par Trivy | [logs/17-trivy-image.txt](logs/17-trivy-image.txt) | [captures/17-trivy-image.png](captures/17-trivy-image.png) |
| 18 | Journaux JSON du backend : `login_success`, `login_failed`, `access_denied`, `suspicious_input`, `grade_created` | [logs/18-journaux-json-securite.txt](logs/18-journaux-json-securite.txt) | [captures/18-journaux-json-securite.png](captures/18-journaux-json-securite.png) |

## Phase 7 — Application (captures Playwright, version vulnérable « avant »)

Générées par `scripts/capture_app.py --phase avant` sur l'instance Docker Compose.

| N° | Ce que la preuve montre | Capture | Journal |
|----|-------------------------|---------|---------|
| 20 | Page de connexion | [captures/20-app-connexion-avant.png](captures/20-app-connexion-avant.png) | |
| 21 | Étudiante : « Mes notes » (matière, note, date, moyenne) | [captures/21-app-etudiant-mes-notes-avant.png](captures/21-app-etudiant-mes-notes-avant.png) | |
| 22 | Enseignante : liste des étudiants | [captures/22-app-enseignant-liste-avant.png](captures/22-app-enseignant-liste-avant.png) | |
| 23 | Recherche par nom (« Martin ») | [captures/23-app-recherche-avant.png](captures/23-app-recherche-avant.png) | |
| 24 | Ajout de note : formulaire | [captures/24-app-ajout-note-formulaire-avant.png](captures/24-app-ajout-note-formulaire-avant.png) | |
| 25 | Ajout de note : résultat | [captures/25-app-ajout-note-resultat-avant.png](captures/25-app-ajout-note-resultat-avant.png) | |
| 26 | **V1 IDOR** : l'étudiante lit les notes d'un autre étudiant (HTTP 200) | [captures/26-app-v1-idor-avant.png](captures/26-app-v1-idor-avant.png) | [logs/26-app-v1-idor-avant.txt](logs/26-app-v1-idor-avant.txt) |
| 27 | **V2 injection SQL** : `' OR '1'='1` renvoie les 6 étudiants | [captures/27-app-v2-sqli-tautologie-avant.png](captures/27-app-v2-sqli-tautologie-avant.png) | [logs/27-app-v2-sqli-avant.txt](logs/27-app-v2-sqli-avant.txt) |
| 28 | **V2 injection SQL** : `UNION` exfiltre les hachages de mots de passe | [captures/28-app-v2-sqli-union-avant.png](captures/28-app-v2-sqli-union-avant.png) | [logs/27-app-v2-sqli-avant.txt](logs/27-app-v2-sqli-avant.txt) |
| 29 | **Bonus 2 XSS** : script injecté exécuté (bannière rouge) | [captures/29-app-b2-xss-avant.png](captures/29-app-b2-xss-avant.png) | [logs/29-app-b2-xss-avant.txt](logs/29-app-b2-xss-avant.txt) |
| 30 | **Bonus 1** : en-têtes de sécurité absents (cookie masqué) | [captures/30-app-b1-entetes-avant.png](captures/30-app-b1-entetes-avant.png) | [logs/30-app-b1-entetes-avant.txt](logs/30-app-b1-entetes-avant.txt) |
| 31 | Administratrice : liste des comptes (filtres par rôle, modifier, supprimer) après création d'un enseignant | [captures/31-app-admin-utilisateurs-avant.png](captures/31-app-admin-utilisateurs-avant.png) | |
| 32 | Administratrice : formulaire de création d'un compte (rôle, nom, e-mail, mot de passe initial) | [captures/32-app-admin-ajout-utilisateur-avant.png](captures/32-app-admin-ajout-utilisateur-avant.png) | |
| 33 | Enseignante : gestion des matières (ajout, modification, suppression ; notes et moyenne par matière) | [captures/33-app-matieres-avant.png](captures/33-app-matieres-avant.png) | |
| 34 | Enseignante : confirmation avant suppression d'une note | [captures/34-app-suppression-note-confirmation-avant.png](captures/34-app-suppression-note-confirmation-avant.png) | |

### Captures manuelles (navigateur)

| N° | URL | Ce qu'il faut montrer | Fichier attendu |
|----|-----|-----------------------|-----------------|
| M01 | https://github.com/emirghdiri/edugrade-devsecops | Page d'accueil du dépôt (public, description, README) | `captures/M01-depot.png` |
| M02 | https://github.com/emirghdiri/edugrade-devsecops/branches | Branches `main` (défaut, protégée) et `develop` | `captures/M02-branches.png` |
| M03 | https://github.com/emirghdiri/edugrade-devsecops/settings/branches | Règle de protection de `main` : PR, 1 approbation, check `build-test`, pas de force push ni suppression | `captures/M03-protection-main.png` |
| M04 | https://github.com/emirghdiri/edugrade-devsecops/settings/access | Collaboratrice `arijcheikhrouhou` (droit Write) | `captures/M04-collaboratrice.png` |
| M05 | https://github.com/emirghdiri/edugrade-devsecops/settings/secrets/actions | Secrets `APP_SECRET_KEY` et `POSTGRES_PASSWORD` (noms seulement, valeurs jamais visibles) | `captures/M05-secrets-actions.png` |
| M06 | https://github.com/emirghdiri/edugrade-devsecops/pulls?q=is%3Apr | PR `feature/terraform-github` → `develop` | `captures/M06-pr-terraform.png` |
| M07 | https://github.com/emirghdiri/edugrade-devsecops/pulls?q=is%3Apr | PR `feature/app-core` et `feature/docker` | `captures/M07-pr-app-docker.png` |
| M08 | https://github.com/emirghdiri/edugrade-devsecops/network | Graphe des branches (`main`, `develop`, `feature/*`) | `captures/M08-graphe-branches.png` |
| M09 | https://github.com/emirghdiri/edugrade-devsecops/tags | Tag annoté `v0.1-vulnerable` (après fusion des PR) | `captures/M09-tag-v0.1-vulnerable.png` |
| M10 | http://localhost:8080 | Application dans le navigateur (optionnel, en complément des captures Playwright) | `captures/M10-app-navigateur.png` |
