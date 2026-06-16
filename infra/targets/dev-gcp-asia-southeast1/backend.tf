terraform {
  backend "gcs" {
    bucket = "portfolio-tfstate-gcp"
    prefix = "dev-gcp-asia-southeast1/terraform.tfstate"
  }
}
