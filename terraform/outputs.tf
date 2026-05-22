output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.portfolio.name
}

output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.portfolio.name
}

output "aks_cluster_fqdn" {
  description = "FQDN of the AKS cluster API server"
  value       = azurerm_kubernetes_cluster.portfolio.fqdn
}

output "aks_node_resource_group" {
  description = "Auto-generated node resource group name"
  value       = azurerm_kubernetes_cluster.portfolio.node_resource_group
}

output "kube_config_raw" {
  description = "Full kubeconfig for cluster access"
  value       = azurerm_kubernetes_cluster.portfolio.kube_config_raw
  sensitive   = true
}

output "get_credentials_command" {
  description = "Ready-to-use az aks get-credentials command"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.portfolio.name} --name ${azurerm_kubernetes_cluster.portfolio.name}"
}

output "ingress_helm_commands" {
  description = "Helm install commands for nginx ingress controller and cert-manager (using static IP)"
  value       = <<-EOT
    # Add Helm repositories
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo add jetstack https://charts.jetstack.io
    helm repo update

    # Install nginx ingress controller with static IP
    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
      --namespace ingress-nginx \
      --create-namespace \
      --set controller.replicaCount=1 \
      --set controller.service.loadBalancerIP=${azurerm_public_ip.ingress.ip_address} \
      --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-resource-group"=${azurerm_resource_group.portfolio.name}

    # Install cert-manager for TLS certificates
    helm upgrade --install cert-manager jetstack/cert-manager \
      --namespace cert-manager \
      --create-namespace \
      --set crds.enabled=true
  EOT
}

output "ingress_public_ip" {
  description = "Static public IP for the NGINX Ingress Controller. Point your domain's A record here. This IP persists across cluster recreations."
  value       = azurerm_public_ip.ingress.ip_address
}

output "load_balancer_ip_command" {
  description = "Command to retrieve the load balancer external IP after ingress installation"
  value       = "kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
}
