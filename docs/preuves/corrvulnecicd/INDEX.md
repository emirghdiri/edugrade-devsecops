# Preuves Partie 2 — Pipeline CI/CD : erreur → correction → vert

Pour chaque contrôle du pipeline qui échoue, trois preuves sont conservées :

1. **erreur** : le job rouge dans GitHub Actions et l'extrait du journal qui
   montre la cause ;
2. **correction** : le diff du commit qui corrige (une branche `fix/*` et une
   Pull Request par faille) ;
3. **après** : le journal du run de la PR de correction, où l'erreur a disparu.

Numérotation à partir de **40** (00-39 et M01-M10 sont utilisés en Partie 1).
Journaux : [`logs/`](logs/) (commande exacte, sortie, code de retour) ;
captures : [`captures/`](captures/). Générés avec :

```bash
CAPTURE_DIR=docs/preuves/corrvulnecicd scripts/capture_cmd.sh NN-description '<commande>'
scripts/ci_log.sh <run-id> <job> '<motif>' [--all]     # extrait d'un journal de job GitHub Actions
.venv/bin/python scripts/capture_web.py <url du run> docs/preuves/corrvulnecicd/captures/NN-...-web.png
```

Règle : aucune valeur de secret, aucun jeton ni cookie complet dans les preuves
(valeurs de V3 masquées `****MASQUÉ****`, cookie tronqué).

## Runs de référence

