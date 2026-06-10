# Deployment Calling Stack

This document maps out which files are used at each stage of the unified
GitHub Actions deployment and teardown pipelines.

## File Roles

| File | Role | Used at runtime? |
|------|------|-----------------|
| `deploy-targets.yml` | **Single source of truth** — defines all targets, read by pipeline at runtime | **Yes** |
| `.github/workflows/deploy.yml` | Unified deploy workflow (test → build → fan-out) | **Yes** |
| `.github/workflows/teardown.yml` | Unified teardown workflow (manual dispatch) | **Yes** |
| `infra/targets/{name}/` | Terraform root module per target | **Yes** — during `terraform apply/destroy` |
| `infra/modules/aws/` | Shared AWS Terraform module (VPC, EKS, ECR, EBS CSI) | **Yes** |
| `infra/modules/azure/` | Shared Azure Terraform module (RG, AKS) | **Yes** |
| `k8s/targets/{name}/` | Kustomize overlay per target | **Yes** — during `kustomize build` |
| `k8s/base/` | Base K8s manifests (Deployment, Service, PVC, Ingress, ClusterIssuer) | **Yes** |
| `k8s/providers/aws/` | AWS-specific patches (StorageClass, PVC) | **Yes** |
| `k8s/providers/azure/` | Azure-specific patches (StorageClass, PVC, Ingress annotations) | **Yes** |

## Deploy Pipeline Flow (`.github/workflows/deploy.yml`)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Trigger: push to main/release/*/v* tag, or manual dispatch          │
└─────────────────────┬───────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ setup: Parse deploy-targets.yml → build matrix of enabled targets   │
└─────────────────────┬───────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ test: Run pytest (once)                                             │
└─────────────────────┬───────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ build: Docker build → push to Docker Hub + ECR (once)               │
└─────────────────────┬───────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ deploy (fan-out, parallel per target):                              │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │ prod-azure-eastus   │  │ prod-aws-us-east-1  │  ...             │
│  │  1. Credentials     │  │  1. Credentials     │                  │
│  │  2. Terraform Apply │  │  2. Terraform Apply │                  │
│  │  3. kubectl config  │  │  3. kubectl config  │                  │
│  │  4. ingress-nginx   │  │  4. ingress-nginx   │                  │
│  │  5. cert-manager    │  │  5. cert-manager    │                  │
│  │  6. Pull secrets    │  │  6. Pull secrets    │                  │
│  │  7. Kustomize deploy│  │  7. Kustomize deploy│                  │
│  │  8. Verify rollout  │  │  8. Verify rollout  │                  │
│  │  9. Cloudflare DNS  │  │  9. Cloudflare DNS  │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Target Selection Logic

The `setup` job reads `deploy-targets.yml` and matches targets based on:

| Trigger | Which targets run |
|---------|-------------------|
| Push to `main` | Targets with `branches: [main]` in trigger |
| Push to `release/*` | Targets with `branches: [release/*]` |
| Push tag `v*` | Targets with `tags: [v*]` |
| Manual dispatch (specific target) | Only the named target |
| Manual dispatch (empty target) | All enabled targets |

Only targets with `enabled: true` are included.

## Teardown Pipeline Flow (`.github/workflows/teardown.yml`)

```
Manual dispatch → select target name + type "destroy"
  1. Resolve target metadata from deploy-targets.yml
  2. Configure provider credentials
  3. Remove Cloudflare DNS records
  4. Connect to cluster → delete LB services → wait for ENI release
  5. Clean up orphaned AWS Load Balancers (AWS only)
  6. Terraform destroy (optionally preserving ECR)
```

## GitHub Secrets Required

| Secret | Used for |
|--------|----------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM access |
| `AWS_ACCOUNT_ID` | ECR registry URL |
| `AZURE_CLIENT_ID` | Azure Service Principal |
| `AZURE_CLIENT_SECRET` | Azure Service Principal |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `DOCKERHUB_USERNAME` | Docker Hub push/pull |
| `DOCKERHUB_TOKEN` | Docker Hub auth |
| `CLOUDFLARE_API_TOKEN` | DNS management |
| `CLOUDFLARE_ZONE_ID` | DNS zone for orchidflow.io |

## Adding a New Target

1. Add entry to `deploy-targets.yml`
2. Run `python scripts/generate-targets.py`
3. Review generated files in `infra/targets/{name}/` and `k8s/targets/{name}/`
4. Commit and push — the pipeline picks it up automatically

The generator derives: cluster_name, resource_group, registry, VPC CIDR,
Terraform files, K8s Kustomize overlays — all from the target name and provider.
