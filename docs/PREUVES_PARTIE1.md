# Preuves — Partie 1 (fondations, Terraform, application vulnérable, Docker)

Récapitulatif destiné au rapport. Le détail de chaque preuve (commande exacte,
sortie complète, code de retour) est dans [`docs/preuves/INDEX.md`](preuves/INDEX.md).
Aucune valeur de secret ni de jeton ne figure dans les preuves (masquage
automatique par `scripts/capture_cmd.sh`).

## 1. Dépôt provisionné par Terraform

| Exigence (cahier §6.3, §6.4) | Preuve |
|------------------------------|--------|
| Dépôt, `main` + `develop` déclarés en code | [04 plan](preuves/captures/04-terraform-plan.png), [05 apply](preuves/captures/05-terraform-apply.png) |
| Protection de `main` : PR, 1 relecture, check `build-test`, ni force push ni suppression | [05 apply](preuves/captures/05-terraform-apply.png), capture manuelle M03 |
| Binôme collaboratrice (droit `push`) | [05 apply](preuves/captures/05-terraform-apply.png), capture manuelle M04 |
| GitHub Secrets créés depuis `terraform.tfvars` non versionné | [04 plan](preuves/captures/04-terraform-plan.png) (`(sensitive value)`), capture manuelle M05 |
| État et variables jamais versionnés | `.gitignore` (`*.tfstate*`, `*.tfvars`, `.terraform/`) |
| Code formaté et valide | [02 fmt](preuves/captures/02-terraform-fmt.png), [03 validate](preuves/captures/03-terraform-validate.png) |

Choix : dépôt **public** (protection de branche gratuite, toutes les données sont
fictives) ; `enforce_admins = false` pour permettre le commit initial.
Limite : les valeurs des secrets sont présentes dans l'état local `terraform.tfstate`
(le provider n'offre pas d'attribut en écriture seule) ; ce fichier n'est jamais versionné.

## 2. Application fonctionnelle

| Exigence (cahier §2) | Preuve |
|----------------------|--------|
| Connexion des deux rôles | [20](preuves/captures/20-app-connexion-avant.png), [11 pytest](preuves/captures/11-pytest-fonctionnels.png) |
| Étudiant : consultation de ses notes (matière, note, date) | [21](preuves/captures/21-app-etudiant-mes-notes-avant.png) |
| Enseignant : liste, recherche, ajout et modification de notes | [22](preuves/captures/22-app-enseignant-liste-avant.png), [23](preuves/captures/23-app-recherche-avant.png), [24](preuves/captures/24-app-ajout-note-formulaire-avant.png), [25](preuves/captures/25-app-ajout-note-resultat-avant.png) |
| Accès par rôle vérifié côté serveur | [11 pytest](preuves/captures/11-pytest-fonctionnels.png) (`test_roles.py`) |
| Mots de passe hachés (werkzeug/scrypt) | `app/seed.py` ; les hachages exposés par V2 ([28](preuves/captures/28-app-v2-sqli-union-avant.png)) montrent le format `scrypt:` |
| Journaux JSON (`login_failed`, `access_denied`, `suspicious_input`, `grade_created`, `grade_updated`) sans mot de passe ni note | [18](preuves/captures/18-journaux-json-securite.png), tests `test_login_failed_is_logged_without_password` et `test_teacher_updates_grade` |

## 3. Failles volontaires (état « avant »)

| Faille | Démonstration | Détection outillée |
|--------|---------------|--------------------|
| V1 IDOR | [26](preuves/captures/26-app-v1-idor-avant.png) | [12 pytest security](preuves/captures/12-pytest-securite-echec-attendu.png) |
| V2 Injection SQL | [27](preuves/captures/27-app-v2-sqli-tautologie-avant.png), [28](preuves/captures/28-app-v2-sqli-union-avant.png) | [09 Semgrep](preuves/captures/09-semgrep.png), [10 Bandit](preuves/captures/10-bandit.png), [12 pytest security](preuves/captures/12-pytest-securite-echec-attendu.png) |
| V3 Secrets en dur | — | [07 Gitleaks](preuves/captures/07-gitleaks-detect.png), [10 Bandit](preuves/captures/10-bandit.png) |
| V4 PyYAML 5.3.1 (CVE-2020-14343) | — | [08 Trivy fs](preuves/captures/08-trivy-fs.png), [17 Trivy image](preuves/captures/17-trivy-image.png) |
| Bonus 1 En-têtes absents | [30](preuves/captures/30-app-b1-entetes-avant.png) | ZAP baseline (Partie 2) |
| Bonus 2 XSS réfléchi | [29](preuves/captures/29-app-b2-xss-avant.png) | [09 Semgrep](preuves/captures/09-semgrep.png), ZAP (Partie 2) |

Description complète (cause, impact, OWASP, reproduction) : [`docs/VULNERABILITES.md`](VULNERABILITES.md).

## 4. Conteneurs

| Exigence (cahier §6.1) | Preuve |
|------------------------|--------|
| Dockerfile multi-stage, `python:3.12-slim`, sans outil de build | `docker/Dockerfile`, [16](preuves/captures/16-docker-run-id-nonroot.png) (ni pip ni gcc) |
| Utilisateur non-root à UID fixe | [15](preuves/captures/15-docker-compose-exec-id.png), [16](preuves/captures/16-docker-run-id-nonroot.png) |
| `.dockerignore` excluant `.git`, `.env`, `*.tfstate`, `terraform/`, `tests/` | `.dockerignore` |
| Compose : Nginx + Flask + PostgreSQL, healthchecks, réseau interne | [13](preuves/captures/13-docker-compose-up.png), [14](preuves/captures/14-docker-compose-ps.png) |
| Scan d'image | [17](preuves/captures/17-trivy-image.png) (rapport : V4 + paquets de l'OS de base) |

Durcissement supplémentaire du Compose : `read_only`, `cap_drop: [ALL]`,
`no-new-privileges`, réseau `backend` interne (la base n'a ni port publié ni accès
sortant), socket de contrôle Gunicorn désactivé.

Limites observées : `trivy image` signale des vulnérabilités HIGH dans les paquets
Debian de l'image de base, pour la plupart sans correctif publié (« affected ») ;
leur traitement (image de base plus récente ou distroless, exceptions justifiées)
relève de la politique de blocage de la Partie 2. Le scanner de secrets de Trivy ne
signale rien dans l'image alors que V3 y est embarquée (`app/config.py`) : ses règles
visent des formats de jetons connus, pas une clé générique. C'est Gitleaks qui porte
la détection de V3 ; « aucun secret trouvé par Trivy » ne signifie donc pas « aucun
secret dans l'image ».

## 5. Tests

- `pytest -m "not security"` : 29 tests fonctionnels verts — [11](preuves/captures/11-pytest-fonctionnels.png).
- `pytest -m security` : 4 échecs **attendus** sur `v0.1-vulnerable` (V1, V2) —
  [12](preuves/captures/12-pytest-securite-echec-attendu.png). Ils seront activés
  dans la CI après les corrections `fix/idor` et `fix/sqli`.

## 6. Captures manuelles à réaliser

Voir la liste M01 à M10 dans [`docs/preuves/INDEX.md`](preuves/INDEX.md#captures-manuelles-navigateur).
