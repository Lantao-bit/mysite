module "azure" {
  source = "../../modules/azure"

  location            = "eastus"
  resource_group_name = "portfolio-rg"
  aks_cluster_name    = "portfolio-aks"
  environment         = "prod"
  project_name        = "portfolio"
  kubernetes_version  = "1.34"
}

output "cluster_endpoint" {
  description = "AKS cluster API server endpoint URL"
  value       = module.azure.cluster_endpoint
  sensitive   = true
}

output "cluster_ca_data" {
  description = "Base64-encoded cluster CA certificate"
  value       = module.azure.cluster_ca_data
  sensitive   = true
}

output "cluster_name" {
  description = "AKS cluster name"
  value       = module.azure.cluster_name
}
