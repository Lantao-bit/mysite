# Requirements Document

## Introduction

This feature adds AWS as a deployment target for the portfolio Flask application and restructures the entire project for scalable multi-cloud deployment. The goal is to establish a configuration-driven, multi-target deployment architecture where all cloud targets are equal peers. The architecture supports the full environment × provider × region matrix (e.g., dev-aws-us-east-1, qa-aws-us-east-1, prod-aws-us-east-1) without artifact duplication — environments share provider modules and K8s provider overlays, while environment-specific K8s patches (replica count, resource limits, logging) are authored once per environment and applied across all targets of that environment regardless of cloud provider. Shared Terraform modules are authored once per provider, thin target instances supply region- and environment-specific parameters and maintain independent state. Existing Azure infrastructure code, Kubernetes manifests, and pipeline configurations will be reorganized into the new scalable structure (e.g., `terraform/` moves to `infra/modules/azure/` + `infra/targets/prod-azure-australiaeast/`, K8s manifests split into `k8s/base/`, `k8s/providers/`, `k8s/environments/`, and `k8s/targets/`). Creating and optimizing the multi-cloud deployment structure takes precedence over preserving the current deployment layout — existing files and directory structures may be moved, renamed, or refactored as needed to achieve the target architecture. This serves as a learning exercise for AWS and lays groundwork for future multi-cloud enterprise deployments.

## Glossary

- **Pipeline**: The CI/CD automation that builds, tests, and deploys the application
- **Deployment_Target**: A cloud environment (e.g., Azure or AWS) where the application is deployed
- **EKS_Cluster**: An Amazon Elastic Kubernetes Service cluster that runs the containerized application
- **AKS_Cluster**: The existing Azure Kubernetes Service cluster
- **Terraform_AWS_Module**: The Terraform configuration files that provision AWS infrastructure
- **ECR_Registry**: Amazon Elastic Container Registry used to store Docker images for AWS deployment
- **Ingress_Controller**: The NGINX ingress controller that routes external traffic to the application
- **Deploy_Targets_Config**: A configuration file (deploy-targets.yml) at the project root listing all deployment targets with their enabled status and cloud-specific parameters
- **Target_List**: An array of deployment target names provided to the Pipeline for deployment or teardown
- **AWS_Infrastructure**: The set of AWS resources (VPC, subnets, EKS, ECR) provisioned by Terraform
- **Provider_Module**: A reusable Terraform module containing the infrastructure logic for a specific cloud provider (e.g., AWS VPC+EKS pattern, Azure VNet+AKS pattern), parameterized by region and target-specific variables
- **Target_Instance**: A specific deployment of a Provider_Module to a particular region and environment, represented by a thin Terraform root module that calls the Provider_Module with region- and environment-specific parameters and maintains its own independent state
- **Environment**: A deployment stage (dev, qa, or prod) that determines resource sizing, replica count, pipeline trigger rules, and access policies for a Target_Instance

## Requirements

### Requirement 1: AWS Infrastructure Provisioning

**User Story:** As a developer, I want to provision AWS infrastructure using Terraform, so that I have an EKS cluster ready to host my portfolio application.

#### Acceptance Criteria

1. WHEN the developer runs Terraform apply for the AWS module, THE Terraform_AWS_Module SHALL provision a VPC with a configurable CIDR block defaulting to 10.1.0.0/16, containing one public subnet and one private subnet in each of two availability zones (four subnets total)
2. WHEN the developer runs Terraform apply for the AWS module, THE Terraform_AWS_Module SHALL provision an EKS_Cluster with a single managed node group configured with a desired count of 1, a minimum count of 1, and a maximum count of 2, and SHALL NOT create the node group if the EKS_Cluster provisioning fails
3. THE Terraform_AWS_Module SHALL store its state in an S3 backend with DynamoDB locking, using a distinct S3 key path and bucket from the Azure Terraform state so that both state files are independently accessible
4. THE Terraform_AWS_Module SHALL tag all provisioned resources with an `environment` tag and a `project` tag, where both tag values are sourced from input variables
5. THE Terraform_AWS_Module SHALL configure the EKS_Cluster node group with a configurable instance type defaulting to t3.small, and a configurable Kubernetes version defaulting to a documented EKS-supported minor version in the format "X.Y"
6. IF Terraform apply fails due to insufficient permissions, THEN THE Terraform_AWS_Module SHALL exit with a non-zero status and produce an error message indicating the missing IAM permission, and SHALL only produce permission-related error messages when permissions are actually insufficient
7. WHEN the EKS_Cluster is provisioned, THE Terraform_AWS_Module SHALL output the cluster endpoint URL, cluster certificate authority data, and cluster name as named Terraform outputs sufficient to configure kubectl access

