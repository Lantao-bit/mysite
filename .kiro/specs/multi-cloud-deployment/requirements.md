# Requirements Document

## Introduction

This feature adds AWS as a deployment target for the portfolio Flask application and restructures the entire project for scalable multi-cloud deployment. The goal is to establish a configuration-driven, multi-target deployment architecture where all cloud targets are equal peers. The architecture supports the full environment × provider × region matrix (e.g., dev-aws-us-east-1, prod-aws-us-east-1, prod-azure-eastus) without artifact duplication — environments share provider modules and K8s provider overlays, while environment-specific K8s patches (replica count, resource limits, logging) are authored once per environment and applied across all targets of that environment regardless of cloud provider. Shared Terraform modules are authored once per provider, thin target instances supply region- and environment-specific parameters and maintain independent state. Existing Azure infrastructure code, Kubernetes manifests, and pipeline configurations will be reorganized into the new scalable structure (e.g., `terraform/` moves to `infra/modules/azure/` + `infra/targets/prod-azure-eastus/`, K8s manifests split into `k8s/base/`, `k8s/providers/`, `k8s/environments/`, and `k8s/targets/`). Creating and optimizing the multi-cloud deployment structure takes precedence over preserving the current deployment layout — existing files and directory structures may be moved, renamed, or refactored as needed to achieve the target architecture. This serves as a learning exercise for AWS and lays groundwork for future multi-cloud enterprise deployments.

## Glossary

- **Workflow**: A GitHub Actions workflow that builds, tests, and deploys the application
- **Deployment_Target**: A cloud environment (e.g., Azure or AWS) where the application is deployed
- **EKS_Cluster**: An Amazon Elastic Kubernetes Service cluster that runs the containerized application
- **AKS_Cluster**: The existing Azure Kubernetes Service cluster
- **Terraform_AWS_Module**: The Terraform configuration files that provision AWS infrastructure
- **ECR_Registry**: Amazon Elastic Container Registry used to store Docker images for AWS deployment
- **Ingress_Controller**: The NGINX ingress controller that routes external traffic to the application
- **Deploy_Targets_Config**: A configuration file (deploy-targets.yml) at the project root listing all deployment targets with their enabled status and cloud-specific parameters
- **Target_List**: An array of deployment target names provided to the Workflow for deployment or teardown
- **AWS_Infrastructure**: The set of AWS resources (VPC, subnets, EKS, ECR, OIDC, EBS CSI) provisioned by Terraform
- **Provider_Module**: A reusable Terraform module containing the infrastructure logic for a specific cloud provider (e.g., AWS VPC+EKS pattern, Azure VNet+AKS pattern), parameterized by region and target-specific variables
- **Target_Instance**: A specific deployment of a Provider_Module to a particular region and environment, represented by a thin Terraform root module that calls the Provider_Module with region- and environment-specific parameters and maintains its own independent state
- **GitHub_Environment**: A GitHub Actions environment that provides protection rules (e.g., manual approval for production) and scoped secrets

## Requirements

### Requirement 1: AWS Infrastructure Provisioning

**User Story:** As a developer, I want to provision AWS infrastructure using Terraform, so that I have an EKS cluster ready to host my portfolio application.

#### Acceptance Criteria

