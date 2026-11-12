# ---------------------------------------------------------------------------
# NetworkPolicies du namespace edugrade (type kubernetes_network_policy, analysé
# par les règles KUBE-* de Trivy ; appliquées par le contrôleur
# kube-router intégré à k3s).
#
# Principe : tout est interdit par défaut, puis seuls les flux nécessaires sont
# ouverts :
#   Traefik (kube-system) ──8080──▶ frontend ──8000──▶ backend ──5432──▶ db
# Le frontend ne peut PAS joindre la base (test de segmentation).
# ---------------------------------------------------------------------------
locals {
  ns = kubernetes_namespace_v1.edugrade.metadata[0].name
  app_labels = {
    frontend = { "app.kubernetes.io/name" = "frontend" }
    backend  = { "app.kubernetes.io/name" = "backend" }
    db       = { "app.kubernetes.io/name" = "db" }
  }
}

# 1. Interdiction par défaut, entrée ET sortie, pour tous les pods.
resource "kubernetes_network_policy" "default_deny" {
  metadata {
    name      = "default-deny-all"
    namespace = local.ns
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

# 2. Résolution DNS (CoreDNS) autorisée pour tous les pods.
resource "kubernetes_network_policy" "allow_dns" {
  metadata {
    name      = "allow-dns"
    namespace = local.ns
  }
  spec {
    pod_selector {}
    policy_types = ["Egress"]
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}

# 3. Frontend : reçoit uniquement Traefik (Ingress k3s), ne parle qu'au backend.
resource "kubernetes_network_policy" "frontend" {
  metadata {
    name      = "frontend"
    namespace = local.ns
  }
  spec {
    pod_selector {
      match_labels = local.app_labels.frontend
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "app.kubernetes.io/name" = "traefik" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "8080"
      }
    }
    egress {
      to {
        pod_selector {
          match_labels = local.app_labels.backend
        }
      }
      ports {
        protocol = "TCP"
        port     = "8000"
      }
    }
  }
}

# 4. Backend : reçoit uniquement le frontend, ne parle qu'à la base.
resource "kubernetes_network_policy" "backend" {
  metadata {
    name      = "backend"
    namespace = local.ns
  }
  spec {
    pod_selector {
      match_labels = local.app_labels.backend
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        pod_selector {
          match_labels = local.app_labels.frontend
        }
      }
      ports {
        protocol = "TCP"
        port     = "8000"
      }
    }
    # Correctif V5 : plus de sortie vers 0.0.0.0/0. Le backend ne joint que la
    # base (et le DNS, policy allow-dns) ; les mises à jour passent par une
    # nouvelle image construite et signée par le pipeline, jamais par le pod.
    egress {
      to {
        pod_selector {
          match_labels = local.app_labels.db
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
  }
}

# 5. Base de données : reçoit uniquement le backend, aucune sortie.
resource "kubernetes_network_policy" "db" {
  metadata {
    name      = "db"
    namespace = local.ns
  }
  spec {
    pod_selector {
      match_labels = local.app_labels.db
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        pod_selector {
          match_labels = local.app_labels.backend
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
  }
}
