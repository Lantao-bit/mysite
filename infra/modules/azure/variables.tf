variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region for all resources"
}

variable "resource_group_name" {
  type        = string
  default     = "portfolio-rg"
  description = "Name of the resource group"
}

variable "aks_cluster_name" {
  type        = string
  default     = "portfolio-aks"
  description = "Name of the AKS cluster"
}

variable "dns_prefix" {
  type        = string
  default     = "portfolio"
  description = "DNS prefix for AKS FQDN"
}

variable "node_vm_size" {
  type        = string
  default     = "Standard_D2s_v3"
  description = "VM size for node pool (Free Tier eligible)"
}

variable "node_count" {
  type        = number
  default     = 1
  description = "Number of nodes in the AKS default node pool (1-10)"

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 10
    error_message = "Node count must be between 1 and 10."
  }
}

variable "os_disk_size_gb" {
  type        = number
  default     = 30
  description = "OS disk size in GB for each node (30-1024)"

  validation {
    condition     = var.os_disk_size_gb >= 30 && var.os_disk_size_gb <= 1024
    error_message = "OS disk size must be between 30 and 1024 GB."
  }
}

variable "vnet_address_space" {
  type        = string
  default     = "10.0.0.0/16"
  description = "VNet CIDR block for the virtual network"
}

variable "subnet_address_prefix" {
  type        = string
  default     = "10.0.1.0/24"
  description = "AKS subnet CIDR address prefix"
}

variable "kubernetes_version" {
  type        = string
  default     = "1.34"
  description = "Kubernetes minor version for the AKS cluster"
}

variable "network_plugin" {
  type        = string
  default     = "azure"
  description = "AKS network plugin (kubenet or azure)"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment tag value for resource tagging"
}

variable "project_name" {
  type        = string
  default     = "portfolio"
  description = "Project tag value for resource tagging"
}

variable "enable_http_app_routing" {
  type        = bool
  default     = false
  description = "Enable AKS HTTP application routing add-on"
}
