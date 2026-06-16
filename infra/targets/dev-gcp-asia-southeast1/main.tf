module "gcp" {
  source = "../../modules/gcp"

  region       = "asia-southeast1"
  cluster_name = "portfolio-dev-gcp-asia-southeast1"
  project_id   = "portfolio-gcp"
  environment  = "dev-gcp-asia-southeast1"
  project_name = "portfolio"
  k8s_version  = "1.31"
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
