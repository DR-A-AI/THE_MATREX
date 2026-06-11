terraform {
  required_providers {
    # 1. Azure AD (For Entra ID Identity Management - Free)
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47.0"
    }
    
    # 2. GitHub (For Repo & Actions Management - Free)
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }

    # 3. Vercel (For Frontend & Edge API Hosting - Free Tier)
    vercel = {
      source  = "vercel/vercel"
      version = "~> 1.13.0"
    }

    # 4. Cloudflare (For DNS, CDN, and Workers - Free Tier)
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.25.0"
    }
  }
}

# Configure Microsoft Entra ID Provider (Using OIDC)
provider "azuread" {
  use_oidc  = true
  tenant_id = var.azure_tenant_id
}

# Configure GitHub Provider
provider "github" {
  owner = var.github_owner
  token = var.github_token
}

# Configure Vercel Provider
provider "vercel" {
  api_token = var.vercel_api_token
}

# Configure Cloudflare Provider
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
