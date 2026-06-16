terraform {
  backend "s3" {
    bucket       = "portfolio-tfstate-712416941115"
    key          = "dev-alicloud-cn-hangzhou/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}
