# -----------------------------------------------------------------------------
# VPC + vSwitches
# -----------------------------------------------------------------------------

data "alicloud_zones" "available" {
  available_resource_creation = "VSwitch"
}

locals {
  zones = slice(data.alicloud_zones.available.zones[*].id, 0, 2)
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
  count = 2

  vswitch_name = "${var.project_name}-${var.environment}-vsw-${count.index}"
  vpc_id       = alicloud_vpc.main.id
  cidr_block   = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  zone_id      = local.zones[count.index]

  tags = {
    Target    = var.environment
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# -----------------------------------------------------------------------------
# ACK Managed Kubernetes Cluster
# -----------------------------------------------------------------------------

resource "alicloud_cs_managed_kubernetes" "main" {
  name    = var.cluster_name
  version = var.k8s_version

  vswitch_ids = alicloud_vswitch.main[*].id

  worker_vswitch_ids = alicloud_vswitch.main[*].id

  new_nat_gateway      = true
  slb_internet_enabled = true

  worker_instance_types = [var.instance_type]
  worker_number         = 1
  worker_disk_size      = 40
  worker_disk_category  = "cloud_essd"

  pod_cidr     = "172.20.0.0/16"
  service_cidr = "172.21.0.0/20"

  tags = {
    Target    = var.environment
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# -----------------------------------------------------------------------------
# Container Registry (ACR)
# -----------------------------------------------------------------------------

resource "alicloud_cr_namespace" "main" {
  name               = var.project_name
  auto_create        = false
  default_visibility = "PRIVATE"
}

resource "alicloud_cr_repo" "main" {
  namespace = alicloud_cr_namespace.main.name
  name      = var.project_name
  summary   = "Docker repository for ${var.project_name}"
  repo_type = "PRIVATE"
}
