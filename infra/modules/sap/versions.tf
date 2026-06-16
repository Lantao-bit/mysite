terraform {
  required_version = ">= 1.0"

  required_providers {
    btp = {
      source  = "sap/btp"
      version = "~> 1.0"
    }
  }
}

# Authentication via service credentials (OAuth2 client credentials)
# Environment variables: BTP_CLI_SERVER_URL, BTP_CLIENT_ID, BTP_CLIENT_SECRET
provider "btp" {
  globalaccount  = var.globalaccount
  cli_server_url = var.cli_server_url
}
