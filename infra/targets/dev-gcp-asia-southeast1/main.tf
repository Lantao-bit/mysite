variable "project_id" {
  description = "GCP project ID (passed via TF_VAR_project_id from pipeline secrets)"
  type        = string
}

module "gcp" {
  source = "../../modules/gcp"

  region       = "asia-southeast1"
  cluster_name = "portfolio-dev-gcp-asia-southeast1"
  project_id   = var.project_id
  environment  = "dev-gcp-asia-southeast1"
  project_name = "portfolio"
  k8s_version  = "1.35.5-gke.1241000"
}

output "cluster_endpoint" {
  value = module.gcp.cluster_endpoint
}

output "cluster_name" {
  value = module.gcp.cluster_name
}

output "artifact_registry_url" {
  value = module.gcp.artifact_registry_url
}
