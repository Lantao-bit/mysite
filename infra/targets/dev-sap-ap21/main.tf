module "sap" {
  source = "../../modules/sap"

  region         = "ap21"
  cluster_name   = "portfolio-dev-sap-ap21"
  environment    = "dev-sap-ap21"
  project_name   = "portfolio"
  subaccount_id  = var.subaccount_id
  globalaccount  = var.globalaccount
  kyma_plan      = "trial"
}

variable "subaccount_id" {
  description = "SAP BTP Subaccount ID (from SAP_BTP_SUBACCOUNT_ID env var)"
  type        = string
  default     = ""
}

variable "globalaccount" {
  description = "SAP BTP Global Account subdomain (from BTP_GLOBALACCOUNT env var)"
  type        = string
  default     = ""
}

output "cluster_name" {
  value = module.sap.cluster_name
}

output "kubeconfig_url" {
  value = module.sap.kubeconfig_url
}
