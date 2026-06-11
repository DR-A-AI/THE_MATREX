variable "azure_tenant_id" {
  type        = string
  description = "The Tenant ID for Microsoft Entra ID"
}

variable "github_owner" {
  type        = string
  description = "The GitHub organization or username"
}

variable "github_token" {
  type        = string
  description = "GitHub Personal Access Token"
  sensitive   = true
}

variable "vercel_api_token" {
  type        = string
  description = "Vercel API Token for deployment"
  sensitive   = true
}

variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API Token for Edge configuration"
  sensitive   = true
}
