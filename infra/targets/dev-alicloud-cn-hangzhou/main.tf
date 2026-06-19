module "alicloud" {
  source = "../../modules/alicloud"

  region       = "cn-hangzhou"
  cluster_name = "portfolio-dev-alicloud-cn-hangzhou"
  environment  = "dev-alicloud-cn-hangzhou"
  project_name = "portfolio"
  vpc_cidr     = "10.4.0.0/16"
  k8s_version  = "1.35"
}

output "cluster_endpoint" {
  value = module.alicloud.cluster_endpoint
}

output "cluster_name" {
  value = module.alicloud.cluster_name
}
