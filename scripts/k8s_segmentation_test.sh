#!/usr/bin/env bash
# Tests de segmentation réseau (NetworkPolicies) et d'admission (Kyverno + Pod
# Security Admission) du namespace edugrade.
#
# Chaque test affiche ATTENDU / OBTENU et OK ou ÉCHEC ; le script sort en code 1
# si un résultat diffère de l'attendu.
#   SIGNED_OTHER_BRANCH : image EduGrade signée par une AUTRE branche que develop/main
set -uo pipefail
NS=edugrade
SIGNED_OTHER_BRANCH="${SIGNED_OTHER_BRANCH:-ghcr.io/emirghdiri/edugrade-backend@sha256:3f41934dbdfc3651465822647eb8174a6894f883bdbb226e320105f02a8c7235}"
FAIL=0

pod_of() { kubectl -n "$NS" get pod -l "app.kubernetes.io/name=$1" -o jsonpath='{.items[0].metadata.name}'; }
FE="$(pod_of frontend)"; BE="$(pod_of backend)"

result() { # $1 description, $2 attendu (autorisé|bloqué|refusé|accepté), $3 obtenu
  local mark="OK"; [ "$2" = "$3" ] || { mark="ÉCHEC"; FAIL=1; }
  printf '%-58s attendu: %-9s obtenu: %-9s %s\n' "$1" "$2" "$3" "$mark"
}

# Connexion TCP depuis un pod (busybox nc dans le frontend, Python dans le backend).
tcp_from() { # $1 pod, $2 hôte, $3 port
  if [ "$1" = "$FE" ]; then
    kubectl -n "$NS" exec "$1" -- nc -z -w 3 "$2" "$3" >/dev/null 2>&1
  else
    kubectl -n "$NS" exec "$1" -- python -c "import socket,sys; socket.create_connection(('$2',$3),timeout=3)" >/dev/null 2>&1
  fi && echo autorisé || echo bloqué
}

echo "=== Segmentation réseau (NetworkPolicies) ==="
result "frontend -> backend:8000 (flux applicatif)"            autorisé "$(tcp_from "$FE" backend 8000)"
result "backend  -> db:5432 (flux applicatif)"                 autorisé "$(tcp_from "$BE" db 5432)"
result "frontend -> db:5432 (contournement du backend)"        bloqué   "$(tcp_from "$FE" db 5432)"
result "frontend -> Internet 1.1.1.1:443"                      bloqué   "$(tcp_from "$FE" 1.1.1.1 443)"
result "backend  -> Internet 1.1.1.1:443 (exfiltration, V5)"   bloqué   "$(tcp_from "$BE" 1.1.1.1 443)"

echo
echo "=== Admission (Kyverno + Pod Security « restricted ») — dry-run serveur ==="
# Pod conforme à toutes les règles sauf, éventuellement, celle testée.
admit() { # $1 nom, $2 image, $3 runAsNonRoot, $4 privileged
  kubectl -n "$NS" apply --dry-run=server -f - >/tmp/admit.out 2>&1 <<YAML
apiVersion: v1
kind: Pod
metadata: { name: $1 }
spec:
  automountServiceAccountToken: false
  securityContext: { runAsNonRoot: $3, runAsUser: 10001, seccompProfile: { type: RuntimeDefault } }
  containers:
    - name: c
      image: $2
      securityContext:
        runAsNonRoot: $3
        privileged: $4
        allowPrivilegeEscalation: false
        capabilities: { drop: [ALL] }
YAML
  if [ $? -eq 0 ]; then echo accepté; else echo refusé; fi
}
reason() { grep -oE "(edugrade-[a-z-]+|violates PodSecurity|policy [a-z-]+)[^;]*" /tmp/admit.out | head -1 | cut -c1-110; }

SIGNED="$(kubectl -n "$NS" get deploy backend -o jsonpath='{.spec.template.spec.containers[0].image}')"
r=$(admit t-signee "$SIGNED" true false);                         result "image EduGrade signée par develop (déployée)" accepté "$r"
r=$(admit t-autre-branche "$SIGNED_OTHER_BRANCH" true false);     result "image EduGrade signée par une autre branche" refusé "$r"; echo "    motif : $(reason)"
r=$(admit t-non-signee "ghcr.io/emirghdiri/edugrade-backend:non-signee" true false); result "image EduGrade non signée (tag local)" refusé "$r"; echo "    motif : $(reason)"
r=$(admit t-registre "busybox:1.37" true false);                  result "image d'un registre non autorisé (busybox)" refusé "$r"; echo "    motif : $(reason)"
r=$(admit t-latest "nginxinc/nginx-unprivileged:latest" true false); result "tag latest" refusé "$r"; echo "    motif : $(reason)"
r=$(admit t-root "$SIGNED" false false);                          result "pod sans runAsNonRoot (root possible)" refusé "$r"; echo "    motif : $(reason)"
r=$(admit t-privileged "$SIGNED" true true);                      result "conteneur privileged" refusé "$r"; echo "    motif : $(reason)"

echo
[ "$FAIL" -eq 0 ] && echo "RÉSULTAT : tous les tests sont conformes." || echo "RÉSULTAT : au moins un test n'est pas conforme."
exit "$FAIL"