### Requirement 2: Container Image Management for AWS

**User Story:** As a developer, I want my Docker image pushed to an AWS-accessible registry, so that EKS can pull the application image during deployment.

#### Acceptance Criteria

1. WHEN the Pipeline builds a new image and the Target_List includes "aws", THE Pipeline SHALL authenticate with the ECR_Registry using AWS credentials and push the image to the ECR_Registry in addition to Docker Hub, and SHALL skip the ECR push entirely when the Target_List does not include "aws"
2. THE Terraform_AWS_Module SHALL provision the ECR_Registry with an image scanning configuration and an IAM policy that grants pull access to the EKS cluster nodes
3. THE ECR_Registry SHALL retain a maximum of 10 tagged image versions using a lifecycle policy, and SHALL expire any untagged images after 1 day
4. WHEN the Pipeline builds a new image, THE Pipeline SHALL tag the image with the numeric build identifier and a "latest" tag independently of whether the image is successfully pushed to the ECR_Registry
5. IF the Pipeline fails to authenticate with or push to the ECR_Registry when the Target_List includes "aws", THEN THE Pipeline SHALL fail the AWS build stage and report an error message indicating the ECR push failure, while other target stages continue independently

### Requirement 3: Kubernetes Deployment to EKS

**User Story:** As a developer, I want my application deployed to EKS with the same configuration as AKS, so that the application runs consistently across both clouds.

#### Acceptance Criteria

1. WHEN the Pipeline deploys to AWS, THE Pipeline SHALL apply Kubernetes manifests to the EKS_Cluster that include the same resource kinds as AKS: Namespace, Secret, PersistentVolumeClaim, Deployment, and Service
2. THE EKS_Cluster SHALL run the portfolio application with the same environment variables (SECRET_KEY from secret, DATABASE_PATH set to /app/data/portfolio.db), resource limits (256Mi memory, 500m CPU), resource requests (64Mi memory, 100m CPU), liveness probe (HTTP GET / on port 5000, initialDelaySeconds 10, periodSeconds 30), and readiness probe (HTTP GET / on port 5000, initialDelaySeconds 5, periodSeconds 10) as the AKS_Cluster
3. WHEN the deployment completes on the EKS_Cluster, THE Pipeline SHALL verify the rollout status of the portfolio deployment within a timeout of 180 seconds
4. THE EKS_Cluster SHALL use a PersistentVolumeClaim with ReadWriteOnce access mode and 256Mi storage capacity backed by Amazon EBS for the SQLite database file
5. IF the rollout fails on the EKS_Cluster, THEN THE Pipeline SHALL exit the EKS deployment stage with a non-zero status and log the failure reason, while all other targeted Deployment_Target stages continue executing independently without being blocked or failed
6. WHEN the Pipeline deploys to the EKS_Cluster, THE Pipeline SHALL first obtain cluster credentials by running `aws eks update-kubeconfig` using the cluster name and region from Terraform outputs

### Requirement 4: Ingress and TLS on AWS

**User Story:** As a developer, I want HTTPS traffic routed to my application on EKS, so that the AWS deployment is accessible securely via a domain name.

#### Acceptance Criteria

1. WHEN the Pipeline completes AWS infrastructure provisioning, THE Pipeline SHALL install the Ingress_Controller on the EKS_Cluster using Helm into a dedicated namespace
2. THE Ingress_Controller SHALL provision an AWS Network Load Balancer and obtain an external IP or hostname within 300 seconds of installation, and SHALL be considered failed if the load balancer provisions but no external IP or hostname is obtained
3. WHEN the Ingress_Controller is running, THE Pipeline SHALL install cert-manager on the EKS_Cluster via Helm, wait for the cert-manager webhook deployment to become available within 120 seconds, and apply a Let's Encrypt ClusterIssuer configured with an HTTP-01 solver
4. WHEN the Ingress_Controller receives an external IP or hostname, THE Pipeline SHALL create or update a Cloudflare DNS A record (or CNAME record for hostnames) for the `aws` subdomain (aws.orchidflow.io) to point to the AWS deployment, leaving the root domain and www subdomain pointing to the Azure deployment
5. THE EKS_Cluster SHALL serve the application over HTTPS with a TLS certificate issued by Let's Encrypt that matches the aws.orchidflow.io domain and is trusted by standard browsers
6. IF the Ingress_Controller does not receive an external IP or hostname within 300 seconds, THEN THE Pipeline SHALL terminate the deployment stage with a failure status
7. THE Ingress_Controller SHALL redirect all HTTP requests on port 80 to HTTPS on port 443

