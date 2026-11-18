# Sorties utiles pour relier le dépôt local et pour le rapport.
# Aucune sortie ne contient de secret.

output "repository_full_name" {
  description = "Nom complet du dépôt (propriétaire/nom)"
  value       = github_repository.edugrade.full_name
}

output "repository_url" {
  description = "URL web du dépôt"
  value       = github_repository.edugrade.html_url
}

output "clone_url_https" {
  description = "URL HTTPS à utiliser comme remote origin"
  value       = github_repository.edugrade.http_clone_url
}

output "protected_branch" {
  description = "Branche protégée"
  value       = github_branch_protection.main.pattern
}

output "actions_secrets" {
  description = "Noms (et non valeurs) des secrets GitHub Actions créés"
  value       = [github_actions_secret.app_secret_key.secret_name, github_actions_secret.postgres_password.secret_name]
}