1. WHEN the developer runs Terraform apply for the AWS module, THE Terraform_AWS_Module SHALL provision a VPC with a configurable CIDR block (auto-assigned per target, e.g., 10.1.0.0/16, 10.2.0.0/16), containing one public subnet and one private subnet in each of two availability zones (four subnets total)
2. WHEN the developer runs Terraform apply for the AWS module, THE Terraform_AWS_Module SHALL provision an EKS_Cluster with a single managed node group configured with a desired count of 1, a minimum count of 1, and a maximum count of 2, and SHALL NOT create the node group if the EKS_Cluster provisioning fails
3. THE Terraform_AWS_Module SHALL store its state in an S3 backend with `use_lockfile = true` for state locking, using a distinct S3 key path per target so that all target state files are independently accessible
4. THE Terraform_AWS_Module SHALL tag all provisioned resources with a `Target` tag (target name), a `Project` tag, and a `ManagedBy: terraform` tag, where tag values are sourced from input variables
5. THE Terraform_AWS_Module SHALL configure the EKS_Cluster node group with a configurable instance type defaulting to t3.medium (required due to EKS pod limit constraints on smaller instances), and a configurable Kubernetes version defaulting to a documented EKS-supported minor version in the format "X.Y"
6. IF Terraform apply fails due to insufficient permissions, THEN THE Terraform_AWS_Module SHALL exit with a non-zero status and produce an error message indicating the missing IAM permission, and SHALL only produce permission-related error messages when permissions are actually insufficient
7. WHEN the EKS_Cluster is provisioned, THE Terraform_AWS_Module SHALL output the cluster endpoint URL and cluster name as named Terraform outputs sufficient to configure kubectl access
8. THE Terraform_AWS_Module SHALL provision an OIDC provider, an IAM role for the EBS CSI driver, and install the EBS CSI driver as an EKS add-on, so that EBS-backed PersistentVolumeClaims can be dynamically provisioned on the cluster

### Requirement 2: Container Image Management for AWS

**User Story:** As a developer, I want my Docker image pushed to an AWS-accessible registry, so that EKS can pull the application image during deployment.

#### Acceptance Criteria

1. WHEN the Workflow builds a new image and the Target_List includes an AWS target, THE Workflow SHALL authenticate with the ECR_Registry using AWS credentials and push the image to the ECR_Registry in addition to Docker Hub, and SHALL skip the ECR push entirely when no AWS targets are selected
2. THE Terraform_AWS_Module SHALL provision the ECR_Registry with an image scanning configuration and an IAM policy that grants pull access to the EKS cluster nodes
3. THE ECR_Registry SHALL retain a maximum of 10 tagged image versions using a lifecycle policy, and SHALL expire any untagged images after 1 day
4. WHEN the Workflow builds a new image, THE Workflow SHALL tag the image with the first 8 characters of the git SHA and a "latest" tag independently of whether the image is successfully pushed to the ECR_Registry
5. IF the Workflow fails to authenticate with or push to the ECR_Registry when AWS targets are selected, THEN THE Workflow SHALL fail the build job and report an error message indicating the ECR push failure, while other non-dependent jobs continue independently

### Requirement 3: Kubernetes Deployment to EKS

**User Story:** As a developer, I want my application deployed to EKS with the same configuration as AKS, so that the application runs consistently across both clouds.

#### Acceptance Criteria

1. WHEN the Workflow deploys to AWS, THE Workflow SHALL apply Kubernetes manifests to the EKS_Cluster that include the same resource kinds as AKS: Namespace, Secret, PersistentVolumeClaim, Deployment, and Service
2. THE EKS_Cluster SHALL run the portfolio application with the same environment variables (SECRET_KEY from secret, DATABASE_PATH set to /app/data/portfolio.db), resource limits (configurable per target via deploy-targets.yml `resources` field), liveness probe (HTTP GET / on port 5000, initialDelaySeconds 10, periodSeconds 30), and readiness probe (HTTP GET / on port 5000, initialDelaySeconds 5, periodSeconds 10) as the AKS_Cluster
3. WHEN the deployment completes on the EKS_Cluster, THE Workflow SHALL verify the rollout status of the portfolio deployment within a timeout of 180 seconds
4. THE EKS_Cluster SHALL use a PersistentVolumeClaim with ReadWriteOnce access mode and 256Mi storage capacity backed by Amazon EBS (via EBS CSI driver) for the SQLite database file
5. IF the rollout fails on the EKS_Cluster, THEN THE Workflow SHALL exit the EKS deployment job with a non-zero status and log the failure reason, while all other targeted Deployment_Target jobs continue executing independently without being blocked or failed
6. WHEN the Workflow deploys to the EKS_Cluster, THE Workflow SHALL first obtain cluster credentials by running `aws eks update-kubeconfig` using the cluster name and region derived from the target configuration

