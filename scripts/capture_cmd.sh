#!/usr/bin/env bash
# Exécute une commande, enregistre sa sortie dans docs/preuves/logs/<nom>.txt
# et la rend en image façon terminal dans docs/preuves/captures/<nom>.png.
#
# Usage : scripts/capture_cmd.sh <NN-description> '<commande>'
#   CAPTURE_CWD=<dossier>   dossier où exécuter la commande (défaut : dossier courant)
#   CAPTURE_TITLE=<titre>   titre affiché dans la capture (défaut : le nom)
#   CAPTURE_MASK=<regex>    motif ERE supplémentaire à masquer dans la sortie
#
# Le code de retour de la commande est conservé et renvoyé.
set -uo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <NN-description> '<commande>'" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$1"; shift
CMD="$*"
RUN_DIR="${CAPTURE_CWD:-$PWD}"
LOG_DIR="$ROOT/docs/preuves/logs"
CAP_DIR="$ROOT/docs/preuves/captures"
PYTHON="${CAPTURE_PYTHON:-$ROOT/.venv/bin/python}"
mkdir -p "$LOG_DIR" "$CAP_DIR"

LOG="$LOG_DIR/$NAME.txt"
PNG="$CAP_DIR/$NAME.png"
RAW="$(mktemp)"
trap 'rm -f "$RAW"' EXIT

# Exécution (sans couleurs ANSI quand l'outil le permet).
( cd "$RUN_DIR" && NO_COLOR=1 TERM=dumb bash -c "$CMD" ) >"$RAW" 2>&1
RC=$?

# Masquage des jetons et secrets avant toute écriture dans docs/.
MASK_EXPR=(
  -e 's/\x1b\[[0-9;?]*[A-Za-z]//g'
  -e 's/(gh[pousr]_)[A-Za-z0-9]{20,}/\1****MASQUÉ****/g'
  -e 's/github_pat_[A-Za-z0-9_]{20,}/github_pat_****MASQUÉ****/g'
  -e 's/(GITHUB_TOKEN=)[^[:space:]]+/\1****MASQUÉ****/g'
)
[ -n "${CAPTURE_MASK:-}" ] && MASK_EXPR+=(-e "s/${CAPTURE_MASK}/****MASQUÉ****/g")
mask() { sed -E "${MASK_EXPR[@]}"; }

REL_DIR="${RUN_DIR/#$ROOT/.}"
{
  echo "# Preuve : $NAME"
  echo "# Date   : $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "# Dossier: $REL_DIR"
  echo "\$ $CMD"
  cat "$RAW"
  echo "[code de retour : $RC]"
} | mask >"$LOG"

if [ -x "$PYTHON" ]; then
  "$PYTHON" "$ROOT/scripts/render_terminal.py" "$LOG" "$PNG" "${CAPTURE_TITLE:-$NAME}" \
    || echo "avertissement : rendu PNG impossible pour $NAME" >&2
else
  echo "avertissement : $PYTHON introuvable, capture PNG non générée" >&2
fi

echo "log     : ${LOG#$ROOT/}"
[ -f "$PNG" ] && echo "capture : ${PNG#$ROOT/}"
exit "$RC"
