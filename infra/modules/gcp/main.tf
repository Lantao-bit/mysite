# -----------------------------------------------------------------------------
# VPC Network
# -----------------------------------------------------------------------------

resource "google_compute_network" "main" {
  name                    = "${var.project_name}-${var.environment}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.project_name}-${var.environment}-subnet"
  ip_cidr_range = var.network_cidr
  region        = var.region
  network       = google_compute_network.main.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.100.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.101.0.0/20"
  }
}

# -----------------------------------------------------------------------------
# GKE Cluster
# -----------------------------------------------------------------------------

resource "google_container_cluster" "main" {
  name     = var.cluster_name
  location = var.region

  network    = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.main.id

  # We use a separately managed node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  min_master_version = var.k8s_version

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  release_channel {
    channel = "REGULAR"
  }

  deletion_protection = false
}

resource "google_container_node_pool" "primary" {
  name       = "${var.cluster_name}-pool"
  location   = var.region
  cluster    = google_container_cluster.main.name
  node_count = 1

  node_config {
    machine_type = var.machine_type
    disk_size_gb = 50
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      target     = var.environment
      project    = var.project_name
      managed_by = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Artifact Registry
# -----------------------------------------------------------------------------

resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "${var.project_name}-repo"
  description   = "Docker repository for ${var.project_name}"
  format        = "DOCKER"
}
