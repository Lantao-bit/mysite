terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "ylt202605201452"
    container_name       = "tfstate"
    key                  = "portfolio.terraform.tfstate"
  }
}

# State locking is automatic via Azure Blob lease mechanism — no additional configuration needed.
