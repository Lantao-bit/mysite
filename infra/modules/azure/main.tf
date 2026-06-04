resource "azurerm_resource_group" "portfolio" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    project     = var.project_name
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
    type            = "VirtualMachineScaleSets"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }

  http_application_routing_enabled = var.enable_http_app_routing

  tags = {
    environment = var.environment
    project     = var.project_name
  }
}
