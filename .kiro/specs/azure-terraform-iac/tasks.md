# Implementation Plan: Azure Terraform IaC

## Overview

This plan implements Terraform Infrastructure-as-Code for the portfolio website's Azure infrastructure. Tasks progress from foundational provider/backend configuration through resource definitions, outputs, pipeline integration, and documentation. Each task produces valid HCL that builds on previous steps, culminating in a fully wired Terraform module integrated into the existing Azure DevOps CI/CD pipeline.

## Tasks

- [x] 1. Set up Terraform directory structure and provider configuration
  - [x] 1.1 Create `terraform/providers.tf` with required Terraform version constraint (>= 1.5.0), azurerm provider pinned to ~> 3.100, azuread provider pinned to ~> 2.50, and the azurerm provider features block with `prevent_deletion_if_contains_resources = false`
    - _Requirements: 10.1, 10.4_

  - [x] 1.2 Create `terraform/backend.tf` with azurerm backend block configured for Azure Blob Storage state backend (resource_group_name, storage_account_name placeholder, container_name from variable default, key set to `portfolio.terraform.tfstate`)
    - State locking is automatic via Azure Blob lease — no extra config needed
    - _Requirements: 4.1, 4.2_

- [x] 2. Define input variables with types, defaults, and validation
  - [x] 2.1 Create `terraform/variables.tf` with all input variable declarations: location, resource_group_name, aks_cluster_name, dns_prefix, node_vm_size, node_count, os_disk_size_gb, vnet_address_space, subnet_address_prefix, kubernetes_version, network_plugin, environment, project_name, enable_http_app_routing, state_container_name
    - Each variable must have explicit `type`, `description` (>= 10 chars), and `default` where applicable
    - Defaults: location = "eastus", node_count = 1, node_vm_size = "Standard_B2s", os_disk_size_gb = 30, vnet_address_space = "10.0.0.0/16", subnet_address_prefix = "10.0.1.0/24", kubernetes_version = "1.29", network_plugin = "kubenet"
    - _Requirements: 5.1, 5.2, 5.3, 10.5_

  - [x] 2.2 Add validation blocks to `terraform/variables.tf` for node_count (1–10) and os_disk_size_gb (30–1024) with descriptive error messages
    - _Requirements: 5.5, 3.2_

- [x] 3. Implement core infrastructure resources
  - [x] 3.1 Add resource group resource to `terraform/main.tf` — `azurerm_resource_group.portfolio` with configurable name, location, and tags (environment, project_name from variables)
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 3.2 Add virtual network resource to `terraform/main.tf` — `azurerm_virtual_network.portfolio` with name derived from resource group name, configurable address_space, located in the resource group
    - _Requirements: 2.1_

  - [x] 3.3 Add subnet resource to `terraform/main.tf` — `azurerm_subnet.aks` with name "aks-subnet", configurable address_prefixes, within the VNet
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 3.4 Add AKS cluster resource to `terraform/main.tf` — `azurerm_kubernetes_cluster.portfolio` with: default_node_pool (system, configurable node_count/vm_size/os_disk_size_gb, vnet_subnet_id), system-assigned identity, network_profile (kubenet, standard LB), dynamic http_application_routing block, dns_prefix, kubernetes_version, tags
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 9.1, 9.3_

- [x] 4. Checkpoint - Validate Terraform configuration
  - Ensure `terraform validate` passes on the terraform/ directory. Ask the user if questions arise.

- [x] 5. Define output values
  - [x] 5.1 Create `terraform/outputs.tf` with outputs: resource_group_name, aks_cluster_name, aks_cluster_fqdn, aks_node_resource_group, kube_config_raw (sensitive), get_credentials_command, ingress_helm_commands, load_balancer_ip_command
    - Each output must have a `description` attribute
    - Mark kube_config_raw as `sensitive = true`
    - get_credentials_command outputs a ready-to-use `az aks get-credentials` string
    - ingress_helm_commands outputs Helm install commands for nginx ingress + cert-manager
    - load_balancer_ip_command outputs the kubectl command to retrieve LB external IP
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 9.2, 9.4, 3.6_

- [x] 6. Create example tfvars and documentation
  - [x] 6.1 Create `terraform/terraform.tfvars.example` listing every variable name with a commented example value and one-line description
    - _Requirements: 5.4_

  - [x] 6.2 Create `terraform/README.md` with: required tool versions (Terraform CLI >= 1.5, Azure CLI), Azure authentication setup (service principal), bootstrap procedure for state backend storage account, commands for init/plan/apply/destroy workflows, architecture decisions summary, teardown procedure (drain workloads, delete PVCs, uninstall Helm charts, terraform destroy)
    - _Requirements: 10.2, 4.3, 8.2_

- [x] 7. Integrate Terraform stages into Azure DevOps pipeline
  - [x] 7.1 Add `TerraformPlan` stage to `azure-pipelines.yml` after the Test stage — runs `terraform init -input=false` and `terraform plan -input=false -out=tfplan`, publishes tfplan artifact, uses ARM_* env vars for service principal auth
    - _Requirements: 7.1, 7.3, 7.5_

  - [x] 7.2 Add `TerraformApply` stage to `azure-pipelines.yml` after TerraformPlan — downloads tfplan artifact, runs `terraform init` and `terraform apply -input=false` with the saved plan file, depends on TerraformPlan success
    - _Requirements: 7.2, 7.4, 7.6_

  - [x] 7.3 Update the existing `Build` stage `dependsOn` from `Test` to `TerraformApply` so infrastructure is provisioned before Docker build and K8s deploy
    - _Requirements: 7.3_

- [x] 8. Final checkpoint - Validate all files
  - Ensure `terraform validate` passes, `terraform fmt -check` passes, and the azure-pipelines.yml is valid YAML. Ask the user if questions arise.

## Notes

- No property-based tests apply to this feature — validation is via `terraform validate`, `terraform plan`, and `terraform fmt -check`
- The state backend storage account must be bootstrapped manually before first `terraform init` (documented in README)
- Pipeline variables ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_SUBSCRIPTION_ID, ARM_TENANT_ID must be configured as secret variables in Azure DevOps
- The `.terraform.lock.hcl` file will be generated on first `terraform init` and should be committed to version control
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "2.1"] },
    { "id": 1, "tasks": ["2.2", "3.1"] },
    { "id": 2, "tasks": ["3.2"] },
    { "id": 3, "tasks": ["3.3"] },
    { "id": 4, "tasks": ["3.4"] },
    { "id": 5, "tasks": ["5.1", "6.1", "6.2"] },
    { "id": 6, "tasks": ["7.1"] },
    { "id": 7, "tasks": ["7.2"] },
    { "id": 8, "tasks": ["7.3"] }
  ]
}
```
