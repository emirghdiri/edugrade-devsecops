#!/usr/bin/env bash
# Vérifie la détection après scripts/attack_scenario.sh :
#   - événements de sécurité EduGrade comptés dans Loki (15 dernières minutes) ;
#   - état des règles d'alerte Grafana « EduGrade ».
# Ouvre des port-forward temporaires (Loki 3100, Grafana 3000) ; aucun secret affiché.
set -uo pipefail
kubectl -n monitoring port-forward svc/loki 3100:3100 >/dev/null 2>&1 & PF1=$!
kubectl -n monitoring port-forward svc/kps-grafana 3000:80 >/dev/null 2>&1 & PF2=$!
trap 'kill $PF1 $PF2 2>/dev/null' EXIT
sleep 5

echo "=== Loki : événements de sécurité (namespace edugrade, 15 min) ==="
curl -s -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query=sum by (event) (count_over_time({namespace="edugrade", event=~"login_failed|login_success|access_denied|suspicious_input|csrf_failed"}[15m]))' \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['data']['result']; [print(f\"{x['metric']['event']:<18} {x['value'][1]}\") for x in sorted(r,key=lambda x:x['metric']['event'])]"

echo
echo "=== Loki : exemples (suspicious_input, access_denied) ==="
curl -s -G http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={namespace="edugrade", event=~"suspicious_input|access_denied"} | json | line_format "{{.timestamp}} {{.event}} user={{.user_id}} role={{.role}} route={{.route}} status={{.status}} {{.patterns}}"' \
  --data-urlencode 'limit=6' \
  | python3 -c "import sys,json; [print(v[1]) for s in json.load(sys.stdin)['data']['result'] for v in s['values'][:3]]"

echo
echo "=== Grafana : règles d'alerte EduGrade ==="
PW="$(kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d)"
curl -s -u "admin:$PW" http://localhost:3000/api/prometheus/grafana/api/v1/rules | python3 -c "
import sys,json
for g in json.load(sys.stdin)['data']['groups']:
  for r in g['rules']:
    print(f\"{r['state']:<9} {r['name']}\")"
