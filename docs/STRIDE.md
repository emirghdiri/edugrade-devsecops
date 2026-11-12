# Modèle de menaces STRIDE — EduGrade (version finale)

Ce modèle couvre EduGrade tel qu'il est livré (`v1.0-secure`) : application Flask
derrière Nginx, base PostgreSQL, déployée sur k3s par un pipeline GitHub Actions.
Pour chaque menace : le scénario, la faille du projet qui l'illustrait, la
mesure en place et la preuve. Toutes les données sont fictives.

## Périmètre et frontières de confiance

```
 Internet ─▶ [F1] Traefik (Ingress) ─▶ [F2] frontend Nginx ─▶ [F3] backend Flask ─▶ [F4] PostgreSQL
                                                                     │
 Développeurs ─▶ [F5] GitHub (PR) ─▶ [F6] GitHub Actions ─▶ [F7] GHCR ─▶ [F8] k3s (admission Kyverno)
                                                                     │
                                        journaux JSON ─▶ Alloy ─▶ Loki ─▶ Grafana (alertes)
```

| Frontière | Ce qui la traverse | Contrôle principal |
|-----------|-------------------|--------------------|
| F1 Internet → cluster | requêtes HTTP des utilisateurs | Ingress unique, en-têtes de sécurité, NetworkPolicy « frontend » |
| F2-F3 proxy → application | requêtes authentifiées | session signée, CSRF, contrôle de rôle et d'appartenance côté serveur |
| F3-F4 application → base | requêtes SQL | requêtes paramétrées, NetworkPolicy « db » (backend seul) |
| F5-F6 code → pipeline | commits, PR | PR obligatoire, 1 approbation, check `build-test`, 9 contrôles bloquants |
| F7-F8 registre → cluster | images | digest immuable, signature Cosign vérifiée par Kyverno |

## Actifs

