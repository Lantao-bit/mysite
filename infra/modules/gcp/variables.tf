variable "region" {
  description = "GCP region for all resources"
  type        = string
}

variable "zone" {
  description = "GCP zone (used for zonal resources if needed)"
  type        = string
  default     = ""
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Deploy target name (used for tagging all resources)"
  type        = string
}

variable "project_name" {
  description = "Project name tag"
  type        = string
  default     = "portfolio"
}

variable "machine_type" {
  description = "GCE machine type for GKE nodes"
  type        = string
  default     = "e2-medium"
}

variable "k8s_version" {
  description = "Kubernetes version for the GKE cluster"
  type        = string
  default     = "1.32"
}

variable "network_cidr" {
  description = "CIDR block for the VPC subnet"
  type        = string
  default     = "10.3.0.0/16"
}
