# Adding a New Deployment Target

This guide walks through adding a new deployment target to the multi-cloud architecture. A target represents a specific combination of environment + provider + region (e.g., `prod-aws-eu-west-1`, `dev-azure-westus2`).

## Overview

Adding a new target for an **existing provider** requires:
1. A thin Terraform target directory (`infra/targets/{name}/`)
2. A Kustomize target directory (`k8s/targets/{name}/`)
3. An entry in `deploy-targets.yml`

Adding a target for a **new provider** additionally requires:
- A Terraform module (`infra/modules/{provider}/`)
- A Kustomize provider layer (`k8s/providers/{provider}/`)

---

## Step-by-Step: New Target for an Existing Provider (AWS Example)

### Naming Convention

Target names follow the format: `{environment}-{provider}-{region}`

Examples: `prod-aws-eu-west-1`, `dev-aws-us-west-2`, `qa-azure-westeurope`

### Step 1: Create the Terraform State Backend

For AWS targets, create an S3 bucket and DynamoDB table (if not already shared):

```bash
# Skip if reusing the existing portfolio-tfstate bucket
aws s3api create-bucket \
  --bucket portfolio-tfstate \
  --region us-east-1

aws dynamodb create-table \
  --table-name portfolio-tfstate-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

For Azure targets, the existing storage account (`ylt202605201452`) can be reused with a new state key.

### Step 2: Create the Terraform Target Directory

Create `infra/targets/{target-name}/` with three files:

**`main.tf`** — Thin root module calling the provider module:
```hcl
# infra/targets/prod-aws-eu-west-1/main.tf
module "aws" {
  source = "../../modules/aws"

  region       = "eu-west-1"
  cluster_name = "portfolio-eks-eu"
  environment  = "prod"
  project_name = "portfolio"
  vpc_cidr     = "10.3.0.0/16"  # Must not overlap with other targets
  instance_type = "t3.small"
  k8s_version  = "1.31"
}

output "cluster_endpoint" {
  description = "EKS cluster API server endpoint URL"
  value       = module.aws.cluster_endpoint
}

output "cluster_ca_data" {
  description = "Base64-encoded cluster CA certificate"
  value       = module.aws.cluster_ca_data
  sensitive   = true
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.aws.cluster_name
}

output "ecr_repo_url" {
  description = "Full ECR repository URL"
  value       = module.aws.ecr_repository_url
}
```

**`backend.tf`** — State backend with a unique key path:
```hcl
# infra/targets/prod-aws-eu-west-1/backend.tf
terraform {
  backend "s3" {
    bucket         = "portfolio-tfstate"
    key            = "prod-aws-eu-west-1/terraform.tfstate"  # Unique per target
    region         = "us-east-1"
    dynamodb_table = "portfolio-tfstate-lock"
    encrypt        = true
  }
}
```

**`versions.tf`** — Provider requirements:
```hcl
# infra/targets/prod-aws-eu-west-1/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

### Step 3: Create the Kustomize Target Directory

Create `k8s/targets/{target-name}/` with two files:

**`kustomization.yaml`** — Composes provider + environment + target-specific patches:
```yaml
# k8s/targets/prod-aws-eu-west-1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../providers/aws
patches:
  - path: ingress-host-patch.yaml
  # Inline environment patches (prod = 2 replicas, production resources)
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: portfolio
        namespace: portfolio
      spec:
        replicas: 2
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: portfolio
        namespace: portfolio
      spec:
        template:
          spec:
            containers:
              - name: portfolio
                resources:
                  requests:
                    memory: "64Mi"
                    cpu: "100m"
                  limits:
                    memory: "256Mi"
                    cpu: "500m"
images:
  - name: ltyang/portfolio
    newName: <AWS_ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/portfolio
    newTag: BUILD_ID
```

