# Implementation Plan: Multi-Cloud Deployment

## Overview

Restructure the portfolio project from a single-target Azure deployment into a configuration-driven multi-cloud architecture supporting Azure AKS and AWS EKS as equal deployment peers. Implementation proceeds incrementally: file reorganization and Terraform modules first, then Kustomize K8s layering, then pipeline configuration, then DNS/TLS, then teardown/rollback mechanisms.

## Tasks

- [x] 1. Restructure Terraform into modular multi-target layout
  - [x] 1.1 Create Azure provider module under `infra/modules/azure/`
    - Refactor existing `terraform/main.tf`, `variables.tf`, `backend.tf` into `infra/modules/azure/main.tf` (resource group, VNet, subnet, AKS cluster)
    - Create `infra/modules/azure/variables.tf` with all current variables (location, resource_group_name, aks_cluster_name, dns_prefix, node_vm_size, node_count, vnet_address_space, subnet_address_prefix, kubernetes_version, environment, project_name)
    - Create `infra/modules/azure/outputs.tf` with cluster_endpoint, cluster_ca_data, cluster_name, resource_group_name
    - Create `infra/modules/azure/versions.tf` with required providers (azurerm ~> 3.0, azuread ~> 2.0)
    - _Requirements: 8.1, 8.10_

  - [x] 1.2 Create Azure target instance under `infra/targets/prod-azure-australiaeast/`
    - Create `infra/targets/prod-azure-australiaeast/main.tf` — thin root module calling `../../modules/azure` with prod parameters
    - Create `infra/targets/prod-azure-australiaeast/backend.tf` — azurerm backend (existing state config)
    - Expose outputs: cluster_endpoint, cluster_ca_data, cluster_name
    - _Requirements: 8.2, 8.10, 8.11_

  - [x] 1.3 Create AWS provider module under `infra/modules/aws/`
    - Create `infra/modules/aws/main.tf` — VPC with configurable CIDR (default 10.1.0.0/16), 2 public + 2 private subnets across 2 AZs, Internet Gateway, NAT Gateway, route tables
    - Create `infra/modules/aws/eks.tf` — EKS cluster + managed node group (desired: 1, min: 1, max: 2, instance type: t3.small, configurable K8s version)
    - Create `infra/modules/aws/ecr.tf` — ECR repository with lifecycle policy (max 10 tagged, untagged expire after 1 day), image scanning, IAM pull policy for EKS nodes
    - Create `infra/modules/aws/variables.tf` — region, cluster_name, environment, project_name, vpc_cidr, instance_type, k8s_version, node_desired, node_min, node_max, ecr_repo_name
    - Create `infra/modules/aws/outputs.tf` — cluster_endpoint, cluster_ca_data, cluster_name, ecr_repository_url, node_role_arn
    - Create `infra/modules/aws/versions.tf` — required providers (aws ~> 5.0)
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 2.2, 2.3_

  - [x] 1.4 Create AWS target instances under `infra/targets/`
    - Create `infra/targets/prod-aws-us-east-1/main.tf` — thin root module calling `../../modules/aws` with prod parameters (region us-east-1, cluster portfolio-eks, t3.small, k8s 1.31)
    - Create `infra/targets/prod-aws-us-east-1/backend.tf` — S3 backend with DynamoDB locking (bucket: portfolio-tfstate, key: prod-aws-us-east-1/terraform.tfstate)
    - Create `infra/targets/dev-aws-us-east-1/main.tf` — thin root module calling `../../modules/aws` with dev parameters
    - Create `infra/targets/dev-aws-us-east-1/backend.tf` — S3 backend with distinct key path (dev-aws-us-east-1/terraform.tfstate)
    - Expose outputs for both targets: cluster_endpoint, cluster_ca_data, cluster_name, ecr_repo_url
    - _Requirements: 1.3, 8.2, 8.11_

  - [x] 1.5 Remove legacy `terraform/` directory
    - Delete `terraform/` directory (code has been refactored into `infra/modules/azure/` and `infra/targets/prod-azure-australiaeast/`)
    - _Requirements: 8.10_

- [x] 2. Checkpoint - Validate Terraform structure
  - Ensure `terraform validate` passes on all modules and targets, ask the user if questions arise.

