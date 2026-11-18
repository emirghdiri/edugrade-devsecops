#!/usr/bin/env bash
# DAST : scan OWASP ZAP authentifié de l'application lancée par Docker Compose.
#
# Usage : scripts/zap_scan.sh [URL]          (défaut : http://localhost:8080)
#   ZAP_USER / ZAP_PASSWORD  compte utilisé pour le scan (défaut : enseignante de démo, fictive)
#   ZAP_MAX_MINUTES          durée maximale du scan actif (défaut : 10)
#   ZAP_OUT                  dossier des rapports (défaut : reports/zap)
#
# Politique (docs/POLITIQUE_BLOCAGE.md) : le script échoue (code 1) si ZAP
# remonte au moins une alerte de risque High ; Medium/Low/Info sont rapportés
# sans bloquer.
set -euo pipefail

TARGET="${1:-http://localhost:8080}"
ZAP_USER="${ZAP_USER:-claire.dubois@edugrade.test}"
ZAP_PASSWORD="${ZAP_PASSWORD:-claire2026}"   # compte de démonstration fictif
MAX_MIN="${ZAP_MAX_MINUTES:-10}"
OUT="${ZAP_OUT:-reports/zap}"
ZAP_IMAGE="${ZAP_IMAGE:-ghcr.io/zaproxy/zaproxy:stable}"

mkdir -p "$OUT"
chmod 777 "$OUT"   # le conteneur ZAP écrit en tant qu'utilisateur « zap » (UID 1000)
OUT_ABS="$(cd "$OUT" && pwd)"

# 1. Connexion scriptée : lire le jeton CSRF de /login, puis POST du formulaire.
JAR="$(mktemp)"; trap 'rm -f "$JAR"' EXIT
TOKEN="$(curl -sf -c "$JAR" -b "$JAR" "$TARGET/login" \
  | grep -o 'name="csrf_token"[^>]*value="[^"]*"' | sed 's/.*value="//;s/"$//')"
[ -n "$TOKEN" ] || { echo "jeton CSRF introuvable sur $TARGET/login" >&2; exit 2; }
CODE="$(curl -s -o /dev/null -w '%{http_code}' -c "$JAR" -b "$JAR" -X POST "$TARGET/login" \
  --data-urlencode "csrf_token=$TOKEN" --data-urlencode "email=$ZAP_USER" --data-urlencode "password=$ZAP_PASSWORD")"
[ "$CODE" = "302" ] || { echo "connexion refusée (HTTP $CODE)" >&2; exit 2; }
COOKIE="$(awk '$6 ~ /session/ {print $6"="$7}' "$JAR" | tail -1)"
[ -n "$COOKIE" ] || { echo "cookie de session absent" >&2; exit 2; }
echo "session ZAP ouverte pour $ZAP_USER (cookie non affiché)"

# 2. Scan complet (spider + scan passif + scan actif). Le « replacer » ajoute le
#    cookie de session à chaque requête de ZAP ; csrf_token fait partie des jetons
#    anti-CSRF connus de ZAP, qui le relit avant chaque POST.
ZAP_OPTS="-config replacer.full_list(0).description=session \
-config replacer.full_list(0).enabled=true \
-config replacer.full_list(0).matchtype=REQ_HEADER \
-config replacer.full_list(0).matchstr=Cookie \
-config replacer.full_list(0).regex=false \
-config replacer.full_list(0).replacement=$COOKIE \
-config scanner.maxScanDurationInMins=$MAX_MIN"

set +e
docker run --rm --network host -v "$OUT_ABS:/zap/wrk:rw" "$ZAP_IMAGE" \
  zap-full-scan.py -t "$TARGET/teacher/students?q=test" -m 2 -I \
  -J zap-report.json -r zap-report.html -w zap-report.md -z "$ZAP_OPTS" \
  | grep -v "$COOKIE"
ZAP_RC=${PIPESTATUS[0]}
set -e
[ -f "$OUT_ABS/zap-report.json" ] || { echo "rapport ZAP absent (code $ZAP_RC)" >&2; exit 2; }

# 3. Politique de blocage : High (riskcode 3) => échec.
python3 - "$OUT_ABS/zap-report.json" <<'PY'
import json, sys
names = {"3": "High", "2": "Medium", "1": "Low", "0": "Info"}
report = json.load(open(sys.argv[1]))
alerts = [a for site in report.get("site", []) for a in site.get("alerts", [])]
alerts.sort(key=lambda a: -int(a["riskcode"]))
print("\n=== Synthèse ZAP (risque | alerte | occurrences) ===")
for a in alerts:
    print(f'{names[a["riskcode"]]:<6} | {a["alert"]} | {a.get("count", len(a.get("instances", [])))}')
high = [a for a in alerts if a["riskcode"] == "3"]
if high:
    print(f"\nÉCHEC : {len(high)} alerte(s) High -> la livraison est bloquée.")
    for a in high:
        for i in a.get("instances", [])[:3]:
            print(f'  - {a["alert"]}: {i.get("method")} {i.get("uri")} param={i.get("param")}')
    sys.exit(1)
print("\nOK : aucune alerte High.")
PY
