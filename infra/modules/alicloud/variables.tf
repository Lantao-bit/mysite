variable "region" {
  description = "Alibaba Cloud region for all resources"
  type        = string
}

variable "cluster_name" {
  description = "Name of the ACK cluster"
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

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.4.0.0/16"
}

variable "instance_type" {
  description = "ECS instance type for ACK worker nodes"
  type        = string
  default     = "ecs.g6.large"
}

variable "k8s_version" {
  description = "Kubernetes version for the ACK cluster"
  type        = string
  default     = "1.36.1-aliyun.1"
}
