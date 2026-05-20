# Azure Terraform Infrastructure

Terraform configuration for provisioning the portfolio website's Azure infrastructure: resource group, virtual network, subnet, and AKS cluster.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Terraform CLI | >= 1.5.0 | Infrastructure provisioning |
| Azure CLI | Latest | Azure authentication and bootstrap |
| kubectl | Latest | Kubernetes cluster access |

## Azure Authentication Setup

Terraform authenticates to Azure using a service principal. Create one and export the credentials as environment variables.

### Create a Service Principal

```bash
az ad sp create-for-rbac \
  --name "terraform-portfolio" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>
```

This outputs `appId`, `password`, `tenant`, and `displayName`.

### Set Environment Variables

```bash
export ARM_CLIENT_ID="<appId>"
export ARM_CLIENT_SECRET="<password>"
export ARM_SUBSCRIPTION_ID="<subscription-id>"
export ARM_TENANT_ID="<tenant>"
```

These variables are read automatically by the `azurerm` provider. In Azure DevOps, configure them as secret pipeline variables.

## Bootstrap State Backend

A one-time procedure to create the storage account used for remote Terraform state. This resource group is intentionally separate from the portfolio resources and survives `terraform destroy`.

```bash
# Create resource group for state (separate from portfolio resources)
az group create --name tfstate-rg --location eastus

# Create storage account (name must be globally unique)
az storage account create \
  --name <unique-storage-name> \
  --resource-group tfstate-rg \
  --sku Standard_LRS \
  --encryption-services blob \
  --min-tls-version TLS1_2

# Create blob container
az storage container create \
  --name tfstate \
  --account-name <unique-storage-name>
```

After bootstrap, update `backend.tf` with the actual storage account name and run `terraform init`.

## Usage

### Initialize

```bash
cd terraform
terraform init
```

### Plan

Preview changes before applying:

```bash
terraform plan -out=tfplan
```

### Apply

Provision or update infrastructure:

```bash
terraform apply tfplan
```

Or apply directly (will prompt for confirmation):

```bash
terraform apply
```

### Destroy

Remove all Terraform-managed resources:

```bash
terraform destroy
```

Or skip confirmation:

```bash
terraform destroy -auto-approve
```

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Single flat module (no nested modules) | Small project; one environment; avoids over-engineering |
| `kubenet` network plugin | Lower IP consumption than Azure CNI; sufficient for single-node Free Tier cluster |
| System-assigned managed identity | No service principal rotation; simplest auth model for AKS |
| State backend in separate storage account | Survives `terraform destroy`; ~$0.02/month on Free Tier |
| Standard SKU load balancer | Required for nginx ingress external IP allocation |
| Terraform stages before Build in pipeline | Infrastructure must exist before Docker push and K8s deploy |

## Teardown Procedure

Follow these steps in order to cleanly remove all infrastructure.

### 1. Drain Workloads

Scale deployments to zero to prevent pod disruption alerts:

```bash
kubectl -n portfolio scale deployment/portfolio --replicas=0
```

### 2. Delete Persistent Volume Claims

Release Azure Disks before resource group deletion:

```bash
kubectl -n portfolio delete pvc portfolio-db-pvc
```

### 3. Uninstall Helm Charts

Remove ingress controller and cert-manager to release the public IP:

```bash
helm uninstall ingress-nginx -n ingress-nginx
helm uninstall cert-manager -n cert-manager
```

### 4. Destroy Terraform Resources

```bash
cd terraform
terraform destroy -auto-approve
```

## What Persists After Teardown

- **State backend storage account** (`tfstate-rg` resource group) — ~$0.02/month
- **Azure DevOps pipeline configuration** — no cost
- **Docker Hub images** — no cost on free tier

## What Is Lost

- **SQLite database on PVC** — data is destroyed with the Azure Disk
- **Let's Encrypt certificates** — re-issued on next spin-up
- **AKS cluster and all workloads** — fully recreated by `terraform apply`
