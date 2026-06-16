terraform {
  backend "s3" {
    bucket       = "portfolio-tfstate-712416941115"
    key          = "dev-sap-ap21/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}
