output "cluster_endpoint" {
  description = "ACK cluster API server endpoint URL"
  value       = alicloud_cs_managed_kubernetes.main.connections["api_server_internet"]
}

output "cluster_name" {
  description = "ACK cluster name"
  value       = alicloud_cs_managed_kubernetes.main.name
}

output "acr_registry_url" {
  description = "Alibaba Container Registry URL"
  value       = "registry.${var.region}.aliyuncs.com/${alicloud_cr_namespace.main.name}/${alicloud_cr_repo.main.name}"
}
