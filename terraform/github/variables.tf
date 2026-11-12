# Variables d'entrée. Les valeurs réelles se trouvent dans terraform.tfvars,
# qui n'est jamais versionné (voir terraform.tfvars.example).

variable "github_owner" {
  description = "Compte GitHub propriétaire du dépôt"
  type        = string
}

variable "repository_name" {
  description = "Nom du dépôt du projet"
  type        = string
  default     = "edugrade-devsecops"
}

variable "repository_visibility" {
  description = "Visibilité du dépôt (public : la protection de branche est gratuite et toutes les données sont fictives)"
  type        = string
  default     = "public"

  validation {
    condition     = contains(["public", "private"], var.repository_visibility)
    error_message = "La visibilité doit être « public » ou « private »."
  }
}

variable "collaborator_username" {
  description = "Nom d'utilisateur GitHub de la binôme, ajoutée comme collaboratrice"
  type        = string
}

variable "required_status_check" {
  description = "Nom du job CI qui doit être vert avant toute fusion dans main"
  type        = string
  default     = "build-test"
}

# Valeurs factices uniquement : elles alimentent les GitHub Secrets de la CI.
variable "app_secret_key" {
  description = "SECRET_KEY Flask utilisée par la CI (valeur factice)"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "Mot de passe PostgreSQL de l'instance de test CI (valeur factice)"
  type        = string
  sensitive   = true
}