### Requirement 5: Scalable Multi-Target Deployment Selection

**User Story:** As a developer, I want to control which cloud target(s) receive a deployment using a configuration-driven approach, so that adding new targets requires only a config change and deployments run in parallel independently.

#### Acceptance Criteria

1. THE Pipeline SHALL read the Deploy_Targets_Config file (deploy-targets.yml at the project root) to determine which Deployment_Targets are available and enabled
2. WHEN the Pipeline is triggered automatically from source control, THE Pipeline SHALL deploy to all Deployment_Targets marked as enabled in the Deploy_Targets_Config
3. THE Pipeline SHALL accept an optional Target_List parameter containing an array of one or more Deployment_Target names that overrides the Deploy_Targets_Config enabled targets for that run
4. WHEN a Target_List is provided, THE Pipeline SHALL deploy only to the Deployment_Targets specified in the Target_List, regardless of the enabled status in the Deploy_Targets_Config
5. THE Pipeline SHALL execute deployments to all selected Deployment_Targets in parallel, treating each target as equal with no target designated as primary or ordered before another
6. WHEN one Deployment_Target deployment fails, THE Pipeline SHALL continue deploying to all other selected Deployment_Targets independently without blocking or failing them
7. THE Pipeline SHALL report overall success only when all selected Deployment_Target deployments succeed, and SHALL report overall failure with per-target status when one or more targets fail
8. IF a Target_List value contains a Deployment_Target name not defined in the Deploy_Targets_Config, THEN THE Pipeline SHALL fail the pipeline run before executing any deployment stage and report an error message identifying the unknown target name
9. THE Deploy_Targets_Config SHALL define each target with name, enabled, provider, region, environment, and trigger fields, where the provider field identifies which Provider_Module and K8s provider overlay to use, the environment field identifies which K8s environment overlay to apply, and the trigger field specifies the source control event that initiates deployment for that target — so that adding a new cloud target requires only adding a new entry to this file without modifying pipeline logic
10. THE Pipeline SHALL use the `provider` field from the Deploy_Targets_Config to determine which Kubernetes provider overlay and Terraform Provider_Module to apply for each target, so that multiple targets sharing the same provider reuse the same overlay and module logic without duplication
11. THE Pipeline SHALL support environment-based trigger rules where different environments deploy from different source control events (e.g., dev deploys on push to main, qa deploys on release branch, prod deploys on release tag or manual approval)
12. THE Pipeline SHALL accept an optional environment filter parameter that selects all enabled targets matching a specific environment (e.g., environment=prod deploys all enabled prod targets across all providers and regions)

### Requirement 6: AWS Credentials and Secrets Management

**User Story:** As a developer, I want AWS credentials managed securely in the pipeline, so that deployments authenticate to AWS without exposing secrets.

#### Acceptance Criteria

1. THE Pipeline SHALL authenticate to AWS using pipeline-stored credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION) retrieved from the CI/CD platform's secret storage mechanism
2. THE Pipeline SHALL pass AWS credentials to Terraform and kubectl commands exclusively via environment variables without writing them to disk or echoing them in build logs
3. WHEN the Pipeline deploys to EKS, THE Pipeline SHALL create or update a Kubernetes image pull secret for the ECR registry in the target deployment namespace using a dry-run and apply strategy to ensure idempotency, and IF the image pull secret creation fails, THEN THE Pipeline SHALL fail the entire EKS deployment stage
4. IF any of the required AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION) are unset or empty, THEN THE Pipeline SHALL fail the Terraform and EKS deployment stages before executing any AWS API calls, with an error message identifying which credential variable is missing
5. WHEN AWS credentials are available, THE Pipeline SHALL treat each deployment stage failure as isolated, allowing other stages with valid credentials to proceed or fail independently
6. IF AWS credentials are set but authentication to AWS fails, THEN THE Pipeline SHALL fail the current deployment stage with an error message indicating the authentication failure reason returned by AWS

### Requirement 7: Multi-Target Infrastructure Teardown and Re-Provisioning

**User Story:** As a developer, I want to tear down infrastructure for one or more targets independently when not in use and re-provision on demand, so that I avoid ongoing costs for learning environments that do not need to be online continuously.

#### Acceptance Criteria

