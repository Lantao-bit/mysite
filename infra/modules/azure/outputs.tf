output "cluster_endpoint" {
  description = "AKS cluster API server endpoint URL"
  value       = azurerm_kubernetes_cluster.portfolio.kube_config[0].host
}

output "cluster_ca_data" {
  description = "Base64-encoded cluster CA certificate"
  value       = azurerm_kubernetes_cluster.portfolio.kube_config[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.portfolio.name
}

output "resource_group_name" {
  description = "Azure resource group name"
  value       = azurerm_resource_group.portfolio.name
}
