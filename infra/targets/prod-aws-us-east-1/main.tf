module "aws" {
  source = "../../modules/aws"

  region       = "us-east-1"
  cluster_name = "portfolio-eks"
  environment  = "prod"
  project_name = "portfolio"
  vpc_cidr     = "10.1.0.0/16"
  instance_type = "t3.small"
  k8s_version  = "1.31"
}

output "cluster_endpoint" {
  description = "EKS cluster API server endpoint URL"
  value       = module.aws.cluster_endpoint
}

output "cluster_ca_data" {
  description = "Base64-encoded cluster CA certificate"
  value       = module.aws.cluster_ca_data
  sensitive   = true
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.aws.cluster_name
}

output "ecr_repo_url" {
  description = "Full ECR repository URL"
  value       = module.aws.ecr_repository_url
}
