terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = {
    target     = var.environment
    project    = var.project_name
    managed_by = "terraform"
  }
}
