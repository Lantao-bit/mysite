resource "azurerm_resource_group" "portfolio" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    project     = var.project_name
  }
}

resource "azurerm_virtual_network" "portfolio" {
  name                = "${var.resource_group_name}-vnet"
  location            = azurerm_resource_group.portfolio.location
  resource_group_name = azurerm_resource_group.portfolio.name
  address_space       = [var.vnet_address_space]
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.portfolio.name
  virtual_network_name = azurerm_virtual_network.portfolio.name
  address_prefixes     = [var.subnet_address_prefix]
}

# Static public IP for the NGINX Ingress Controller LoadBalancer.
# This IP survives cluster recreation so DNS never needs updating.
resource "azurerm_public_ip" "ingress" {
  name                = "${var.aks_cluster_name}-ingress-ip"
  location            = azurerm_resource_group.portfolio.location
  resource_group_name = azurerm_resource_group.portfolio.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = {
    environment = var.environment
    project     = var.project_name
    purpose     = "ingress-nginx"
  }
}

resource "azurerm_kubernetes_cluster" "portfolio" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.portfolio.location
  resource_group_name = azurerm_resource_group.portfolio.name
  dns_prefix          = var.dns_prefix
  kubernetes_version  = var.kubernetes_version
  oidc_issuer_enabled = true

  default_node_pool {
    name            = "system"
    node_count      = var.node_count
    vm_size         = var.node_vm_size
    os_disk_size_gb = var.os_disk_size_gb
    vnet_subnet_id  = azurerm_subnet.aks.id
    type            = "VirtualMachineScaleSets"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = var.network_plugin
    load_balancer_sku = "standard"
    service_cidr      = "172.16.0.0/16"
    dns_service_ip    = "172.16.0.10"
  }

  http_application_routing_enabled = var.enable_http_app_routing

  tags = {
    environment = var.environment
    project     = var.project_name
  }
}

# NOTE: The AKS managed identity needs "Network Contributor" on this resource group
# to bind the static IP to the ingress LoadBalancer. This role assignment must be
# created manually (requires Owner/User Access Administrator permissions):
#
#   AKS_IDENTITY=$(az aks show --name portfolio-aks --resource-group portfolio-rg --query "identity.principalId" -o tsv)
#   az role assignment create --assignee "$AKS_IDENTITY" --role "Network Contributor" \
#     --scope /subscriptions/<SUB_ID>/resourceGroups/portfolio-rg
#
# This only needs to be done once after each cluster creation.
