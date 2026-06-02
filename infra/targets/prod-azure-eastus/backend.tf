terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "ylt202605201452"
    container_name       = "tfstate"
    key                  = "prod-azure-eastus.terraform.tfstate"
  }
}