| Actif | Sensibilité |
|-------|-------------|
| Notes des étudiants | confidentialité, intégrité (fictives, mais traitées comme réelles) |
| Comptes et hachages de mots de passe (scrypt) | confidentialité |
| `SECRET_KEY` (signature des sessions) | confidentialité critique : sa fuite permet d'usurper tout compte |
| Mot de passe PostgreSQL | confidentialité |
| Image applicative et pipeline | intégrité (chaîne d'approvisionnement) |
| Journaux de sécurité | intégrité, disponibilité (enquête) |

## Menaces

### S — Usurpation d'identité (Spoofing)

| Menace | Faille illustrée | Mesures | Preuve |
|--------|------------------|---------|--------|
| Forger un cookie de session enseignant avec une clé lue dans le dépôt | **V3** (clé en dur) | clé uniquement dans l'environnement (Secret Kubernetes généré par Terraform, GitHub Secret) ; rotation ; Gitleaks bloquant sur tout l'historique | corrvulnecicd 43, 68-70 |
| Deviner un mot de passe (force brute) | — | hachage scrypt ; événement `login_failed` ; **alerte Grafana** > 5 échecs / 5 min ; confinement par blocage IP (plan de réponse) | 98-100 |
| Usurper l'IP source dans les journaux | IP de Traefik journalisée | `TRUSTED_PROXY_COUNT` (2 en k3s) ; Traefik remplace `X-Forwarded-For` d'un client | 102-104, `tests/test_proxy.py` |
| Faire passer une image pour celle du pipeline | — | Cosign keyless (OIDC GitHub, journal Rekor) ; Kyverno n'admet que `ci.yml` sur develop/main | 81, 97 |

### T — Altération (Tampering)

| Menace | Faille illustrée | Mesures | Preuve |
|--------|------------------|---------|--------|
| Modifier ou lire la base par injection SQL | **V2** | requêtes paramétrées ; Semgrep (ERROR) et ZAP (High) bloquants ; test `test_sqli.py` | 41-42, 47, 62-63 |
| Exécuter du JavaScript dans la session d'un enseignant (modifier des notes) | **Bonus 2** (XSS) | échappement Jinja (plus de `\|safe`), CSP `script-src 'none'` ; ZAP bloquant ; test `test_xss.py` | 47, 64-67 |
| Requêtes forgées depuis un autre site | — | jeton CSRF sur tous les POST, cookie `SameSite=Lax` | tests fonctionnels |
| Exécution de code via un YAML malveillant | **V4** (PyYAML 5.3.1) | PyYAML 6.0.3 + `yaml.safe_load` ; Trivy fs/image bloquants | 44-45, 71-72 |
| Image modifiée entre le scan et le déploiement | — | image construite une fois, scannée, publiée par **digest**, signée ; Kyverno vérifie le digest | 81, 85 |
| Code non relu sur `main` | — | protection de branche (PR, approbation, `build-test`, pas de force push) déclarée par Terraform | Partie 1, 04-05 |

### R — Répudiation (Repudiation)

| Menace | Mesures | Preuve |
|--------|---------|--------|
| Nier une action (modification de note, suppression de compte) | journaux JSON horodatés : `grade_*`, `user_*`, `subject_*` avec `user_id`, `role`, `route`, `ip` ; collecte Alloy → Loki (rétention 72 h) | 99-100 |
| Nier une tentative d'accès | `access_denied`, `login_failed`, `suspicious_input`, `csrf_failed` journalisés même quand l'action est refusée | 61, 99 |
| Nier une livraison | historique git (merge commits de PR), runs GitHub Actions, entrées Rekor des signatures | 80-86 |

### I — Divulgation d'information (Information disclosure)

| Menace | Faille illustrée | Mesures | Preuve |
|--------|------------------|---------|--------|
| Un étudiant lit les notes d'un autre | **V1** (IDOR) | contrôle d'appartenance côté serveur, 403 + `access_denied` ; alerte IDOR | 41, 60-61, 98-99 |
| Exfiltration de la base par un backend compromis | **V5** (sortie `0.0.0.0/0`) | NetworkPolicy backend limitée à `db:5432` ; Trivy config (KUBE-0002) bloquant ; test de segmentation | 93-97, 101 |
| Accès direct à la base depuis le frontend | — | `default-deny` + NetworkPolicy « db » (backend seul) | 97 |
| Secrets dans les journaux CI ou les preuves | Bandit affichait les secrets V3 | sortie Bandit sans valeur ; `--redact` Gitleaks ; masquage des captures | 48, 51-52 |
| Fuite par le navigateur (clickjacking, Referer, MIME) | **Bonus 1** | CSP stricte, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP/CORP/COEP | 66-67 |

### D — Déni de service (Denial of service)

| Menace | Mesures |
|--------|---------|
| Épuisement des ressources du nœud par un pod | `requests`/`limits` mémoire sur tous les pods ; `client_max_body_size 1m` (Nginx) ; `proxy_read_timeout 30s` |
| Indisponibilité non détectée | sondes `readiness`/`liveness` (`/healthz` vérifie la base) ; Prometheus/Alertmanager |
| Pipeline bloqué par du bruit | seuils calibrés (`docs/POLITIQUE_BLOCAGE.md`) : HIGH/CRITICAL avec correctif, ZAP High ; exceptions limitées et datées |

Risque résiduel : pas de limitation de débit applicative sur `/login` ; atténué par
l'alerte de force brute et le blocage IP au niveau de Traefik (plan de réponse).

### E — Élévation de privilèges (Elevation of privilege)

| Menace | Mesures | Preuve |
|--------|---------|--------|
| Un étudiant accède aux fonctions enseignant / administrateur | `role_required` côté serveur, `access_denied` journalisé | tests `test_roles.py` |
| Évasion de conteneur depuis l'application | conteneurs non-root (UID fixe), système de fichiers en lecture seule, `drop: [ALL]`, seccomp `RuntimeDefault`, pas de jeton de compte de service ; Pod Security `restricted` + Kyverno | 97 |
| Déployer un pod privilégié ou root | Kyverno (CEL) + PSA refusent `privileged`, `allowPrivilegeEscalation`, root, `latest`, registres non autorisés | 97 |
| Modifier la configuration du dépôt | collaboratrice en droit `push` (pas admin), configuration déclarée en Terraform | Partie 1 |

## Risques résiduels et acceptés

| Risque | Décision | Justification |
|--------|----------|---------------|
| Dépôt public (Trivy GIT-0001) | accepté jusqu'au 2027-06-30 | protection de branche gratuite, données fictives (`.trivyignore.yaml`) |
| Commits non signés (GIT-0004) | accepté jusqu'au 2027-06-30 | compensé par PR + approbation + CI |
| Anciennes valeurs V3 dans l'historique git | accepté | valeurs révoquées (rotation prouvée) ; `main` interdit la réécriture |
| Vulnérabilités Debian sans correctif dans l'image de base | surveillé | `--ignore-unfixed`, visibles dans la SBOM, image reconstruite à chaque livraison |
| Pas de limitation de débit sur `/login` | à traiter | alerte + blocage IP en attendant (middleware Traefik `rateLimit`) |
| Limite de la règle Trivy KUBE-0002 (premier bloc `egress` seulement) | compensé | test de segmentation sur le cluster réel |
