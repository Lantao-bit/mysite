# -----------------------------------------------------------------------------
# SAP BTP Kyma Runtime
# -----------------------------------------------------------------------------

# Reference the existing BTP subaccount
data "btp_subaccount" "main" {
  id = var.subaccount_id
}

# Kyma environment instance
resource "btp_subaccount_environment_instance" "kyma" {
  subaccount_id    = data.btp_subaccount.main.id
  name             = var.cluster_name
  environment_type = "kyma"
  service_name     = "kymaruntime"
  plan_name        = var.kyma_plan

  parameters = jsonencode({
    name   = var.cluster_name
    region = var.region
  })
}
