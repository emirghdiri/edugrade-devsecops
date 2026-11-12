variable "kubeconfig_path" {
  description = "Chemin du kubeconfig du cluster k3s"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Contexte kubeconfig à utiliser"
  type        = string
  default     = "default"
}

variable "app_namespace" {
  description = "Namespace de l'application"
  type        = string
  default     = "edugrade"
}

variable "monitoring_namespace" {
  description = "Namespace de l'observabilité (Prometheus, Grafana, Loki, Alloy)"
  type        = string
  default     = "monitoring"
}

# Versions épinglées des charts Helm (mises à jour par Pull Request).
variable "chart_versions" {
  description = "Versions des charts Helm"
  type        = map(string)
  default = {
    kyverno               = "3.10.0"
    kube_prometheus_stack = "93.2.2"
    loki                  = "7.6.0"
    alloy                 = "1.15.0"
  }
}