**`ingress-host-patch.yaml`** — Target-specific domain and TLS:
```yaml
# k8s/targets/prod-aws-eu-west-1/ingress-host-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: portfolio-ingress
  namespace: portfolio
spec:
  tls:
    - hosts:
        - eu.orchidflow.io
      secretName: portfolio-tls-eu
  rules:
    - host: eu.orchidflow.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: portfolio-service
                port:
                  number: 5000
```

### Step 4: Add Entry to `deploy-targets.yml`

Add the new target to the `targets` array:

```yaml
  - name: prod-aws-eu-west-1
    enabled: true                    # Set to false to skip on auto-triggers
    provider: aws
    region: eu-west-1
    environment: prod
    trigger:
      branches: [release/*]
      tags: [v*]
    dns:
      subdomain: eu                  # Creates eu.orchidflow.io
      record_type: A
    registry: ecr
    cluster_name: portfolio-eks-eu
    ecr_repo: portfolio
```

### Step 5: Add to the Appropriate CI/CD Pipeline

**For AWS targets** — add a deploy job in `.github/workflows/deploy-aws.yml` (copy an existing job and modify the target name, cluster name, and DNS subdomain).

**For Azure targets** — add a deploy stage in `pipelines/deploy.yml` using the `templates/deploy-target.yml` template.

Also add a corresponding teardown entry:
- AWS: `.github/workflows/teardown-aws.yml` (add to the `target` choice options)
- Azure: `pipelines/teardown.yml`

### Step 6: Add Secrets to the CI/CD Platform

**For GitHub Actions (AWS targets):**
Go to GitHub → Settings → Secrets and variables → Actions, and add:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID` (12-digit account ID for ECR URLs)
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID`

**For Azure DevOps (Azure targets):**
Go to Azure DevOps → Pipelines → Library → Variable groups, and ensure:
- `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID`

### Step 7: Validate Locally

```bash
# Terraform
cd infra/targets/prod-aws-eu-west-1
terraform init -backend=false
terraform validate

# Kustomize
kubectl kustomize k8s/targets/prod-aws-eu-west-1/

# Parse targets
python pipelines/scripts/parse-targets.py --target-list "prod-aws-eu-west-1"
```

### Step 8: Deploy

Push to trigger automatically, or run manually with:
- `target_list = "prod-aws-eu-west-1"`

---

## Important Notes

### VPC CIDR Allocation

Each AWS target needs a unique VPC CIDR to avoid conflicts if you ever peer VPCs:
| Target | VPC CIDR |
|--------|----------|
| prod-aws-us-east-1 | 10.1.0.0/16 |
| dev-aws-us-east-1 | 10.2.0.0/16 |
| prod-aws-eu-west-1 | 10.3.0.0/16 |

### Environment Patches

Use the appropriate environment for your target:
- **prod**: 2 replicas, production resource limits
- **dev**: 1 replica, relaxed limits, FLASK_DEBUG=1
- **qa**: 2 replicas, production-like config

### DNS Subdomains

Each target gets a unique subdomain under orchidflow.io:
| Target | Domain |
|--------|--------|
| prod-azure-australiaeast | orchidflow.io (root) |
| prod-aws-us-east-1 | aws.orchidflow.io |
| dev-aws-us-east-1 | dev-aws.orchidflow.io |
| prod-aws-eu-west-1 | eu.orchidflow.io |

### Teardown

To destroy a target's infrastructure (saves costs when not needed):
1. Go to Azure DevOps → Pipelines → Teardown pipeline
2. Run manually with `target_list = "prod-aws-eu-west-1"`
3. The cluster and all resources are destroyed, but state backend and ECR images are preserved
4. Re-deploy anytime by running the deploy pipeline — it re-creates everything from scratch

### Cost Awareness

Each AWS target costs approximately:
- EKS cluster: ~$73/month (control plane)
- t3.small node: ~$15/month
- NAT Gateway: ~$32/month
- Load Balancer: ~$16/month
- **Total: ~$136/month per target**

Use the teardown pipeline to destroy targets when not actively needed.
