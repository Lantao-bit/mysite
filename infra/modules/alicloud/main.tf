# -----------------------------------------------------------------------------
# VPC + vSwitches
# -----------------------------------------------------------------------------

data "alicloud_zones" "available" {
  available_resource_creation = "VSwitch"
  available_instance_type     = var.instance_type
}

locals {
  zones = slice(data.alicloud_zones.available.zones[*].id, 0, min(2, length(data.alicloud_zones.available.zones[*].id)))
}

resource "alicloud_vpc" "main" {
  vpc_name   = "${var.project_name}-${var.environment}-vpc"
  cidr_block = var.vpc_cidr

  tags = {
    Target    = var.environment
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

resource "alicloud_vswitch" "main" {
  count = length(local.zones)

  vswitch_name = "${var.project_name}-${var.environment}-vsw-${count.index}"
  vpc_id       = alicloud_vpc.main.id
  cidr_block   = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  zone_id      = local.zones[count.index]

  tags = {
    Target    = var.environment
    Project   = var.project_name
    ManagedBy = "terraform"
  }

  timeouts {
    create = "10m"
    delete = "15m"
  }
}

# -----------------------------------------------------------------------------
# ACK Managed Kubernetes Cluster
# -----------------------------------------------------------------------------

resource "alicloud_cs_managed_kubernetes" "main" {
  name    = var.cluster_name
  version = var.k8s_version

  vswitch_ids = alicloud_vswitch.main[*].id

  new_nat_gateway      = true
  slb_internet_enabled = true

  pod_cidr     = "172.20.0.0/16"
  service_cidr = "172.21.0.0/20"

  tags = {
    Target    = var.environment
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# -----------------------------------------------------------------------------
# Node Pool (replaces deprecated worker_* fields)
# -----------------------------------------------------------------------------

resource "alicloud_cs_kubernetes_node_pool" "main" {
  cluster_id     = alicloud_cs_managed_kubernetes.main.id
  node_pool_name = "${var.cluster_name}-pool"
  vswitch_ids    = alicloud_vswitch.main[*].id
  desired_size = 1

  instance_types       = [var.instance_type]
  system_disk_category = "cloud_essd"
  system_disk_size     = 40

  tags = {
    Target    = var.environment
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}
