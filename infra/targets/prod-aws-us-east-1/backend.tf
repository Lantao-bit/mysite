terraform {
  backend "s3" {
    bucket         = "portfolio-tfstate-712416941115"
    key            = "prod-aws-us-east-1/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "portfolio-tfstate-lock"
    encrypt        = true
  }
}