### Requirement 4: Ingress and TLS on AWS

**User Story:** As a developer, I want HTTPS traffic routed to my application on EKS, so that the AWS deployment is accessible securely via a domain name.

#### Acceptance Criteria

1. WHEN the Workflow completes AWS infrastructure provisioning, THE Workflow SHALL install the Ingress_Controller on the EKS_Cluster using Helm into a dedicated namespace with `controller.admissionWebhooks.enabled=false` to avoid pre-upgrade hook timeouts on small clusters
2. THE Ingress_Controller SHALL provision an AWS Network Load Balancer and obtain an external IP or hostname within 300 seconds of installation, and SHALL be considered failed if the load balancer provisions but no external IP or hostname is obtained
3. WHEN the Ingress_Controller is running, THE Workflow SHALL install cert-manager on the EKS_Cluster via Helm, wait for the cert-manager webhook deployment to become available within 180 seconds, and apply a Let's Encrypt ClusterIssuer configured with an HTTP-01 solver
4. WHEN the Ingress_Controller receives an external IP or hostname, THE Workflow SHALL create or update a Cloudflare DNS A record (or CNAME record for hostnames) for the target's `dns_subdomain` (e.g., aws.orchidflow.io) to point to the AWS deployment, leaving the root domain and www subdomain pointing to the Azure deployment
5. THE EKS_Cluster SHALL serve the application over HTTPS with a TLS certificate issued by Let's Encrypt that matches the target's domain and is trusted by standard browsers
6. IF the Ingress_Controller does not receive an external IP or hostname within 300 seconds, THEN THE Workflow SHALL terminate the deployment job with a failure status
7. THE Ingress_Controller SHALL redirect all HTTP requests on port 80 to HTTPS on port 443

### Requirement 5: Scalable Multi-Target Deployment Selection (GitHub Actions)

**User Story:** As a developer, I want to control which cloud target(s) receive a deployment using a configuration-driven GitHub Actions workflow with dynamic matrix strategy, so that adding new targets requires only a config change and deployments run in parallel independently.

#### Acceptance Criteria

1. THE Workflow SHALL read the Deploy_Targets_Config file (deploy-targets.yml at the project root) in a `setup` job that parses the YAML using Python + yq and outputs a JSON matrix for the deploy job's `strategy.matrix`
2. WHEN the Workflow is triggered automatically from a push event, THE Workflow SHALL deploy to all Deployment_Targets that are marked as enabled and whose `trigger` rules match the current git ref (branch or tag)
3. THE Workflow SHALL accept an optional `target` input (via `workflow_dispatch`) containing a single Deployment_Target name that overrides the trigger-based filtering for that run
4. WHEN a `target` input is provided via manual dispatch, THE Workflow SHALL deploy only to the specified Deployment_Target, regardless of trigger rules (but still requires `enabled: true`)
5. THE Workflow SHALL execute deployments to all selected Deployment_Targets in parallel using `strategy.matrix` with `fail-fast: false`, treating each target as an independent matrix job with no ordering between targets
6. WHEN one Deployment_Target's matrix job fails, THE Workflow SHALL continue deploying to all other selected Deployment_Targets independently without blocking or failing them (enforced by `fail-fast: false`)
7. THE Workflow SHALL report overall success only when all selected Deployment_Target matrix jobs succeed, and SHALL report per-job status in the workflow summary
8. THE Deploy_Targets_Config SHALL define each target with name, enabled, provider, region, github_environment, dns_subdomain, replicas, resources, and trigger fields — where the provider field identifies which Provider_Module and K8s provider overlay to use, and the trigger field specifies the source control events that initiate deployment for that target — so that adding a new cloud target requires only adding a new entry to this file and running `scripts/generate-targets.py` without modifying workflow logic
9. THE Workflow SHALL use the `provider` field from the Deploy_Targets_Config to determine which Kubernetes provider overlay and Terraform Provider_Module to apply for each target, so that multiple targets sharing the same provider reuse the same overlay and module logic without duplication
10. THE Workflow SHALL map each target's `github_environment` field to the GitHub Actions `environment` property on the deploy job, enabling environment-specific protection rules (e.g., manual approval for production)
11. THE Workflow SHALL derive `cluster_name` as `portfolio-{target-name}`, `resource_group` as `portfolio-rg-{target-name}` (Azure only), and `registry` from provider (aws=ecr, azure=dockerhub) — these values are NOT stored in the config file

