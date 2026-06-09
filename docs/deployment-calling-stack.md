# Deployment Calling Stack

This document maps out which files are used at each stage of the deployment
and teardown pipelines for AWS targets via GitHub Actions.

## File Roles

| File | Role | Used at runtime? |
|------|------|-----------------|
| `deploy-targets.yml` | Documentation only — describes intended targets, triggers, and DNS config | **No** — not read by any pipeline |
| `.github/workflows/deploy-aws.yml` | GitHub Actions workflow — defines jobs, triggers, and all deploy logic | **Yes** |
| `.github/workflows/teardown-aws.yml` | GitHub Actions workflow — manual teardown | **Yes** |
| `infra/targets/prod-aws-us-east-1/` | Terraform root module for prod | **Yes** — during `terraform apply/destroy` |
| `infra/targets/dev-aws-us-east-1/` | Terraform root module for dev | **Yes** — during `terraform apply/destroy` |
| `infra/modules/aws/` | Shared Terraform module (VPC, EKS, ECR, EBS CSI) | **Yes** — referenced by target modules |
| `k8s/targets/prod-aws-us-east-1/` | Kustomize overlay for prod K8s manifests | **Yes** — during `kustomize build` |
| `k8s/targets/dev-aws-us-east-1/` | Kustomize overlay for dev K8s manifests | **Yes** — during `kustomize build` |
| `k8s/base/` | Base K8s manifests (Deployment, Service, PVC, Ingress) | **Yes** — composed by Kustomize |
| `k8s/providers/aws/` | AWS-specific patches (StorageClass, PVC) | **Yes** — composed by Kustomize |
| `k8s/environments/dev/` | Dev environment patches (replicas, resources) | **Yes** — composed by Kustomize |
| `k8s/environments/prod/` | Prod environment patches | **Yes** — composed by Kustomize |

## Deploy Pipeline Flow (`.github/workflows/deploy-aws.yml`)

```
Push to main ──────────────────────────► deploy-dev job
Push to release/* or v* tag ───────────► deploy-prod job
Manual dispatch (select target) ───────► deploy-dev OR deploy-prod job
```

### Job: deploy-dev

```
1. Checkout code
2. Determine image tag (git SHA)
3. Configure AWS credentials          ← GitHub Secrets
4. Setup Terraform
5. Terraform Apply                     ← infra/targets/dev-aws-us-east-1/
   └── module source                   ← infra/modules/aws/
       ├── main.tf (VPC, subnets, NAT, routes)
       ├── eks.tf (EKS cluster, node group, OIDC, EBS CSI)
       └── ecr.tf (data source only, create_ecr=false)
6. Configure kubectl                   ← portfolio-eks-dev cluster
7. Install ingress-nginx (Helm)        ← ingress-nginx chart
8. Wait for Load Balancer              ← AWS ELB provisioning
9. Install cert-manager (Helm)         ← jetstack/cert-manager chart
10. Create pull secrets                ← dockerhub-pull-secret, ecr-pull-secret, portfolio-secret
11. Deploy with Kustomize              ← k8s/targets/dev-aws-us-east-1/
    └── kustomization.yaml composes:
        ├── k8s/base/                  (deployment, service, pvc, ingress)
        ├── k8s/providers/aws/         (storageclass, pvc-patch)
        └── k8s/environments/dev/      (replica count, resource limits)
12. Verify rollout                     ← kubectl rollout status
13. Update Cloudflare DNS              ← dev-aws.orchidflow.io → ELB hostname
```

### Job: deploy-prod

Same flow as deploy-dev, but uses:
- `infra/targets/prod-aws-us-east-1/` (Terraform)
- `portfolio-eks` cluster
- `k8s/targets/prod-aws-us-east-1/` (Kustomize)
- DNS: `aws.orchidflow.io`

## Teardown Pipeline Flow (`.github/workflows/teardown-aws.yml`)

```
Manual dispatch only (must type "destroy" to confirm)
```

```
1. Validate confirmation
2. Configure AWS credentials
3. Remove Cloudflare DNS record        ← aws.orchidflow.io or dev-aws.orchidflow.io
4. Clean up K8s LoadBalancers          ← kubectl delete svc (releases AWS ELBs)
5. Setup Terraform
6. Clean up orphaned Load Balancers    ← AWS API (catches ELBs missed by kubectl)
7. Terraform Destroy                   ← infra/targets/{target}/
   └── Optionally preserves ECR repo (--target flag excludes ECR resources)
```

## What Controls Which Target Gets Deployed

| Decision | Controlled by |
|----------|---------------|
| Which job runs (dev vs prod) | `if:` conditions in workflow YAML (branch/tag matching) |
| Which infrastructure is created | `working-directory` in Terraform steps (points to target folder) |
| Which K8s manifests are applied | `cd k8s/targets/{target}` in Kustomize step |
| Which DNS record is updated | Hardcoded in the workflow job (`aws.orchidflow.io` vs `dev-aws.orchidflow.io`) |
| Which cluster to connect to | `CLUSTER_NAME_PROD` / `CLUSTER_NAME_DEV` env vars |

## GitHub Environments (prod-aws, dev-aws)

These are **labels** in GitHub, not infrastructure selectors. They provide:
- Deployment history view in the GitHub UI
- Optional protection rules (required reviewers for prod)
- Environment-scoped secrets (if needed)

They do NOT control what gets deployed — the workflow logic does that.

## deploy-targets.yml

Currently serves as **documentation only**. It describes the intended
multi-cloud architecture and target registry but is not parsed by any
automation. The original design envisioned a dynamic pipeline that reads
this file and fans out, but the current GitHub Actions implementation uses
hardcoded job definitions instead.
