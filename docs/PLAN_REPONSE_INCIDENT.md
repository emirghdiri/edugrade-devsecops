# Plan de réponse à incident — EduGrade

Ce plan décrit **qui fait quoi** quand une alerte de sécurité se déclenche sur
EduGrade déployé dans k3s. Il suit les phases du NIST SP 800-61 : préparation,
détection et analyse, confinement, éradication, rétablissement, retour
d'expérience. Toutes les données sont fictives.

## 1. Préparation

| Élément | Où |
|---------|----|
| Journaux applicatifs JSON (`event`, `user_id`, `role`, `route`, `ip`, `status`) | Loki, labels `namespace="edugrade"`, `event`, `level` (collecte Alloy) |
| Tableau de bord « Sécurité EduGrade » | Grafana, dossier EduGrade (`terraform/cluster/grafana/dashboard-securite.json`) |
| Règles d'alerte | Grafana, dossier EduGrade (`terraform/cluster/grafana/alertes.yaml`) |
| Accès Grafana | `kubectl -n monitoring port-forward svc/kps-grafana 3000:80` ; identifiants dans le Secret `grafana-admin` |
| Inventaire de l'image déployée | digest dans `k8s/backend.yaml`, SBOM SPDX (artefact `sbom` du pipeline), signature Cosign |
| Contrôles préventifs | pipeline bloquant (`docs/POLITIQUE_BLOCAGE.md`), Kyverno, Pod Security « restricted », NetworkPolicies |

Rôles (équipe de deux) :

| Rôle | Titulaire | Responsabilités |
|------|-----------|-----------------|
| Responsable d'incident | membre d'astreinte | qualifie l'alerte, décide du confinement, tient la chronologie |
| Opérateur technique | l'autre membre | exécute les commandes, collecte les preuves, applique le correctif |

## 2. Détection et analyse

### Alertes et seuils

| Alerte | Requête LogQL | Seuil | Gravité |
|--------|---------------|-------|---------|
| Force brute sur la connexion | `sum(count_over_time({namespace="edugrade", event="login_failed"}[5m]))` | > 5 en 5 min | critique |
| Tentative d'injection (SQLi / XSS) | `sum(count_over_time({namespace="edugrade", event="suspicious_input"}[5m]))` | > 0 en 5 min | critique |
| Accès non autorisé (IDOR) | `sum(count_over_time({namespace="edugrade", event="access_denied"}[5m]))` | > 3 en 5 min | avertissement |

### Qualification (15 minutes maximum)

1. Ouvrir le tableau de bord « Sécurité EduGrade » sur la fenêtre de l'alerte.
2. Identifier la ou les **adresses IP** (tableau « Adresses IP à l'origine des
   échecs ») et les **comptes** visés (`user_id`, `email` absent des journaux
   par conception : retrouver le compte par `user_id`).
3. Requêtes Loki utiles :
   ```logql
   {namespace="edugrade", event="login_failed"} | json | line_format "{{.ip}} {{.route}} {{.status}}"
   {namespace="edugrade", event="suspicious_input"} | json | line_format "{{.user_id}} {{.role}} {{.patterns}}"
   {namespace="edugrade"} | json | ip="<IP suspecte>"
   ```
4. Une connexion **réussie** (`login_success`) depuis la même IP après des
   échecs signifie un **compte compromis** : gravité critique.
5. Classer l'incident :

| Niveau | Critère | Délai de confinement |
|--------|---------|----------------------|
| P1 critique | compte compromis, injection aboutie, donnée exfiltrée | immédiat |
| P2 élevé | attaque en cours sans succès confirmé | < 1 h |
| P3 modéré | tentative isolée, bloquée | < 24 h |

## 3. Confinement

| Situation | Action | Commande / lieu |
|-----------|--------|-----------------|
| Force brute en cours | bloquer l'IP source à l'entrée (Traefik) | Middleware Traefik `ipDenyList` sur l'Ingress `edugrade` |
| Compte compromis | invalider **toutes** les sessions : rotation de `SECRET_KEY` (cookies signés) | `terraform -chdir=terraform/cluster apply -replace=random_password.app_secret_key` puis `kubectl -n edugrade rollout restart deploy/backend` |
| Compte compromis | réinitialiser le mot de passe du compte | espace administrateur (CRUD des comptes) |
| Injection aboutie / exfiltration suspectée | isoler le backend (aucun flux sortant hors base) | NetworkPolicy `backend` (déjà sans sortie Internet depuis la correction de V5) ; au besoin `kubectl -n edugrade scale deploy/frontend --replicas=0` |
| Image suspecte | revenir à la dernière image saine **signée** | modifier le digest dans `k8s/backend.yaml`, `scripts/k8s_deploy.sh` ; Kyverno refuse toute image non signée |

Conserver les preuves **avant** toute modification :

```bash
kubectl -n edugrade logs deploy/backend --since=24h > incident-$(date +%F)-backend.log
kubectl -n edugrade get pods,deploy,netpol -o yaml > incident-$(date +%F)-etat.yaml
```

## 4. Éradication

1. Identifier la cause (faille applicative, secret exposé, dépendance).
2. Corriger dans une branche `fix/*` ; la Pull Request doit passer **tout** le
   pipeline (tests de sécurité, SAST, Gitleaks, Trivy, ZAP).
3. Ajouter un **test de non-régression** qui reproduit l'attaque
   (`tests/security/`).
4. Si un secret a fuité : rotation (GitHub Secrets, Secrets Kubernetes via
   Terraform), puis vérification Gitleaks sur l'historique.

## 5. Rétablissement

1. Fusion dans `develop` : le pipeline publie et **signe** la nouvelle image.
2. Mettre à jour le digest dans `k8s/backend.yaml`, déployer
   (`scripts/k8s_deploy.sh`) ; Kyverno vérifie la signature.
3. Rejouer `scripts/k8s_segmentation_test.sh` et le scénario d'attaque :
   l'attaque doit être bloquée et visible dans Grafana.
4. Surveiller le tableau de bord 24 h.

## 6. Retour d'expérience (sous 5 jours)

Rédiger une note : chronologie (détection → confinement → rétablissement),
cause racine, ce qui a bien fonctionné, ce qui a manqué (seuil d'alerte,
journalisation, règle de pipeline), actions correctives avec responsable et
date. Mettre à jour ce plan et `docs/POLITIQUE_BLOCAGE.md` si nécessaire.

## 7. Exercice réalisé

Le scénario `scripts/attack_scenario.sh` (force brute, injections, XSS, IDOR) a
été joué contre le cluster ; sa détection dans Loki et le déclenchement des
alertes sont prouvés dans `docs/preuves/corrvulnecicd/` (preuves 9x).