### Requirement 6: AWS Credentials and Secrets Management

**User Story:** As a developer, I want AWS credentials managed securely in the workflow, so that deployments authenticate to AWS without exposing secrets.

#### Acceptance Criteria

1. THE Workflow SHALL authenticate to AWS using GitHub Actions secrets (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) via the `aws-actions/configure-aws-credentials@v4` action, with the region determined from the target configuration
2. THE Workflow SHALL authenticate to Azure using GitHub Actions secrets (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID) via the `azure/login@v2` action, and map these to ARM_* environment variables for the Terraform provider
3. WHEN the Workflow deploys to EKS, THE Workflow SHALL create or update a Kubernetes image pull secret for the ECR registry in the target deployment namespace using a dry-run and apply strategy to ensure idempotency, and IF the image pull secret creation fails, THEN THE Workflow SHALL fail the entire EKS deployment job
4. IF any of the required AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) are unset or empty, THEN THE Workflow SHALL fail the credential configuration step before executing any AWS API calls
5. WHEN AWS credentials are available, THE Workflow SHALL treat each deployment job failure as isolated, allowing other matrix jobs with valid credentials to proceed or fail independently
6. IF AWS credentials are set but authentication to AWS fails, THEN THE Workflow SHALL fail the current deployment job with an error message indicating the authentication failure reason returned by AWS

### Requirement 7: Multi-Target Infrastructure Teardown and Re-Provisioning

**User Story:** As a developer, I want to tear down infrastructure for a target independently when not in use and re-provision on demand, so that I avoid ongoing costs for learning environments that do not need to be online continuously.

#### Acceptance Criteria

1. THE project SHALL provide a separate teardown workflow (`.github/workflows/teardown.yml`) triggered by `workflow_dispatch` with inputs: `target` (required), `preserve_registry` (boolean, default true), and `confirm` (must equal "destroy")
2. WHEN the teardown workflow is triggered, THE Workflow SHALL derive cluster_name and resource_group from the target name, configure provider credentials, and run `terraform destroy` in the target's directory under `infra/targets/{target-name}/`
3. WHEN the teardown workflow is triggered for a target, THE Workflow SHALL remove the corresponding Cloudflare DNS record for that target before destroying infrastructure, and clean up Kubernetes LoadBalancer services to release cloud load balancers
4. THE Workflow SHALL preserve the Terraform state storage resources (S3 bucket for AWS, Azure storage account for Azure) during teardown, so that subsequent `terraform apply` can re-provision the infrastructure cleanly
5. WHEN the developer re-provisions a Deployment_Target after a teardown, THE deploy Workflow SHALL execute the full deployment flow (Terraform apply, Helm installs, manifest application) and restore the DNS record for that target
6. WHEN the teardown workflow is triggered, THE Workflow SHALL skip all deployment-related steps and SHALL only execute destruction operations
7. IF the teardown workflow is triggered and the target infrastructure does not exist, THEN THE Workflow SHALL complete successfully without error (idempotent destroy)
8. THE ECR_Registry SHALL optionally be preserved or destroyed during AWS teardown based on the `preserve_registry` input defaulting to "preserve"
9. THE teardown workflow SHALL require the `confirm` input to equal "destroy" as a safety gate before executing any destructive operations

### Requirement 8: Scalable Multi-Target File Organization

