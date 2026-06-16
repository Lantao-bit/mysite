terraform {
  backend "oss" {
    bucket = "portfolio-tfstate-ali"
    prefix = "dev-alicloud-cn-hangzhou/terraform.tfstate"
    region = "cn-hangzhou"
  }
}