1. THE Pipeline SHALL accept a Teardown_Action parameter that, when set to "destroy", triggers teardown instead of deployment, along with a Target_List parameter specifying one or more Deployment_Targets to tear down
2. WHEN the Teardown_Action is set to "destroy", THE Pipeline SHALL run `terraform destroy` in the target's directory under `infra/targets/{target-name}/` for each Deployment_Target specified in the Target_List, executing teardowns in parallel
3. WHEN the Teardown_Action is set to "destroy" for a target, THE Pipeline SHALL remove the corresponding Cloudflare DNS record for that target to avoid pointing to a non-existent endpoint
4. THE Pipeline SHALL preserve the Terraform state storage resources (S3 bucket and DynamoDB table for AWS, Azure storage account for Azure) during teardown, so that subsequent `terraform apply` can re-provision the infrastructure cleanly
5. WHEN the developer re-provisions a Deployment_Target after a teardown, THE Pipeline SHALL execute the full deployment flow (Terraform apply, Helm installs, manifest application) and restore the DNS record for that target
6. WHEN the Teardown_Action is set to "destroy", THE Pipeline SHALL skip all deployment-related stages for the specified targets and SHALL only execute destruction operations
7. IF the Teardown_Action is set to "destroy" and the target infrastructure does not exist, THEN THE Pipeline SHALL complete successfully without error (idempotent destroy)
8. THE ECR_Registry SHALL optionally be preserved or destroyed during AWS teardown based on a configurable pipeline parameter defaulting to "preserve"
9. WHEN multiple targets are specified for teardown, THE Pipeline SHALL execute each target teardown independently so that one target's teardown failure does not block or fail the teardown of other targets

### Requirement 8: Scalable Multi-Target File Organization

**User Story:** As a developer, I want infrastructure code and Kubernetes manifests organized in a four-level hierarchy (provider modules → environment overlays → target instances → K8s layering), so that adding a new region or environment for an existing provider requires only a thin target directory and a config entry without duplicating provider logic or environment configuration.

#### Acceptance Criteria

1. THE project SHALL organize reusable Terraform modules under `infra/modules/{provider}/` (e.g., `infra/modules/aws/` for VPC+EKS+ECR logic, `infra/modules/azure/` for VNet+AKS logic), where each Provider_Module is parameterized by region and target-specific variables
2. THE project SHALL organize target-specific Terraform configurations under `infra/targets/{target-name}/` using the naming convention `{environment}-{provider}-{region}` (e.g., `infra/targets/dev-aws-us-east-1/`, `infra/targets/prod-aws-us-east-1/`, `infra/targets/prod-azure-australiaeast/`), where each Target_Instance is a thin root module that calls its Provider_Module with target-specific variables (region, cluster name, environment) and maintains its own independent state backend
3. THE project SHALL organize cloud-agnostic shared Kubernetes manifests under `k8s/base/` containing Deployment, Service, and PVC template resources
4. THE project SHALL organize provider-specific Kubernetes patches under `k8s/providers/{provider}/` (e.g., `k8s/providers/aws/` for EBS StorageClass and NLB annotations, `k8s/providers/azure/` for managed disk StorageClass and Azure LB annotations), shared across all targets of that provider
5. THE project SHALL organize environment-specific Kubernetes patches under `k8s/environments/{environment}/` (e.g., `k8s/environments/dev/` for single-replica and debug logging, `k8s/environments/prod/` for multi-replica and production resource limits), shared across all targets of that environment regardless of provider
6. THE project SHALL organize optional target-specific Kubernetes overrides under `k8s/targets/{target-name}/` that inherit from the environment and provider overlays (usually minimal or empty)
7. WHEN multiple targets share the same environment, THE environment-specific K8s patches (replica count, resource limits, logging configuration) SHALL be authored once in `k8s/environments/{environment}/` and applied to all targets of that environment without duplication
8. WHEN a new region is added for an existing provider, THE developer SHALL only need to create a thin `infra/targets/{target-name}/` directory, optionally a `k8s/targets/{target-name}/` directory, and add an entry to the Deploy_Targets_Config file — without duplicating any provider logic, environment patches, or modifying existing target configurations, because environment patches are reused automatically via the environment field in the config
9. WHEN a new cloud provider is added, THE developer SHALL create an `infra/modules/{provider}/` directory, a `k8s/providers/{provider}/` directory, and at least one Target_Instance entry under `infra/targets/`
10. THE existing Azure Terraform configuration (currently in `terraform/`) SHALL be refactored into `infra/modules/azure/` (shared Provider_Module) and `infra/targets/prod-azure-australiaeast/` (thin root module). THE existing `terraform/` directory, `k8s/` flat structure, and `azure-pipelines.yml` SHALL be restructured or replaced to conform to the new multi-target layout.
11. EACH Target_Instance's Terraform root module under `infra/targets/{target-name}/` SHALL declare its own backend configuration and call the Provider_Module, with no cross-references between target directories
12. THE Pipeline SHALL compose Kubernetes manifests by layering four levels: `k8s/base/` → `k8s/providers/{provider}/` → `k8s/environments/{environment}/` → `k8s/targets/{target-name}/` (using Kustomize or equivalent), where provider patches handle cloud-specific resources (StorageClass, LB annotations), environment patches handle sizing and operational config (replica count, resource limits, logging level), and target patches handle instance-unique overrides
13. THE project SHALL maintain a Deploy_Targets_Config file (deploy-targets.yml) at the project root that lists all Deployment_Targets with their name, enabled status, provider, region, environment, and trigger fields
14. THE Pipeline SHALL use a main deploy pipeline file (`pipelines/deploy.yml`) that reads the Deploy_Targets_Config and fans out to per-target deployment stages, and a separate teardown pipeline file (`pipelines/teardown.yml`)
15. THE project SHALL separate concerns across the target matrix as follows: Terraform module logic and K8s provider patches (StorageClass, LB annotations) are shared across all targets of the same provider; K8s environment patches (replica count, resource limits, logging level, debug config) are shared across all targets of the same environment; cluster name, Terraform state, DNS subdomain, and specific variable values are unique per target

