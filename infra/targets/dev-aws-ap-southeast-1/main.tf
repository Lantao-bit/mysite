module "aws" {
  source = "../../modules/aws"

  region       = "ap-southeast-1"
  cluster_name = "portfolio-dev-aws-ap-southeast-1"
  environment  = "dev-aws-ap-southeast-1"
  project_name = "portfolio"
  vpc_cidr     = "10.4.0.0/16"
  instance_type = "t3.medium"
  k8s_version  = "1.36"
  create_ecr   = false

  cluster_admin_arns = [
    "arn:aws:iam::712416941115:user/OFP_Admin",
  ]
}

output "cluster_endpoint" {
  value = module.aws.cluster_endpoint
}

output "cluster_name" {
  value = module.aws.cluster_name
}

output "ecr_repo_url" {
  value = module.aws.ecr_repository_url
}
