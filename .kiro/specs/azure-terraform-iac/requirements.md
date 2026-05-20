# Requirements Document

## Introduction

This feature introduces Terraform Infrastructure-as-Code (IaC) to manage the Azure infrastructure for the personal portfolio website. The goal is to codify all Azure resources (AKS cluster, resource group, networking, and supporting services) so the environment is reproducible, version-controlled, and can be torn down and recreated consistently. The existing Kubernetes manifests and Azure DevOps CI/CD pipeline will continue to work with the Terraform-managed infrastructure.

## Glossary

- **Terraform_Module**: A self-contained Terraform configuration that provisions a specific set of related Azure resources
- **AKS_Cluster**: The Azure Kubernetes Service cluster that hosts the portfolio application containers
- **Resource_Group**: An Azure resource group that logically contains all related Azure resources for the portfolio
- **State_Backend**: The Azure Storage Account used to store Terraform state files remotely for collaboration and consistency
- **VNet**: The Azure Virtual Network providing network isolation for the AKS cluster
- **Terraform_Plan**: The output of `terraform plan` showing proposed infrastructure changes before they are applied
- **CI_CD_Pipeline**: The Azure DevOps pipeline that builds, tests, and deploys the application and infrastructure
- **Node_Pool**: The set of virtual machine nodes within the AKS cluster that run workloads

## Requirements

### Requirement 1: Resource Group Provisioning

**User Story:** As a developer, I want the Azure resource group defined in Terraform, so that all portfolio resources are grouped and can be created or destroyed as a unit.

#### Acceptance Criteria

1. WHEN `terraform apply` is executed, THE Terraform_Module SHALL create a resource group with a configurable name in a configurable Azure region that defaults to a documented value in the variables definition
2. THE Terraform_Module SHALL tag the resource group with an `environment` tag and a `project` tag, where both tag values are sourced from input variables
3. IF the resource group already exists and its name, region, and tags match the current Terraform state, THEN THE Terraform_Module SHALL report no changes required
4. IF the resource group provisioning fails due to insufficient permissions or an invalid region, THEN THE Terraform_Module SHALL exit with a non-zero status and display an error message indicating the failure reason

### Requirement 2: Virtual Network and Subnet Configuration

**User Story:** As a developer, I want networking resources defined in Terraform, so that the AKS cluster has proper network isolation and a predictable address space.

#### Acceptance Criteria

1. WHEN the resource group is provisioned, THE Terraform_Module SHALL create a Virtual Network with a configurable address space defaulting to 10.0.0.0/16
2. THE Terraform_Module SHALL create a dedicated subnet for the AKS node pool within the VNet with a configurable address prefix defaulting to 10.0.1.0/24
3. THE Terraform_Module SHALL output the subnet ID for use by the AKS cluster configuration
4. THE Terraform_Module SHALL size the subnet to accommodate the maximum configured node count plus AKS system pods

### Requirement 3: AKS Cluster Provisioning

**User Story:** As a developer, I want the AKS cluster defined in Terraform, so that the Kubernetes environment is reproducible and its configuration is version-controlled.

#### Acceptance Criteria

1. WHEN the VNet and subnet are provisioned, THE Terraform_Module SHALL create an AKS_Cluster with a system node pool and a configurable DNS prefix used to generate the cluster FQDN
2. THE Terraform_Module SHALL configure the default node pool with a configurable VM size, a node count between 1 and 10 with a default of 1, and an OS disk size between 30 GB and 1024 GB with a default of 30 GB
3. THE Terraform_Module SHALL enable the AKS cluster identity using a system-assigned managed identity
4. THE Terraform_Module SHALL configure the AKS_Cluster to use the provisioned subnet for pod networking with a configurable network plugin having a documented default of either "azure" or "kubenet"
5. THE Terraform_Module SHALL set Kubernetes version to a configurable value with a documented default that specifies a valid AKS-supported minor version in the format "X.Y"
6. THE Terraform_Module SHALL output the cluster host endpoint, cluster CA certificate, and client credentials sufficient to construct a kubeconfig for use by downstream deployment steps
7. IF the AKS_Cluster provisioning fails due to quota or capacity constraints, THEN THE Terraform_Module SHALL surface the Azure error message in the Terraform output without masking the root cause

### Requirement 4: Terraform State Backend

**User Story:** As a developer, I want Terraform state stored remotely in Azure Storage, so that state is not lost and infrastructure changes are safe from local machine failures.

#### Acceptance Criteria

1. THE Terraform_Module SHALL configure an Azure Storage Account as the remote state backend with state locking enabled via Azure Blob lease mechanism
2. THE Terraform_Module SHALL store state in a dedicated blob container with a configurable container name and a configurable state file key (blob name)
3. THE Terraform_Module SHALL document the one-time bootstrap procedure for creating the storage account and container before first use, including required storage account settings and authentication configuration
4. IF the remote state backend is unreachable during `terraform plan` or `terraform apply`, THEN THE Terraform_Module SHALL fail with an error indicating the backend connectivity issue without modifying local or remote state

### Requirement 5: Variable Parameterization

**User Story:** As a developer, I want all environment-specific values parameterized as Terraform variables, so that the configuration can be reused across environments without code changes.

#### Acceptance Criteria

