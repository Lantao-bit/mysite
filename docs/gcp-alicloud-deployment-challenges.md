# Deployment Challenges and Solutions: GCP and Alicloud

This document summarizes the challenges encountered and solutions applied when deploying the portfolio application to GCP (Google Cloud Platform) and Alicloud (Alibaba Cloud) targets.

## GCP (dev-gcp-asia-southeast1)

### 1. Wrong Project ID in Terraform

**Challenge:** Terraform was using a hardcoded project ID `portfolio-gcp` instead of the actual project `mysite-499605`. Despite updating the `GCP_PROJECT_ID` secret, Terraform never received the value.

**Root Cause:** The project ID was hardcoded in `infra/targets/dev-gcp-asia-southeast1/main.tf` and `scripts/generate-targets.py`. The deploy workflow set `GCP_PROJECT` for gcloud CLI but never passed `TF_VAR_project_id` to Terraform.

**Solution:**
- Added `TF_VAR_project_id` and `GOOGLE_CLOUD_PROJECT` env vars to deploy and teardown workflows
- Changed target `main.tf` to declare `variable "project_id"` and pass `var.project_id` to the module
- Updated `generate-targets.py` template accordingly

### 2. GKE Kubernetes Version Not Available

**Challenge:** GKE returned `No valid versions with the prefix "1.31" found` and later the same for `1.32`.

**Root Cause:** GKE skipped Kubernetes 1.31 entirely and version availability varies by region. The REGULAR release channel in `asia-southeast1` required a full version string.

**Solution:** Set `k8s_version` to the exact version `1.35.5-gke.1241000` (confirmed available in the region).

### 3. Compute Engine Resource Exhaustion

**Challenge:** `Google Compute Engine does not have enough resources available to fulfill request: asia-southeast1`

**Root Cause:** Temporary capacity constraints in the `asia-southeast1` region. Regional clusters need resources across multiple zones.

**Solution:** Re-ran the pipeline after capacity freed up. Alternative options include switching to a specific zone or a different region.

### 4. SSD Quota Exceeded

**Challenge:** `Quota 'SSD_TOTAL_GB' exceeded. Limit: 250.0 in region asia-southeast1`

**Root Cause:** GKE's temporary default node pool was using `pd-ssd` boot disks, consuming SSD quota.

**Solution:** Added `node_config` block to the cluster resource with `disk_type = "pd-standard"` and `disk_size_gb = 30` for the initial (temporary) default pool.

### 5. gke-gcloud-auth-plugin Not Found

**Challenge:** kubectl couldn't authenticate to the GKE cluster — `executable gke-gcloud-auth-plugin not found`.

**Root Cause:** The GitHub Actions runner has gcloud installed via apt, which disables `gcloud components`. The auth plugin wasn't pre-installed.

**Solution:** Added `google-github-actions/setup-gcloud@v2` action with `install_components: gke-gcloud-auth-plugin` before the kubectl configuration step.

### 6. Teardown Missing TF_VAR_project_id

**Challenge:** Teardown workflow failed with `No value for required variable "project_id"`.

**Root Cause:** The teardown workflow's Terraform Destroy step didn't include `TF_VAR_project_id` in its env vars.

**Solution:** Added `TF_VAR_project_id` and `GOOGLE_CLOUD_PROJECT` to the teardown workflow's env block.

---

## Alicloud (dev-alicloud-cn-hangzhou)

### 1. RAM Sub-User Permission Denied

**Challenge:** `Forbidden.RAM: User not authorized to operate on the specified resource`

**Root Cause:** The RAM sub-user lacked necessary policies for VPC, NAT Gateway, SLB, and ROS operations.

**Solution:** Attached the following account-level policies to the sub-user:
- `AliyunVPCFullAccess`
- `AliyunCSFullAccess`
- `AliyunECSFullAccess`
- `AliyunNATGatewayFullAccess`
- `AliyunSLBFullAccess`
- `AliyunROSFullAccess`

### 2. Service-Linked Roles Not Created

**Challenge:** `EntityNotExist.Role: The role not exists: aliyuncsdefaultrole`

**Root Cause:** First-time ACK usage requires pre-created service-linked roles that ACK assumes internally.

