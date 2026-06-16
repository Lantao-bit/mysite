variable "region" {
  description = "SAP BTP region for the Kyma runtime"
  type        = string
}

variable "cluster_name" {
  description = "Name of the Kyma cluster"
  type        = string
}

variable "environment" {
  description = "Deploy target name (used for tagging)"
  type        = string
}

variable "project_name" {
  description = "Project name tag"
  type        = string
  default     = "portfolio"
}

variable "subaccount_id" {
  description = "SAP BTP Subaccount ID"
  type        = string
}

variable "kyma_plan" {
  description = "Kyma plan name (underlying hyperscaler: azure, aws, gcp)"
  type        = string
  default     = "azure"
}

variable "globalaccount" {
  description = "SAP BTP Global Account subdomain"
  type        = string
}

variable "cli_server_url" {
  description = "BTP CLI server URL for OAuth2 authentication"
  type        = string
  default     = "https://cli.btp.cloud.sap"
}
