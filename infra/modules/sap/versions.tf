terraform {
  required_version = ">= 1.0"

  required_providers {
    btp = {
      source  = "sap/btp"
      version = "~> 1.0"
    }
  }
}

# Authentication via BTP_USERNAME and BTP_PASSWORD environment variables
provider "btp" {
  globalaccount = var.globalaccount
}
