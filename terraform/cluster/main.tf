# ---------------------------------------------------------------------------
# Namespaces
# edugrade : Pod Security Admission « restricted » imposée par l'API server
# (non-root, pas de privilège, seccomp, capacités retirées), en plus de Kyverno.
# ---------------------------------------------------------------------------
resource "kubernetes_namespace_v1" "edugrade" {
  metadata {
    name = var.app_namespace
    labels = {
      "app.kubernetes.io/part-of"                  = "edugrade"
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "latest"
      "pod-security.kubernetes.io/warn"            = "restricted"
      "pod-security.kubernetes.io/audit"           = "restricted"
    }
  }
}

resource "kubernetes_namespace_v1" "monitoring" {
  metadata {
    name = var.monitoring_namespace
    labels = {
      "app.kubernetes.io/part-of" = "edugrade"
      # node-exporter et Alloy ont besoin d'accès à l'hôte : « privileged »
      # est limité à ce namespace d'outillage, jamais à l'application.
      "pod-security.kubernetes.io/enforce" = "privileged"
    }
  }
}

# ---------------------------------------------------------------------------
# Secrets Kubernetes
# Valeurs générées par Terraform : elles n'existent ni dans le code ni dans
# git (seulement dans l'état local terraform.tfstate, ignoré par git).
# ---------------------------------------------------------------------------
resource "random_password" "app_secret_key" {
  length  = 48
  special = false
}

resource "random_password" "postgres" {
  length  = 32
  special = false
}

resource "random_password" "grafana_admin" {
  length  = 24
  special = false
}

resource "kubernetes_secret_v1" "app" {
  metadata {
    name      = "edugrade-app"
    namespace = kubernetes_namespace_v1.edugrade.metadata[0].name
  }
  data = {
    SECRET_KEY = random_password.app_secret_key.result
  }
  type = "Opaque"
}

resource "kubernetes_secret_v1" "db" {
  metadata {
    name      = "edugrade-db"
    namespace = kubernetes_namespace_v1.edugrade.metadata[0].name
  }
  data = {
    POSTGRES_PASSWORD = random_password.postgres.result
  }
  type = "Opaque"
}

resource "kubernetes_secret_v1" "grafana_admin" {
  metadata {
    name      = "grafana-admin"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
  data = {
    admin-user     = "admin"
    admin-password = random_password.grafana_admin.result
  }
  type = "Opaque"
}
