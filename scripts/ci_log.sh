#!/usr/bin/env bash
# Affiche le journal d'un job GitHub Actions, sans horodatage ni couleurs.
#
# Usage : scripts/ci_log.sh <run-id> <début du nom du job> [motif ERE à garder] [--all]
#   Par défaut, seules les étapes en échec sont affichées (--log-failed) ;
#   --all affiche toutes les étapes (utile pour un job vert).
# Exemple : scripts/ci_log.sh 43276134672 secrets 'RuleID|File|Line|leaks'
set -euo pipefail

RUN="$1"; JOB="$2"; PATTERN="${3:-.}"; MODE="--log-failed"
[ "${4:-}" = "--all" ] && MODE="--log"
REPO="${CI_REPO:-emirghdiri/edugrade-devsecops}"

JOB_ID="$(gh run view "$RUN" -R "$REPO" --json jobs \
  -q ".jobs[] | select(.name | startswith(\"$JOB\")) | .databaseId" | head -1)"
[ -n "$JOB_ID" ] || { echo "job « $JOB » introuvable dans le run $RUN" >&2; exit 2; }

gh run view "$RUN" -R "$REPO" --json jobs -q ".jobs[] | select(.databaseId == $JOB_ID) | \"Job : \(.name) — \(.conclusion)\nURL : \(.url)\""
echo "------------------------------------------------------------"
gh run view "$RUN" -R "$REPO" --job "$JOB_ID" $MODE \
  | cut -f3- \
  | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z ?//; s/\x1b\[[0-9;]*m//g' \
  | grep -vE '^\s*$' | grep -E -- "$PATTERN" || true