### Requirement 9: Deployment Rollback and Recovery

**User Story:** As a developer, I want to quickly roll back a deployment to a known-good version when a major issue is discovered in production, so that application users are not affected by broken releases.

#### Acceptance Criteria

1. THE Kubernetes Deployment manifest SHALL configure a `revisionHistoryLimit` of at least 5, so that Kubernetes retains previous ReplicaSets sufficient for rollback
2. WHEN a major issue is discovered post-deployment, THE developer SHALL be able to execute `kubectl rollout undo deployment/portfolio -n {namespace}` on any target cluster to immediately revert to the previous working version without running the full pipeline
3. THE Pipeline SHALL accept an optional `image_tag` parameter that, when provided, skips the image build stage and deploys the specified pre-built image tag to the selected targets
4. WHEN the `image_tag` parameter is provided, THE Pipeline SHALL verify that the specified tag exists in the target registry (Docker Hub or ECR) before attempting deployment, and SHALL fail with a descriptive error if the tag is not found
5. THE Pipeline SHALL retain at least 10 tagged image versions in each container registry (Docker Hub and ECR) so that rollback to any of the last 10 builds is possible via the `image_tag` parameter
6. WHEN a rollout is in progress and the new pods fail health checks within the rollout timeout (180 seconds), THE Kubernetes Deployment SHALL automatically halt the rollout and keep the previous healthy pods serving traffic (default rolling update behavior)
7. THE Pipeline SHALL log the deployed image tag for each target at the end of a successful deployment stage, so that the last known-good tag is easily identifiable in pipeline history

### Requirement 10: Zero-Downtime Deployment Configuration

**User Story:** As a developer, I want deployments to complete without dropping any in-flight requests or causing user-visible errors, so that application users experience no interruption during releases.

#### Acceptance Criteria

1. THE Kubernetes Deployment manifest in `k8s/base/` SHALL configure a rolling update strategy with `maxUnavailable: 0` and `maxSurge: 1`, ensuring that the old pod is never terminated before the new pod is ready to receive traffic
2. THE Kubernetes Deployment manifest SHALL configure `terminationGracePeriodSeconds` of at least 60 seconds, giving in-flight requests sufficient time to complete before the pod is forcefully terminated
3. THE Kubernetes container spec SHALL include a `preStop` lifecycle hook that executes `sleep 5` before the application receives SIGTERM, allowing the ingress controller time to remove the pod from its routing table before shutdown begins
4. WHEN the application container receives SIGTERM, THE application (Gunicorn) SHALL stop accepting new connections and finish processing all in-flight requests before exiting, within the termination grace period
5. THE Kubernetes Deployment manifest SHALL configure a readiness probe so that new pods only receive traffic after the application is fully initialized and responding to health checks
6. WHEN a rolling update is in progress, THE Kubernetes cluster SHALL maintain at least one pod in a ready state serving traffic at all times, ensuring no gap in availability between old and new versions
7. THE `k8s/environments/prod/` overlay SHALL configure `replicas: 2` or higher for production targets, ensuring that at least one pod remains available during rolling updates even if the new pod takes time to become ready
8. THE `k8s/environments/dev/` overlay MAY configure `replicas: 1` for cost savings, accepting that a brief availability gap is possible during deployments in non-production environments
