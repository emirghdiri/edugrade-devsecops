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

### Captures manuelles (navigateur)

| N° | URL | Ce qu'il faut montrer | Fichier attendu |
|----|-----|-----------------------|-----------------|
| M01 | https://github.com/emirghdiri/edugrade-devsecops | Page d'accueil du dépôt (public, description, README) | `captures/M01-depot.png` |
| M02 | https://github.com/emirghdiri/edugrade-devsecops/branches | Branches `main` (défaut, protégée) et `develop` | `captures/M02-branches.png` |
| M03 | https://github.com/emirghdiri/edugrade-devsecops/settings/branches | Règle de protection de `main` : PR, 1 approbation, check `build-test`, pas de force push ni suppression | `captures/M03-protection-main.png` |
| M04 | https://github.com/emirghdiri/edugrade-devsecops/settings/access | Collaboratrice `arijcheikhrouhou` (droit Write) | `captures/M04-collaboratrice.png` |
| M05 | https://github.com/emirghdiri/edugrade-devsecops/settings/secrets/actions | Secrets `APP_SECRET_KEY` et `POSTGRES_PASSWORD` (noms seulement, valeurs jamais visibles) | `captures/M05-secrets-actions.png` |
| M06 | https://github.com/emirghdiri/edugrade-devsecops/pulls?q=is%3Apr | PR `feature/terraform-github` → `develop` | `captures/M06-pr-terraform.png` |
