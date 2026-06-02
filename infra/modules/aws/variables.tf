variable "region" {
  description = "AWS region for all resources"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "environment" {
  description = "Environment tag (dev, qa, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name tag"
  type        = string
  default     = "portfolio"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "instance_type" {
  description = "EC2 instance type for EKS node group"
  type        = string
  default     = "t3.small"
}

variable "k8s_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "node_desired" {
  description = "Desired number of nodes in the EKS node group"
  type        = number
  default     = 1
}

variable "node_min" {
  description = "Minimum number of nodes in the EKS node group"
  type        = number
  default     = 1
}

variable "node_max" {
  description = "Maximum number of nodes in the EKS node group"
  type        = number
  default     = 2
}

variable "ecr_repo_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "portfolio"
}