- [x] 3. Create Kustomize-based Kubernetes manifest layering
  - [x] 3.1 Create K8s base layer under `k8s/base/`
    - Create `k8s/base/kustomization.yaml` listing all base resources
    - Create `k8s/base/namespace.yaml` (portfolio namespace)
    - Create `k8s/base/deployment.yaml` — cloud-agnostic deployment with rolling update strategy (maxUnavailable: 0, maxSurge: 1), revisionHistoryLimit: 5, terminationGracePeriodSeconds: 60, preStop sleep 5, liveness/readiness probes, resource requests/limits, placeholder image tag
    - Create `k8s/base/service.yaml` — ClusterIP service on port 5000
    - Create `k8s/base/pvc.yaml` — PVC template (ReadWriteOnce, 256Mi)
    - Create `k8s/base/cert-manager-issuer.yaml` — Let's Encrypt ClusterIssuer with HTTP-01 solver
    - _Requirements: 3.1, 3.2, 8.3, 10.1, 10.2, 10.3, 10.5, 9.1_

  - [x] 3.2 Create K8s AWS provider layer under `k8s/providers/aws/`
    - Create `k8s/providers/aws/kustomization.yaml` referencing `../../base` and listing patches
    - Create `k8s/providers/aws/storageclass.yaml` — EBS gp3 StorageClass
    - Create `k8s/providers/aws/pvc-patch.yaml` — sets storageClassName: ebs-gp3
    - Create `k8s/providers/aws/ingress-patch.yaml` — NLB annotations (aws-load-balancer-type: nlb, internet-facing scheme)
    - _Requirements: 3.4, 4.2, 8.4_

  - [x] 3.3 Create K8s Azure provider layer under `k8s/providers/azure/`
    - Create `k8s/providers/azure/kustomization.yaml` referencing `../../base` and listing patches
    - Create `k8s/providers/azure/storageclass.yaml` — Azure managed-premium StorageClass
    - Create `k8s/providers/azure/pvc-patch.yaml` — sets storageClassName: managed-premium
    - Create `k8s/providers/azure/ingress-patch.yaml` — Azure LB health probe annotation
    - _Requirements: 8.4_

  - [x] 3.4 Create K8s environment layers under `k8s/environments/`
    - Create `k8s/environments/prod/replica-patch.yaml` — replicas: 2
    - Create `k8s/environments/prod/resources-patch.yaml` — production resource limits
    - Create `k8s/environments/dev/replica-patch.yaml` — replicas: 1
    - Create `k8s/environments/dev/resources-patch.yaml` — relaxed resource limits, debug logging
    - Create `k8s/environments/qa/replica-patch.yaml` — replicas: 2
    - Create `k8s/environments/qa/resources-patch.yaml` — production-like config
    - _Requirements: 8.5, 8.7, 10.7, 10.8_

  - [x] 3.5 Create K8s target layers under `k8s/targets/`
    - Create `k8s/targets/prod-azure-australiaeast/kustomization.yaml` — references providers/azure, applies prod env patches, sets image to ltyang/portfolio
    - Create `k8s/targets/prod-azure-australiaeast/ingress-host-patch.yaml` — orchidflow.io + www.orchidflow.io hosts, TLS secret name
    - Create `k8s/targets/prod-aws-us-east-1/kustomization.yaml` — references providers/aws, applies prod env patches, sets image to ECR URL
    - Create `k8s/targets/prod-aws-us-east-1/ingress-host-patch.yaml` — aws.orchidflow.io host, TLS secret name
    - Create `k8s/targets/dev-aws-us-east-1/kustomization.yaml` — references providers/aws, applies dev env patches, sets image to ECR URL
    - Create `k8s/targets/dev-aws-us-east-1/ingress-host-patch.yaml` — dev-aws.orchidflow.io host, TLS secret name
    - _Requirements: 8.6, 8.12, 8.15_

  - [x] 3.6 Remove legacy flat K8s manifests
    - Remove old `k8s/deployment.yaml`, `k8s/service.yaml`, `k8s/pvc.yaml`, `k8s/namespace.yaml`, `k8s/secret.yaml`, `k8s/ingress/`, `k8s/deploy.sh` (replaced by Kustomize layers)
    - _Requirements: 8.10_

- [x] 4. Checkpoint - Validate Kustomize builds
  - Ensure `kustomize build k8s/targets/{name}/` produces valid YAML for each target, ask the user if questions arise.