**Solution:** Visited the [ACK Console](https://cs.console.aliyun.com) which prompted automatic role authorization, and separately authorized `AliyunOOSLifecycleHook4CSRole` via the RAM role authorization URL.

### 3. Real-Name Authentication Required

**Challenge:** `RealNameAuthenticationError: Your account has not passed the real-name authentication yet`

**Root Cause:** Alibaba Cloud requires identity verification before creating Kubernetes clusters (Chinese regulatory requirement).

**Solution:** Completed real-name authentication in the Alibaba Cloud account settings.

### 4. Risk Control Check Failed

**Challenge:** `OperationFailed.RiskControl: Risk control check failed`

**Root Cause:** New account without payment method triggered fraud prevention system.

**Solution:** Added a valid payment method to the Alibaba Cloud account.

### 5. Kubernetes Version Not Available

**Challenge:** `no ros component exists. clusterType: ManagedKubernetes, version: 1.30/1.31/1.32/1.35`

**Root Cause:** ACK uses its own version scheme (e.g., `1.36.1-aliyun.1`). Standard Kubernetes version numbers don't match ACK's internal ROS templates.

**Solution:** Used the exact version from the ACK console: `1.36.1-aliyun.1`.

### 6. Instance Type Not Available in Zone

**Challenge:** `InstanceType.Unauthorized: The instanceTypes are not authorized or not supported in current zones`

**Root Cause:** `ecs.g6.large` wasn't available in the dynamically selected zones. Instance availability varies by zone.

**Solution:**
- Changed instance type to `ecs.c9i.large` (confirmed available in Zone B)
- Updated zone data source to filter by `available_instance_type` so VSwitches are only created in zones where the instance type exists

### 7. China Firewall Blocking Container Registries

**Challenge:** Pods couldn't pull images from `registry.k8s.io` (ingress-nginx) or `docker.io` (application image) — all timed out.

**Root Cause:** The Great Firewall of China blocks or severely throttles access to international container registries from mainland China nodes.

**Solution:**
- Skipped ingress-nginx and cert-manager installation for Alicloud target
- Changed service type to `LoadBalancer` (direct SLB) instead of using Ingress
- Created an Alibaba Container Registry (ACR) personal instance
- Pipeline pushes the application image to ACR (public endpoint) during build
- ACK nodes pull from ACR (VPC endpoint) for faster, reliable access

### 8. PVC Minimum Disk Size

**Challenge:** `pod has unbound immediate PersistentVolumeClaims` — PVC stuck in Pending.

**Root Cause:** Alibaba Cloud ESSD disks have a minimum size of 20Gi. The PVC requested only 256Mi.

**Solution:** Updated the Alicloud PVC patch to request `20Gi` storage.

### 9. StorageClass Immutable Field

**Challenge:** `StorageClass "alicloud-disk-essd" is invalid: volumeBindingMode: field is immutable`

**Root Cause:** ACK pre-creates the `alicloud-disk-essd` StorageClass. Re-applying it via Kustomize with a different `volumeBindingMode` failed.

**Solution:** Removed the StorageClass from Alicloud's Kustomize resources (relying on ACK's built-in one).

### 10. Stale cert-manager Webhook Blocking Resource Creation

**Challenge:** `failed calling webhook "webhook.cert-manager.io": no endpoints available`

**Root Cause:** A previous failed cert-manager install left ValidatingWebhookConfigurations that intercepted all cert-manager CRD operations, but no cert-manager pods were running.

**Solution:**
- Added a cleanup step to delete stale cert-manager webhooks before Kustomize deploy for Alicloud
- Moved `cert-manager-issuer.yaml` out of base Kustomize into provider-specific layers (only AWS, Azure, GCP include it)

### 11. ACR Image Pull Authorization

**Challenge:** `pull access denied, repository does not exist or may require authorization`

**Root Cause:** ACK nodes need credentials to pull from the private ACR repository.

**Solution:**
- Created `acr-pull-secret` Kubernetes secret with ACR VPC endpoint credentials
- Added a Kustomize deployment patch for Alicloud to use `imagePullSecrets: acr-pull-secret`

### 12. kubectl Cluster ID vs Name

**Challenge:** `aliyun cs GET /k8s/<cluster-name>/user_config` returned 404 even though the cluster existed.

**Root Cause:** The Alibaba Cloud CS API requires the cluster **ID** (not name) in the URL path.

**Solution:** Updated the pipeline to first list clusters, find the ID by name, then use the ID to fetch the kubeconfig.

### 13. ICP Filing for Domain Access

**Challenge:** `ali.orchidflow.io` and the IP on port 80/443 are unreachable, but `IP:5000` works.

**Root Cause:** Mainland China requires ICP filing (备案) for any domain pointing to a Chinese IP address. Without it, ISPs block standard web ports.

**Current Status:** Application accessible at `http://<IP>:5000`. Full domain access requires ICP filing (1-3 weeks) or switching to a non-China Alibaba region.

### 14. Teardown Missing AWS Credentials for S3 Backend

**Challenge:** `No valid credential sources found` when running Terraform destroy for Alicloud.

**Root Cause:** The Alicloud target uses an S3 backend for Terraform state, which requires AWS credentials. The teardown workflow didn't pass `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.

**Solution:** Added AWS credentials to the teardown workflow's Terraform Destroy env vars.

---

## Key Lessons

1. **China deployments are fundamentally different** — network restrictions (GFW), regulatory requirements (ICP, real-name auth), and unique versioning require China-specific handling at every layer.

2. **Terraform variables should come from pipeline secrets**, not hardcoded values — prevents stale project IDs and makes the same code work across environments.

3. **Service-linked roles are a one-time setup** — cloud providers require pre-authorized roles before managed services can operate. Visit the respective console once to complete authorization.

4. **Container registries must be reachable from the cluster** — in China, this means using a local registry (ACR) rather than Docker Hub or Google's registry.

5. **Kustomize provider layers enable clean per-cloud customization** — ingress strategy, StorageClass, pull secrets, and service types can differ without touching shared base manifests.
