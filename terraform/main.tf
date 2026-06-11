# ==========================================
# 🛡️ THE MATRIX: OMNIPOTENT ZERO-COST CORE
# ==========================================

# 1. ENTRA ID (Azure AD): Matrix Identity Management
# The Matrix creates an App Registration to control Clerk Auth Sync and Graph API
resource "azuread_application" "matrix_clerk_sync" {
  display_name = "Matrix-Clerk-Identity-Sync"
  sign_in_audience = "AzureADMyOrg"
  
  web {
    redirect_uris = ["https://matrix.dashboard.local/oauth/callback"]
    implicit_grant {
      access_token_issuance_enabled = true
      id_token_issuance_enabled     = true
    }
  }
}

# 2. GITHUB: Matrix Code Automation
# The Matrix manages its own repositories and CI/CD pipelines
resource "github_repository" "matrix_edge_nodes" {
  name        = "matrix-edge-nodes"
  description = "Auto-generated repository for Matrix Edge Computing Nodes"
  visibility  = "private"
  auto_init   = true
}

# 3. VERCEL: Matrix Frontend Deployment (Chrome Dev Tools Integration Target)
# Deploying the React Dashboard automatically to Vercel's global edge network
resource "vercel_project" "matrix_dashboard" {
  name      = "matrix-sovereign-dashboard"
  framework = "vite"
  
  git_repository = {
    type = "github"
    repo = github_repository.matrix_edge_nodes.full_name
  }
}

# 4. CLOUDFLARE: Matrix Global Shield
# Setting up DNS and Edge firewall rules for ultimate protection
# resource "cloudflare_zone" "matrix_domain" {
#   account_id = var.cloudflare_account_id
#   zone       = "the-matrix-sovereign.local"
# }

# Output the ultimate App ID that Clerk Auth will use to sync with Entra ID
output "entra_app_client_id" {
  value = azuread_application.matrix_clerk_sync.client_id
  description = "Inject this Client ID into Clerk Auth for Entra ID Federation."
}
