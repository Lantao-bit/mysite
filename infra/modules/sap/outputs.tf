output "cluster_name" {
  description = "Kyma cluster name"
  value       = btp_subaccount_environment_instance.kyma.name
}

output "kubeconfig_url" {
  description = "URL to download kubeconfig for the Kyma cluster"
  value       = btp_subaccount_environment_instance.kyma.dashboard_url
}