**User Story:** As a developer, I want infrastructure code and Kubernetes manifests organized in a four-level hierarchy (provider modules → environment overlays → target instances → K8s layering), so that adding a new region or environment for an existing provider requires only a thin target directory and a config entry without duplicating provider logic or environment configuration.

#### Acceptance Criteria

1. THE project SHALL organize reusable Terraform modules under `infra/modules/{provider}/` (e.g., `infra/modules/aws/` for VPC+EKS+ECR+EBS CSI logic, `infra/modules/azure/` for VNet+AKS logic), where each Provider_Module is parameterized by region and target-specific variables
2. THE project SHALL organize target-specific Terraform configurations under `infra/targets/{target-name}/` using the naming convention `{environment}-{provider}-{region}` (e.g., `infra/targets/dev-aws-us-east-1/`, `infra/targets/prod-aws-us-east-1/`, `infra/targets/prod-azure-eastus/`), where each Target_Instance is a thin root module that calls its Provider_Module with target-specific variables (region, cluster name, environment) and maintains its own independent state backend
3. THE project SHALL organize cloud-agnostic shared Kubernetes manifests under `k8s/base/` containing Deployment, Service, and PVC template resources
4. THE project SHALL organize provider-specific Kubernetes patches under `k8s/providers/{provider}/` (e.g., `k8s/providers/aws/` for EBS StorageClass and NLB annotations, `k8s/providers/azure/` for managed disk StorageClass and Azure LB annotations), shared across all targets of that provider
5. THE project SHALL organize environment-specific Kubernetes patches under `k8s/environments/{environment}/` (e.g., `k8s/environments/dev/` for single-replica and debug logging, `k8s/environments/prod/` for multi-replica and production resource limits), shared across all targets of that environment regardless of provider
6. THE project SHALL organize optional target-specific Kubernetes overrides under `k8s/targets/{target-name}/` that inherit from the provider overlay and include inline replicas/resources patches (generated by `scripts/generate-targets.py`)
7. WHEN multiple targets share the same provider, THE provider-specific K8s patches (StorageClass, LB annotations) SHALL be authored once in `k8s/providers/{provider}/` and applied to all targets of that provider without duplication
8. WHEN a new region is added for an existing provider, THE developer SHALL only need to add an entry to the Deploy_Targets_Config file and run `scripts/generate-targets.py` to generate the thin `infra/targets/{target-name}/` directory and `k8s/targets/{target-name}/` directory — without duplicating any provider logic or modifying existing target configurations
9. WHEN a new cloud provider is added, THE developer SHALL create an `infra/modules/{provider}/` directory, a `k8s/providers/{provider}/` directory, and at least one Target_Instance entry under `infra/targets/`
10. THE existing Azure Terraform configuration (currently in `terraform/`) SHALL be refactored into `infra/modules/azure/` (shared Provider_Module) and `infra/targets/prod-azure-eastus/` (thin root module). THE existing `terraform/` directory, `k8s/` flat structure, and `azure-pipelines.yml` SHALL be restructured or replaced to conform to the new multi-target layout.
11. EACH Target_Instance's Terraform root module under `infra/targets/{target-name}/` SHALL declare its own backend configuration and call the Provider_Module, with no cross-references between target directories
12. THE Workflow SHALL compose Kubernetes manifests by layering: `k8s/base/` → `k8s/providers/{provider}/` → target-specific patches (using Kustomize), where provider patches handle cloud-specific resources (StorageClass, LB annotations) and target patches handle replicas, resources, and ingress host
13. THE project SHALL maintain a Deploy_Targets_Config file (deploy-targets.yml) at the project root that lists all Deployment_Targets with their name, enabled status, provider, region, github_environment, dns_subdomain, replicas, resources, and trigger fields
14. THE project SHALL use GitHub Actions workflow files (`.github/workflows/deploy.yml` for deployment, `.github/workflows/teardown.yml` for teardown) that read the Deploy_Targets_Config and fan out via dynamic matrix strategy, and a developer script (`scripts/generate-targets.py`) that generates Terraform and K8s target files from the config
15. THE project SHALL separate concerns across the target matrix as follows: Terraform module logic and K8s provider patches (StorageClass, LB annotations) are shared across all targets of the same provider; replicas and resource limits are specified per-target in deploy-targets.yml; cluster name, Terraform state, DNS subdomain, and specific variable values are unique per target (derived from target name)

