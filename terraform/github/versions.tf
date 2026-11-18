# Versions de Terraform et du provider GitHub.
# Le provider est épinglé pour que tous les membres obtiennent exactement
# le même comportement ; le fichier .terraform.lock.hcl est versionné.

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "= 6.13.0"
    }
  }
}

# Le jeton n'est jamais écrit dans le code : le provider lit la variable
# d'environnement GITHUB_TOKEN (export GITHUB_TOKEN=$(gh auth token)).
provider "github" {
  owner = var.github_owner
}
