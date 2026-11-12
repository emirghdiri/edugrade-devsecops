# Politique de blocage du pipeline CI/CD

Ce document fixe, pour chaque outil du pipeline `.github/workflows/ci.yml`, ce qui
**bloque** la livraison et ce qui est seulement **rapporté**, avec la justification.

Principe général : **une faille exploitable connue bloque, le bruit ne bloque pas.**
Un seuil trop bas rend le pipeline rouge en permanence et pousse l'équipe à
l'ignorer ; un seuil trop haut laisse passer V1-V4. Les seuils ci-dessous sont
calibrés sur la version `v0.1-vulnerable` : chaque faille volontaire est
bloquée par au moins un contrôle.

## Ordre des contrôles

```
build-test ─┬─ security-tests ─┐
            ├─ sast ───────────┤
            ├─ secrets ────────┤
            ├─ dependencies ───┼─▶ publish (push GHCR, signature Cosign)
            ├─ iac ────────────┤      seulement sur develop/main, si TOUT est vert
            └─ image-scan ─────┘
                    └─▶ dast (Docker Compose + ZAP)
```

- `build-test` est le contrôle exigé par la protection de `main`
  (`required_status_check` dans `terraform/github/variables.tf`).
- `publish` dépend de **tous** les contrôles : aucune image n'est publiée ni
  signée si un seul est rouge. Sur une Pull Request, rien n'est publié.
- L'image est construite **une seule fois** (`image-scan`) puis transmise en
  artefact : l'image scannée, l'image testée par ZAP et l'image publiée sont
  la même.
- `dast` tourne même si un contrôle statique échoue, pour toujours produire le
  rapport ZAP ; il bloque lui-même la PR s'il trouve une alerte High.

## Règles par outil

| Étape | Outil | Bloque si | Rapporté sans bloquer | Failles couvertes |
|-------|-------|-----------|-----------------------|-------------------|
| Build + tests | pytest `-m "not security"` | un test fonctionnel échoue | — | régressions |
| Tests de sécurité | pytest `-m security` | un test échoue | — | V1 (IDOR), V2 (SQLi) |
| SAST | Semgrep `p/default` + `p/security-audit` | au moins un constat **ERROR** | WARNING, INFO | V2 (ERROR) ; Bonus 2 (WARNING) |
| SAST | Bandit | sévérité **HIGH** et confiance ≥ MEDIUM | LOW, MEDIUM | V2 (B608), V3 (B105) rapportés |
| Secrets | Gitleaks (historique **complet**) | au moins une fuite | — | V3 |
| Dépendances | Trivy fs | **HIGH/CRITICAL avec correctif** disponible | sans correctif | V4 |
| IaC | Trivy config | **HIGH/CRITICAL** non couvert par une exception | MEDIUM, LOW | V5 (Partie 2), dépôt GitHub |
| IaC | Checkov | jamais (`--soft-fail`) | tout | second avis IaC |
| Image | Trivy image | **HIGH/CRITICAL avec correctif** | sans correctif | V4 dans l'image |
| SBOM | Syft (SPDX JSON) | génération impossible | — | traçabilité |
| Publication | Cosign (keyless, OIDC GitHub) | signature ou vérification impossible | — | intégrité de l'image |
| DAST | OWASP ZAP (scan actif authentifié) | au moins une alerte **High** | Medium, Low, Info | V2, Bonus 2 ; Bonus 1 rapporté |

## Justifications

- **Semgrep ERROR uniquement** : les règles ERROR (`sqlalchemy-execute-raw-query`,
  `formatted-sql-query`) visent des injections directement exploitables. Les
  WARNING (`template-unescaped-with-safe`) sont plus bruitées ; le XSS (Bonus 2)
  est de toute façon bloqué par ZAP, qui prouve qu'il est exploitable.
- **Bandit HIGH uniquement** : Bandit produit beaucoup de LOW (par exemple B311
  `random` dans `app/seed.py`, sans enjeu de sécurité pour des données de
  démonstration). V2 (B608, MEDIUM) est déjà bloquée par Semgrep ; V3 (B105, LOW)
  par Gitleaks. Bandit sert de second avis rapporté.
- **Gitleaks sur tout l'historique** (`fetch-depth: 0`) : un secret retiré du
  code reste lisible dans les anciens commits d'un dépôt public. Corriger V3
  impose donc une rotation **et** une purge de l'historique.
- **Trivy `--ignore-unfixed`** : l'image `python:3.12-slim` contient des
  vulnérabilités Debian HIGH sans correctif publié. Les bloquer rendrait le
  pipeline rouge en permanence sans action possible ; elles restent visibles
  dans la SBOM et sont suivies à la reconstruction de l'image de base.
- **ZAP High uniquement** : les alertes High de ZAP (injection SQL, XSS réfléchi)
  sont des attaques confirmées par le scan actif. Les en-têtes manquants
  (Bonus 1) sont Medium/Low : ils sont rapportés et corrigés, mais ne sont pas
  une faille exploitable à eux seuls.
- **Checkov non bloquant** : Trivy config porte la décision IaC ; Checkov,
  plus verbeux, sert de second avis sans doubler les blocages.

## Exceptions

Toute exception est déclarée dans un fichier versionné (`.trivyignore`, etc.),
relue en Pull Request et justifiée ici. Aucune exception n'est accordée pour une
faille volontaire V1-V5 ou Bonus.

| Outil | Identifiant | Fichier | Justification | Revue |
|-------|-------------|---------|---------------|-------|
| _aucune pour l'instant_ | | | | |

## Secrets utilisés par le pipeline

| Secret | Usage | Source |
|--------|-------|--------|
| `POSTGRES_PASSWORD` | base PostgreSQL de test (services CI, Docker Compose du DAST) | GitHub Secret créé par Terraform |
| `APP_SECRET_KEY` | `SECRET_KEY` Flask du Docker Compose du DAST | GitHub Secret créé par Terraform |
| `GITHUB_TOKEN` | push GHCR (`packages: write`) | fourni par GitHub Actions, éphémère |
| jeton OIDC | signature Cosign sans clé (`id-token: write`) | fourni par GitHub Actions, éphémère |

Aucune valeur de secret n'apparaît dans les journaux du pipeline ni dans les preuves.