1. THE Terraform_Module SHALL expose variables for Azure region, resource group name, AKS cluster name, node VM size, node count, VNet address space, subnet address prefix, Kubernetes version, OS disk size, and state backend container name
2. THE Terraform_Module SHALL define each variable with an explicit type constraint and a description string of at least 10 characters explaining the variable's purpose
3. THE Terraform_Module SHALL provide default values for all variables where the defaults are: node count of 1, VM size of Standard_B2s, OS disk size of 30 GB, and Azure region of a documented single region
4. THE Terraform_Module SHALL include a `terraform.tfvars.example` file that lists every variable name with a commented example value and a one-line description of its effect
5. IF a variable value fails its type constraint or validation rule, THEN THE Terraform_Module SHALL reject the input at plan time with an error message indicating which variable is invalid and what values are accepted

### Requirement 6: Terraform Output Values

**User Story:** As a developer, I want Terraform to output key resource identifiers, so that the CI/CD pipeline and Kubernetes manifests can reference the provisioned infrastructure.

#### Acceptance Criteria

1. THE Terraform_Module SHALL output the resource group name, AKS cluster name, and AKS cluster FQDN as named outputs in `outputs.tf` with descriptive `description` attributes for each
2. THE Terraform_Module SHALL output a ready-to-use `az aks get-credentials` command string containing the resource group name and cluster name for local kubectl access
3. THE Terraform_Module SHALL output the AKS-managed node pool resource group name as a named output
4. THE Terraform_Module SHALL mark outputs that contain credential-related data or cluster access information as `sensitive = true`

### Requirement 7: CI/CD Pipeline Integration

**User Story:** As a developer, I want Terraform plan and apply integrated into the Azure DevOps pipeline, so that infrastructure changes are reviewed and applied automatically alongside application deployments.

#### Acceptance Criteria

1. WHEN a commit is pushed to the main branch, THE CI_CD_Pipeline SHALL execute `terraform init` followed by `terraform plan` and publish the plan output to the pipeline stage logs
2. WHEN the plan stage succeeds and detects infrastructure changes, THE CI_CD_Pipeline SHALL execute `terraform apply` with the saved plan file to provision or update infrastructure
3. THE CI_CD_Pipeline SHALL run Terraform stages after the test stage and before the application build and deploy stages
4. IF `terraform plan` detects no changes, THEN THE CI_CD_Pipeline SHALL skip the apply step and proceed to the application build stage
5. THE CI_CD_Pipeline SHALL use a service principal or managed identity for Azure authentication during Terraform operations
6. IF `terraform plan` or `terraform apply` fails with a non-zero exit code, THEN THE CI_CD_Pipeline SHALL halt execution and mark the pipeline run as failed without proceeding to subsequent stages

### Requirement 8: Infrastructure Teardown

**User Story:** As a developer, I want the ability to destroy all Terraform-managed resources with a single command, so that I can cleanly remove the environment when needed.

#### Acceptance Criteria

1. WHEN `terraform destroy` is executed, THE Terraform_Module SHALL remove all provisioned Azure resources in the correct dependency order as determined by the Terraform dependency graph
2. THE Terraform_Module SHALL document the teardown procedure including: draining Kubernetes workloads, removing persistent volume claims, and confirming no external dependencies reference the resources
3. IF `terraform destroy` encounters a resource that cannot be deleted due to locks or dependencies, THEN THE Terraform_Module SHALL report the blocking resource and reason without leaving state in an inconsistent condition
4. THE State_Backend storage account and container SHALL NOT be destroyed by `terraform destroy` since they exist outside the managed state

### Requirement 9: AKS Add-on Configuration

**User Story:** As a developer, I want the nginx ingress controller and cert-manager support configured through Terraform, so that TLS termination infrastructure is reproducible.

#### Acceptance Criteria

1. THE Terraform_Module SHALL configure the AKS_Cluster network profile with a network plugin and a Standard SKU load balancer to support external LoadBalancer service allocation for the nginx ingress controller
2. WHEN the AKS_Cluster is provisioned, THE Terraform_Module SHALL output a Terraform output value containing the Helm commands and namespace references needed to install the nginx ingress controller and cert-manager, including chart repository URLs and target namespace names
3. THE Terraform_Module SHALL expose a variable to select between enabling the AKS HTTP application routing add-on or relying on a manual nginx ingress controller installation via Helm
4. IF the HTTP application routing add-on is not enabled, THEN THE Terraform_Module SHALL output the load balancer public IP address or the command to retrieve it after ingress controller installation

### Requirement 10: Project Structure and Documentation

**User Story:** As a developer, I want the Terraform code organized in a clear directory structure with documentation, so that the infrastructure code is maintainable and understandable.

#### Acceptance Criteria

1. THE Terraform_Module SHALL organize files into `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, and `backend.tf` within a dedicated `terraform/` directory
2. THE Terraform_Module SHALL include a README containing at minimum: required tool versions (Terraform CLI, Azure CLI), Azure authentication setup steps, commands for `terraform init`, `plan`, `apply`, and `destroy` workflows, and a summary of architecture decisions explaining resource dependencies
3. THE Terraform_Module SHALL include a `.terraform.lock.hcl` committed to version control for provider version pinning
4. THE Terraform_Module SHALL pin the `azurerm` and `azuread` providers using the pessimistic constraint operator (`~>`) with a specific minor version to allow only patch-level updates
5. THE Terraform_Module SHALL include a `type`, `description`, and `default` (where applicable) for every variable defined in `variables.tf`
