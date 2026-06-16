terraform {
  required_version = ">= 1.0"

  required_providers {
    btp = {
      source  = "sap/btp"
      version = "~> 1.0"
    }
  }
}
