module "sap" {
  source = "../../modules/sap"

  region         = "ap21"
  cluster_name   = "portfolio-dev-sap-ap21"
  environment    = "dev-sap-ap21"
  project_name   = "portfolio"
  subaccount_id  = "placeholder-subaccount-id"
  globalaccount  = "placeholder-globalaccount"
}

output "cluster_name" {
  value = module.sap.cluster_name
}

output "kubeconfig_url" {
  value = module.sap.kubeconfig_url
}
