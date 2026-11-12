#!/usr/bin/env bash
# Télécharge les charts Helm épinglés (terraform/cluster/variables.tf) dans
# terraform/cluster/charts/ (ignoré par git). Terraform les installe depuis le
# disque : le plan/apply ne dépend plus de la disponibilité des dépôts Helm.
set -euo pipefail
cd "$(dirname "$0")/../terraform/cluster"
mkdir -p charts
ver() { grep -E "^\s+$1\s+=" variables.tf | sed -E 's/.*"([^"]+)".*/\1/'; }
pull() { # $1 dépôt, $2 chart, $3 version
  [ -f "charts/$2-$3.tgz" ] && { echo "déjà présent : $2-$3.tgz"; return; }
  for i in 1 2 3 4 5 6; do
    helm pull "$2" --repo "$1" --version "$3" -d charts >/dev/null 2>&1 && { echo "téléchargé : $2-$3.tgz"; return; }
    echo "  $2 : essai $i échoué, nouvelle tentative"; sleep 5
  done
  echo "échec : $2-$3" >&2; return 1
}
pull https://kyverno.github.io/kyverno/ kyverno "$(ver kyverno)"
pull https://prometheus-community.github.io/helm-charts kube-prometheus-stack "$(ver kube_prometheus_stack)"
pull https://grafana.github.io/helm-charts loki "$(ver loki)"
pull https://grafana.github.io/helm-charts alloy "$(ver alloy)"