### Requirement 9: Deployment Rollback and Recovery

**User Story:** As a developer, I want to quickly roll back a deployment to a known-good version when a major issue is discovered in production, so that application users are not affected by broken releases.

#### Acceptance Criteria

1. THE Kubernetes Deployment manifest SHALL configure a `revisionHistoryLimit` of at least 5, so that Kubernetes retains previous ReplicaSets sufficient for rollback
2. WHEN a major issue is discovered post-deployment, THE developer SHALL be able to execute `kubectl rollout undo deployment/portfolio -n {namespace}` on any target cluster to immediately revert to the previous working version without running the full workflow
3. THE Workflow SHALL accept an optional `image_tag` input (via `workflow_dispatch`) that, when provided, skips the image build job and deploys the specified pre-built image tag to the selected targets
4. WHEN the `image_tag` input is provided, THE Workflow SHALL verify that the specified tag exists in the target registry (Docker Hub or ECR) before attempting deployment, and SHALL fail with a descriptive error if the tag is not found
5. THE Workflow SHALL retain at least 10 tagged image versions in each container registry (Docker Hub and ECR) so that rollback to any of the last 10 builds is possible via the `image_tag` input
6. WHEN a rollout is in progress and the new pods fail health checks within the rollout timeout (180 seconds), THE Workflow SHALL report the rollout as failed and the previous ReplicaSet SHALL be available for manual `kubectl rollout undo`
7. THE Workflow SHALL log the deployed image tag for each target at the end of a successful deployment job, so that the last known-good tag is easily identifiable in workflow history

### Requirement 10: Deployment Strategy (Recreate due to RWO PVC)

**User Story:** As a developer, I want deployments to handle the ReadWriteOnce PVC constraint correctly, so that volume mount conflicts do not cause pods to hang indefinitely during updates.

#### Acceptance Criteria

1. THE Kubernetes Deployment manifest in `k8s/base/` SHALL configure a `Recreate` deployment strategy (not RollingUpdate), because the application uses a ReadWriteOnce PVC (EBS on AWS, Azure Disk on Azure) that can only be mounted by one pod at a time
2. THE Kubernetes Deployment manifest SHALL configure `terminationGracePeriodSeconds` of at least 60 seconds, giving in-flight requests sufficient time to complete before the pod is forcefully terminated
3. THE Kubernetes container spec SHALL include a `preStop` lifecycle hook that executes `sleep 5` before the application receives SIGTERM, allowing the ingress controller time to remove the pod from its routing table before shutdown begins
4. WHEN the application container receives SIGTERM, THE application (Gunicorn) SHALL stop accepting new connections and finish processing all in-flight requests before exiting, within the termination grace period
5. THE Kubernetes Deployment manifest SHALL configure a readiness probe so that new pods only receive traffic after the application is fully initialized and responding to health checks
6. WHEN a Recreate update is in progress, THE Kubernetes cluster SHALL terminate the existing pod(s), release the PVC, then start the new pod(s) which can mount the now-available volume — avoiding the deadlock where a new pod cannot start because the old pod still holds the RWO volume
7. THE brief downtime window during Recreate deployments (old pod terminates → new pod starts → passes readiness) SHALL be acceptable for this portfolio application, documented as a known trade-off of the RWO PVC + single-node architecture
8. THE `k8s/environments/dev/` overlay MAY configure `replicas: 1` for cost savings, and production targets MAY configure `replicas: 2` for availability outside of deployment windows (noting that during deployment, the Recreate strategy still causes brief downtime regardless of replica count due to the RWO constraint)