| Run | Branche | Résultat | Lien |
|-----|---------|----------|------|
| Run 1 | `feature/ci-pipeline` (PR #9) — version vulnérable | **rouge** : 7 jobs sur 9 bloquent, `publish` sauté | [43276134672](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43276134672) |
| Run 3 | `feature/ci-pipeline` (PR #9) — Bandit corrigé | rouge (failles encore présentes) | [43279459278](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43279459278) |
| PR #10 | `fix/idor` | V1 corrigée | [43281357691](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281357691) |
| PR #11 | `fix/sqli` | V2 corrigée, `sast` vert | [43281364009](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281364009) |
| PR #12 | `fix/xss` | Bonus 2 corrigé | [43281373154](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281373154) |
| PR #13 | `fix/security-headers` | Bonus 1 corrigé | [43281380634](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281380634) |
| PR #14 | `fix/secrets` | V3 corrigée, `secrets` vert | [43281394826](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281394826) |
| PR #15 | `fix/pyyaml` | V4 corrigée, `dependencies` vert | [43281402183](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281402183) |
| PR #16 | `fix/image-base` | zlib corrigé | [43281407572](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281407572) |
| PR #17 | `fix/iac-github` | IaC, `iac` vert | [43281427223](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281427223) |
| Intégration | `integration/v1.0-secure` (toutes les corrections) | **vert : 9 jobs sur 9**, image publiée et signée | [43281516275](https://github.com/emirghdiri/edugrade-devsecops/actions/runs/43281516275) |

Chaque PR ne corrige qu'une faille : un job qui détecte plusieurs failles
(`security-tests` : V1+V2 ; `dast` : V2+B1+B2 ; `image` : V4+zlib) reste rouge
tant que les autres ne sont pas corrigées. La preuve « après » montre alors que
**l'alerte visée a disparu** du journal ; le run d'intégration prouve que tout
est vert une fois les corrections réunies.

## Run 1 — Pipeline sur la version vulnérable (preuves « avant »)

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| 40 | Synthèse du run 1 : `build-test` vert, 7 contrôles rouges, `publish` sauté (aucune image vulnérable publiée) | [log](logs/40-ci-run1-pipeline-rouge.txt) | [terminal](captures/40-ci-run1-pipeline-rouge.png) · [GitHub](captures/40-ci-run1-pipeline-rouge-web.png) |
| 41 | `security-tests` : 4 échecs — V1 (notes de Youssef accessibles, aucun `access_denied`), V2 (tautologie, hachages divulgués) | [log](logs/41-ci-security-tests-v1-v2-avant.txt) | [capture](captures/41-ci-security-tests-v1-v2-avant.png) |
| 42 | `sast` : Semgrep V2 `sqlalchemy-execute-raw-query` (ERROR, bloquant) ; Bonus 2 `template-unescaped-with-safe` (WARNING) | [log](logs/42-ci-sast-semgrep-v2-b2-avant.txt) | [capture](captures/42-ci-sast-semgrep-v2-b2-avant.png) |
| 43 | `secrets` : Gitleaks V3, 2 × `generic-api-key` dans `app/config.py` (commit `f78fd00`) | [log](logs/43-ci-secrets-gitleaks-v3-avant.txt) | [capture](captures/43-ci-secrets-gitleaks-v3-avant.png) |
| 44 | `dependencies` : Trivy fs V4, PyYAML 5.3.1 CVE-2020-14343 (CRITICAL) | [log](logs/44-ci-dependencies-trivy-fs-v4-avant.txt) | [capture](captures/44-ci-dependencies-trivy-fs-v4-avant.png) |
| 45 | `image` : Trivy image V4 + zlib CVE-2026-76844 / CVE-2026-85091 (HIGH, trouvaille hors failles volontaires) | [log](logs/45-ci-image-trivy-v4-zlib-avant.txt) | [capture](captures/45-ci-image-trivy-v4-zlib-avant.png) |
| 46 | `iac` : Trivy config GIT-0001 (dépôt public, CRITICAL), GIT-0004 (commits signés, HIGH) | [log](logs/46-ci-iac-trivy-config-avant.txt) | [capture](captures/46-ci-iac-trivy-config-avant.png) |
| 47 | `dast` : ZAP, 3 alertes High (SQL Injection, XSS réfléchi, XSS DOM) + en-têtes absents (Bonus 1, Medium/Low) | [log](logs/47-ci-dast-zap-v2-b1-b2-avant.txt) | [capture](captures/47-ci-dast-zap-v2-b1-b2-avant.png) |
| 49 | PR #9 : checks rouges dans l'interface GitHub | — | [GitHub](captures/49-ci-pr9-checks-rouges-web.png) |

## Erreur du pipeline lui-même

| Étape | N° | Ce que la preuve montre | Journal | Capture |
|-------|----|-------------------------|---------|---------|
| Erreur | 48 | Bandit fait échouer `sast` alors qu'aucun constat n'est HIGH (`bandit -f txt` sort en code 1) **et affiche les secrets V3 dans le journal public** (masqués ici) | [log](logs/48-ci-erreur-pipeline-bandit-avant.txt) | [capture](captures/48-ci-erreur-pipeline-bandit-avant.png) |
| Correction | 51 | Commit `123420d` : format Bandit sans message ni code (`{relpath}:{line} {test_id} {severity}/{confidence}`), blocage HIGH seul ; `upload-artifact` v6 (Node 24) | [log](logs/51-ci-erreur-pipeline-bandit-correction.txt) | [capture](captures/51-ci-erreur-pipeline-bandit-correction.png) |
| Après | 52 | Run 3 : Bandit rapporte les 4 constats sans valeur, « aucun constat bloquant » | [log](logs/52-ci-erreur-pipeline-bandit-apres.txt) | [capture](captures/52-ci-erreur-pipeline-bandit-apres.png) |

## Corrections des failles

| Faille | Erreur (avant) | Correction (diff) | Après |
|--------|----------------|-------------------|-------|
| **V1** IDOR — PR #10 | [41](captures/41-ci-security-tests-v1-v2-avant.png) | [60](captures/60-v1-idor-correction.png) : 403 + `access_denied` si un étudiant demande les notes d'un autre | [61](captures/61-v1-idor-apres.png) : les 2 tests IDOR **PASSED** |
| **V2** injection SQL — PR #11 | [41](captures/41-ci-security-tests-v1-v2-avant.png), [42](captures/42-ci-sast-semgrep-v2-b2-avant.png), [47](captures/47-ci-dast-zap-v2-b1-b2-avant.png) | [62](captures/62-v2-sqli-correction.png) : `ILIKE %s` + paramètre lié | [63](captures/63-v2-sqli-apres.png) : tests SQLi **PASSED**, `sast` **vert** ([GitHub](captures/63-v2-sqli-apres-web.png)) |
| **Bonus 2** XSS — PR #12 | [47](captures/47-ci-dast-zap-v2-b1-b2-avant.png), [42](captures/42-ci-sast-semgrep-v2-b2-avant.png) | [64](captures/64-b2-xss-correction.png) : suppression de `\|safe` + `tests/security/test_xss.py` | [65](captures/65-b2-xss-apres.png) : plus aucune alerte ZAP XSS |
| **Bonus 1** en-têtes — PR #13 | [47](captures/47-ci-dast-zap-v2-b1-b2-avant.png) | [66](captures/66-b1-entetes-correction.png) : CSP stricte, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP/CORP/COEP dans Nginx | [67](captures/67-b1-entetes-apres.png) : plus aucune alerte ZAP d'en-tête |
| **V3** secrets — PR #14 | [43](captures/43-ci-secrets-gitleaks-v3-avant.png) | [68](captures/68-v3-secrets-correction.png) : secrets lus dans l'environnement, exception Gitleaks limitée aux 2 empreintes de `f78fd00` | [69](captures/69-v3-secrets-apres.png) : `no leaks found`, `secrets` **vert** ([GitHub](captures/69-v3-secrets-apres-web.png)) ; [70](captures/70-v3-rotation-ancienne-cle-refusee-apres.png) : cookie forgé avec l'ancienne clé → **302 /login** (rotation effective) |
| **V4** PyYAML — PR #15 | [44](captures/44-ci-dependencies-trivy-fs-v4-avant.png), [45](captures/45-ci-image-trivy-v4-zlib-avant.png) | [71](captures/71-v4-pyyaml-correction.png) : `PyYAML==6.0.3` + `yaml.safe_load` | [72](captures/72-v4-pyyaml-apres.png) : `requirements.txt` 0 vulnérabilité, `dependencies` **vert** ([GitHub](captures/72-v4-pyyaml-apres-web.png)) |
| **zlib** (image de base) — PR #16 | [45](captures/45-ci-image-trivy-v4-zlib-avant.png) | [73](captures/73-image-zlib-correction.png) : `apt-get upgrade` dans l'image d'exécution | [74](captures/74-image-zlib-apres.png) : plus de zlib (reste PyYAML, corrigé par PR #15) |
| **IaC** dépôt GitHub — PR #17 | [46](captures/46-ci-iac-trivy-config-avant.png) | [75](captures/75-iac-github-correction.png) : exceptions `.trivyignore.yaml` limitées à `main.tf`, justifiées, expirant le 2027-06-30 | [76](captures/76-iac-github-apres.png) : `main.tf` 0 constat, `iac` **vert** ([GitHub](captures/76-iac-github-apres-web.png)) |

## Toutes les corrections réunies — pipeline vert

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| 80 | Run d'intégration : **9 jobs sur 9 verts**, 44 tests fonctionnels + tests de sécurité | [log](logs/80-ci-integration-tout-vert.txt) | [terminal](captures/80-ci-integration-tout-vert.png) · [GitHub](captures/82-ci-integration-tout-vert-web.png) |
| 81 | `publish` : image poussée sur GHCR (tag = SHA), **signée par Cosign sans clé (OIDC)**, entrée dans le journal de transparence Rekor, signature **vérifiée** | [log](logs/81-ci-publish-ghcr-cosign-apres.txt) | [capture](captures/81-ci-publish-ghcr-cosign-apres.png) |
| 83 | SBOM Syft (SPDX JSON) : 101 paquets ; Trivy image sans HIGH/CRITICAL corrigeable | [log](logs/83-ci-sbom-syft-apres.txt) | [capture](captures/83-ci-sbom-syft-apres.png) |
| 84 | `dast` : ZAP authentifié, **aucune alerte High** (reste 1 Low « Cookie Slack Detector », informative) | [log](logs/84-ci-dast-zap-tout-vert.txt) | [capture](captures/84-ci-dast-zap-tout-vert.png) |