- [x] 5. Create deploy-targets.yml configuration file
  - [x] 5.1 Create `deploy-targets.yml` at project root
    - Define prod-azure-australiaeast target (enabled, provider: azure, region: australiaeast, environment: prod, trigger: release/*/v*, dns: root domain, registry: dockerhub, cluster_name, resource_group)
    - Define prod-aws-us-east-1 target (enabled, provider: aws, region: us-east-1, environment: prod, trigger: release/*/v*, dns: subdomain aws, registry: ecr, cluster_name, ecr_repo)
    - Define dev-aws-us-east-1 target (disabled, provider: aws, region: us-east-1, environment: dev, trigger: main, dns: subdomain dev-aws, registry: ecr, cluster_name, ecr_repo)
    - _Requirements: 5.1, 5.9, 8.13_

- [x] 6. Create pipeline configuration
  - [x] 6.1 Create target parsing script `pipelines/scripts/parse-targets.py`
    - Read and parse `deploy-targets.yml`
    - Accept optional target_list parameter — validate all names exist in config, fail with error if unknown target found
    - Accept optional environment filter — select all enabled targets matching environment
    - Output target matrix as pipeline variable for fan-out
    - _Requirements: 5.1, 5.3, 5.8, 5.12_

  - [x] 6.2 Create per-target deployment template `pipelines/templates/deploy-target.yml`
    - Credential setup (provider-specific: ARM_* for Azure, AWS_* for AWS)
    - Pre-flight credential validation — fail before API calls if credentials missing
    - Terraform init + plan + apply in `infra/targets/{target-name}/`
    - Cluster access (aws eks update-kubeconfig for AWS, az aks get-credentials for Azure)
    - Helm upgrade --install ingress-nginx (idempotent)
    - Wait for external IP/hostname (300s timeout)
    - Helm upgrade --install cert-manager + wait for webhook (120s timeout)
    - Create/update image pull secret (dry-run + apply for idempotency)
    - Kustomize edit set image + kustomize build + kubectl apply
    - Rollout status verification (180s timeout)
    - DNS update (Cloudflare A/CNAME record for target subdomain)
    - Log deployed image tag
    - _Requirements: 3.3, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 9.7_

  - [x] 6.3 Create main deploy pipeline `pipelines/deploy.yml`
    - Trigger on main, release/*, v* tags
    - Parameters: target_list (optional), environment (optional), image_tag (optional), teardown (deploy/destroy), preserve_ecr (boolean)
    - Validate stage: run parse-targets.py, validate target_list, check image_tag exists in registry if provided
    - Test stage: run pytest (same as current)
    - Build stage: build Docker image, push to Docker Hub always, push to ECR if any AWS target selected
    - Fan-out: one stage per selected target using deploy-target.yml template (parallel, independent)
    - Skip build if image_tag parameter provided
    - Report per-target status, overall success only when all targets succeed
    - _Requirements: 2.1, 2.4, 2.5, 5.2, 5.4, 5.5, 5.6, 5.7, 5.10, 5.11, 8.14, 9.3, 9.4, 9.5_

  - [x] 6.4 Create per-target teardown template `pipelines/templates/teardown-target.yml`
    - Validate target exists in deploy-targets.yml
    - Remove Cloudflare DNS record for target
    - Run `terraform destroy -auto-approve` in `infra/targets/{target-name}/`
    - Preserve state backend resources (S3 bucket/DynamoDB for AWS, Azure storage for Azure)
    - Handle ECR preservation based on preserve_ecr parameter
    - Idempotent: succeed even if infrastructure doesn't exist
    - _Requirements: 7.2, 7.3, 7.4, 7.6, 7.7, 7.8_

  - [x] 6.5 Create teardown pipeline `pipelines/teardown.yml`
    - Parameters: target_list (required), preserve_ecr (default: true)
    - Validate targets exist in config
    - Fan-out: parallel teardown per target using teardown-target.yml template
    - Independent execution — one failure doesn't block others
    - Skip all deployment stages
    - _Requirements: 7.1, 7.2, 7.6, 7.9_

  - [x] 6.6 Remove legacy `azure-pipelines.yml`
    - Delete `azure-pipelines.yml` (replaced by `pipelines/deploy.yml`)
    - _Requirements: 8.10_

- [x] 7. Checkpoint - Validate pipeline configuration
  - Ensure pipeline YAML files are valid, parse-targets.py runs correctly against deploy-targets.yml, ask the user if questions arise.

- [x] 8. Configure DNS, TLS, and ingress per target
  - [x] 8.1 Add ingress resource to K8s base layer
    - Create `k8s/base/ingress.yaml` — base Ingress resource with cert-manager annotation, ssl-redirect, TLS configuration placeholder
    - Update `k8s/base/kustomization.yaml` to include ingress.yaml
    - _Requirements: 4.5, 4.7, 10.6_

  - [x] 8.2 Configure target-specific ingress hosts and TLS
    - Update `k8s/targets/prod-azure-australiaeast/ingress-host-patch.yaml` — hosts: orchidflow.io, www.orchidflow.io; TLS secret: portfolio-tls-azure
    - Update `k8s/targets/prod-aws-us-east-1/ingress-host-patch.yaml` — host: aws.orchidflow.io; TLS secret: portfolio-tls-aws
    - Update `k8s/targets/dev-aws-us-east-1/ingress-host-patch.yaml` — host: dev-aws.orchidflow.io; TLS secret: portfolio-tls-dev-aws
    - _Requirements: 4.4, 4.5_

- [x] 9. Implement rollback and re-provisioning support
  - [x] 9.1 Add image_tag parameter validation to deploy pipeline
    - In pipelines/deploy.yml Validate stage: if image_tag is provided, verify tag exists in target registries (Docker Hub and/or ECR) before deployment
    - Fail with descriptive error if tag not found
    - _Requirements: 9.3, 9.4_

  - [x] 9.2 Add re-provisioning flow documentation and verification
    - Ensure deploy pipeline handles previously torn-down targets: terraform apply re-creates infra, Helm installs fresh, manifests applied, DNS re-created
    - Add comments in deploy-target.yml template documenting re-provisioning flow
    - _Requirements: 7.5_

- [x] 10. Checkpoint - Final validation
  - Ensure all Terraform modules validate, all Kustomize targets build, pipeline YAML is well-formed, and deploy-targets.yml schema is correct. Ask the user if questions arise.

- [x] 11. Add validation tests
  - [x] 11.1 Write unit tests for `pipelines/scripts/parse-targets.py`
    - Test valid config parsing returns correct target list
    - Test unknown target in target_list raises error
    - Test environment filter selects correct targets
    - Test disabled targets excluded on automatic trigger
    - _Requirements: 5.1, 5.8, 5.12_

  - [x] 11.2 Write Kustomize build validation script
    - Script that runs `kustomize build` for each target in k8s/targets/
    - Validates output contains expected resource kinds (Namespace, Deployment, Service, PVC, Ingress)
    - Verifies prod targets have replicas: 2, dev targets have replicas: 1
    - Verifies AWS targets have EBS StorageClass, Azure targets have managed-premium
    - _Requirements: 3.1, 3.2, 8.12_

  - [x] 11.3 Write Terraform validation script
    - Script that runs `terraform validate` on each module and target directory
    - Verifies outputs are declared in each module
    - _Requirements: 1.7, 8.1_

- [x] 12. Final checkpoint - Ensure all validations pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major phase
- No property-based tests are included because this feature is entirely IaC, pipeline config, K8s manifests, and shell scripts — none of which have pure function behavior suitable for PBT
- The design uses HCL (Terraform), YAML (K8s/pipelines), Python (parse script), and Bash (pipeline steps) — language is determined by the component type
- Existing `terraform/` directory and `azure-pipelines.yml` are removed after their replacements are created
- The old flat `k8s/` manifests are removed after the Kustomize layering is in place

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3"] },
    { "id": 1, "tasks": ["1.2", "1.4"] },
    { "id": 2, "tasks": ["1.5", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4"] },
    { "id": 4, "tasks": ["3.5", "5.1"] },
    { "id": 5, "tasks": ["3.6", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.4"] },
    { "id": 7, "tasks": ["6.3", "6.5"] },
    { "id": 8, "tasks": ["6.6", "8.1"] },
    { "id": 9, "tasks": ["8.2", "9.1"] },
    { "id": 10, "tasks": ["9.2"] },
    { "id": 11, "tasks": ["11.1", "11.2", "11.3"] }
  ]
}
```
