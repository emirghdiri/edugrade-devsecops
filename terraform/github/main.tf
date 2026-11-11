# ---------------------------------------------------------------------------
# Dépôt du projet
# Le dépôt est déclaré en code pour que sa configuration soit relue,
# versionnée et reproductible au lieu d'être cliquée dans l'interface.
# ---------------------------------------------------------------------------
resource "github_repository" "edugrade" {
  name        = var.repository_name
  description = "EduGrade : portail de gestion de notes (projet DevSecOps ING-5-SSIR, données fictives)"
  visibility  = var.repository_visibility

  has_issues   = true
  has_projects = false
  has_wiki     = false

  # auto_init crée un premier commit sur main : il faut une branche source
  # pour pouvoir créer develop et protéger main dans le même apply.
  auto_init = true

  # Les branches feature/* et fix/* disparaissent après fusion : le dépôt
  # reste lisible et on ne réutilise pas une branche déjà fusionnée.
  delete_branch_on_merge = true

  # Fusion par commit de merge uniquement : l'historique garde la trace de
  # chaque Pull Request.
  allow_merge_commit = true
  allow_squash_merge = false
  allow_rebase_merge = false
}

# Alertes Dependabot sur les dépendances vulnérables (complète Trivy).
# Ressource dédiée : l'argument vulnerability_alerts de github_repository
# est déprécié depuis le provider 6.x.
resource "github_repository_vulnerability_alerts" "edugrade" {
  repository = github_repository.edugrade.name
  enabled    = true
}

# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

# develop : branche d'intégration ; toutes les branches de travail en partent
# et y reviennent par Pull Request.
resource "github_branch" "develop" {
  repository    = github_repository.edugrade.name
  branch        = "develop"
  source_branch = "main"
}

# main reste la branche par défaut : c'est la version livrée.
resource "github_branch_default" "main" {
  repository = github_repository.edugrade.name
  branch     = "main"
}

