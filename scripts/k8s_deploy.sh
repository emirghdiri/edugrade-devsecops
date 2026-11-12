#!/usr/bin/env bash
# Déploie l'application EduGrade sur k3s (après terraform -chdir=terraform/cluster apply).
#   1. ConfigMap nginx-conf depuis docker/nginx.conf (même configuration qu'en Compose) ;
#   2. manifestes durcis k8s/ (kustomize) ;
#   3. attente des trois composants.
# Kyverno vérifie à l'admission la signature de l'image backend et le durcissement.
set -euo pipefail
cd "$(dirname "$0")/.."
NS=edugrade

kubectl -n "$NS" create configmap nginx-conf \
  --from-file=default.conf=docker/nginx.conf --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k k8s/
kubectl -n "$NS" rollout status statefulset/db --timeout=180s
kubectl -n "$NS" rollout status deployment/backend --timeout=240s
kubectl -n "$NS" rollout status deployment/frontend --timeout=120s
kubectl -n "$NS" get pods -o wide
echo "Application : http://edugrade.localhost"
