module "azure" {
  source = "../../modules/azure"

  location            = "eastus"
  resource_group_name = "portfolio-rg-prod-azure-eastus"
  aks_cluster_name    = "portfolio-prod-azure-eastus"
  target_name         = "prod-azure-eastus"
  project_name        = "portfolio"
  kubernetes_version  = "1.34"
}

output "cluster_endpoint" {
  value     = module.azure.cluster_endpoint
  sensitive = true
}

output "cluster_name" {
  value = module.azure.cluster_name
}
