# ---------------------------------------------------------------------------
# Outillage installé par Helm (versions épinglées dans variables.tf).
# Charts téléchargés au préalable par scripts/fetch_charts.sh dans charts/
# (ignoré par git) : plan et apply ne dépendent pas du réseau.
# ---------------------------------------------------------------------------

# Kyverno : contrôleur d'admission. Les règles EduGrade (image signée,
# non-root, pas de privileged, pas de latest) sont dans policies/kyverno/.
resource "helm_release" "kyverno" {
  name             = "kyverno"
  chart            = "${path.module}/charts/kyverno-${var.chart_versions.kyverno}.tgz"
  namespace        = "kyverno"
  create_namespace = true
  timeout          = 900
  values           = [file("${path.module}/values/kyverno.yaml")]
}

# Règles Kyverno EduGrade, empaquetées en mini-chart (policies/kyverno) pour
# être installées après les CRD de Kyverno.
resource "helm_release" "kyverno_policies" {
  name       = "edugrade-policies"
  chart      = "${path.module}/../../policies/kyverno"
  namespace  = "kyverno"
  depends_on = [helm_release.kyverno]
}

# Prometheus, Alertmanager, Grafana (+ datasource Loki, tableaux de bord et
# alertes provisionnés par ConfigMap).
resource "helm_release" "kube_prometheus_stack" {
  name       = "kps"
  chart      = "${path.module}/charts/kube-prometheus-stack-${var.chart_versions.kube_prometheus_stack}.tgz"
  namespace  = kubernetes_namespace_v1.monitoring.metadata[0].name
  timeout    = 900
  values     = [file("${path.module}/values/kube-prometheus-stack.yaml")]
  depends_on = [kubernetes_secret_v1.grafana_admin]
}

# Loki (mode SingleBinary, stockage fichier) : journaux JSON de l'application.
resource "helm_release" "loki" {
  name      = "loki"
  chart     = "${path.module}/charts/loki-${var.chart_versions.loki}.tgz"
  namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  timeout   = 600
  values    = [file("${path.module}/values/loki.yaml")]
}

# Alloy : collecte les journaux des pods du namespace edugrade via l'API
# Kubernetes (aucun accès hostPath) et les envoie à Loki.
resource "helm_release" "alloy" {
  name       = "alloy"
  chart      = "${path.module}/charts/alloy-${var.chart_versions.alloy}.tgz"
  namespace  = kubernetes_namespace_v1.monitoring.metadata[0].name
  timeout    = 600
  values     = [file("${path.module}/values/alloy.yaml")]
  depends_on = [helm_release.loki]
}

# Tableau de bord « Sécurité EduGrade » et règle d'alerte, chargés par les
# sidecars de Grafana (labels grafana_dashboard / grafana_alert).
resource "kubernetes_config_map_v1" "grafana_dashboard" {
  metadata {
    name      = "edugrade-securite-dashboard"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
    labels    = { grafana_dashboard = "1" }
  }
  data = {
    "edugrade-securite.json" = file("${path.module}/grafana/dashboard-securite.json")
  }
}

resource "kubernetes_config_map_v1" "grafana_alerts" {
  metadata {
    name      = "edugrade-securite-alertes"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
    labels    = { grafana_alert = "1" }
  }
  data = {
    "edugrade-alertes.yaml" = file("${path.module}/grafana/alertes.yaml")
  }
}
