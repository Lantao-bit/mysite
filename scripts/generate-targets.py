#!/usr/bin/env python3
"""
Generate Terraform and K8s target files from deploy-targets.yml.

Usage:
    python scripts/generate-targets.py

This script reads deploy-targets.yml and generates:
  - infra/targets/{name}/main.tf, backend.tf, versions.tf
  - k8s/targets/{name}/kustomization.yaml, ingress-host-patch.yaml

Run after editing deploy-targets.yml to keep generated files in sync.
"""

import os
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_TARGETS = ROOT / "deploy-targets.yml"


def load_targets():
    with open(DEPLOY_TARGETS) as f:
        data = yaml.safe_load(f)
    return data.get("targets", [])


def derive_values(target):
    """Derive cluster_name, resource_group, registry from target attributes."""
    name = target["name"]
    provider = target["provider"]

    target["cluster_name"] = f"portfolio-{name}"
    target["registry"] = {
        'aws': 'ecr',
        'azure': 'dockerhub',
        'gcp': 'dockerhub',
        'sap': 'dockerhub',
        'alicloud': 'dockerhub'
    }.get(provider, 'dockerhub')

    if provider == "azure":
        target["resource_group"] = f"portfolio-rg-{name}"

    return target


def validate_targets(targets):
    """Run consistency checks and warn on issues."""
    warnings = []
    for t in targets:
        # Warn if github_environment is production but triggers on main
        env = t.get("github_environment", "")
        branches = t.get("trigger", {}).get("branches", [])
        if env == "production" and "main" in branches:
            warnings.append(
                f"  ⚠ Target '{t['name']}': github_environment is 'production' "
                f"but triggers on 'main' branch. This means every push to main "
                f"will require manual approval."
            )

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(w)
        print()

    return len(warnings) == 0


# ─── Terraform generators ─────────────────────────────────────────────────────

def generate_terraform_aws(target):
    name = target["name"]
    region = target["region"]
    cluster_name = target["cluster_name"]
    # First AWS target owns ECR, others reference it
    is_first_aws = target.get("_is_first_aws", False)

    main_tf = f'''module "aws" {{
  source = "../../modules/aws"

  region       = "{region}"
  cluster_name = "{cluster_name}"
  environment  = "{name}"
  project_name = "portfolio"
  vpc_cidr     = "{target.get('_vpc_cidr', '10.1.0.0/16')}"
  instance_type = "t3.medium"
  k8s_version  = "1.36"
  create_ecr   = {"true" if is_first_aws else "false"}

  cluster_admin_arns = [
    "arn:aws:iam::712416941115:user/OFP_Admin",
  ]
}}

output "cluster_endpoint" {{
  value = module.aws.cluster_endpoint
}}

output "cluster_name" {{
  value = module.aws.cluster_name
}}

output "ecr_repo_url" {{
  value = module.aws.ecr_repository_url
}}
'''

    backend_tf = f'''terraform {{
  backend "s3" {{
    bucket       = "portfolio-tfstate-712416941115"
    key          = "{name}/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }}
}}
'''

    versions_tf = '''terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
'''

    return {"main.tf": main_tf, "backend.tf": backend_tf, "versions.tf": versions_tf}


def generate_terraform_azure(target):
    name = target["name"]
    region = target["region"]
    cluster_name = target["cluster_name"]
    resource_group = target["resource_group"]

    main_tf = f'''module "azure" {{
  source = "../../modules/azure"

  location            = "{region}"
  resource_group_name = "{resource_group}"
  aks_cluster_name    = "{cluster_name}"
  target_name         = "{name}"
  project_name        = "portfolio"
  kubernetes_version  = "1.34"
}}

output "cluster_endpoint" {{
  value     = module.azure.cluster_endpoint
  sensitive = true
}}

output "cluster_name" {{
  value = module.azure.cluster_name
}}
'''

    backend_tf = f'''terraform {{
  backend "azurerm" {{
    resource_group_name  = "tfstate-rg"
    storage_account_name = "ylt202605201452"
    container_name       = "tfstate"
    key                  = "{name}.terraform.tfstate"
  }}
}}
'''

    versions_tf = '''terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {}
}
'''

    return {"main.tf": main_tf, "backend.tf": backend_tf, "versions.tf": versions_tf}


def generate_terraform_gcp(target):
    name = target["name"]
    region = target["region"]
    cluster_name = target["cluster_name"]

    main_tf = f'''module "gcp" {{
  source = "../../modules/gcp"

  region       = "{region}"
  cluster_name = "{cluster_name}"
  project_id   = "portfolio-gcp"
  environment  = "{name}"
  project_name = "portfolio"
  k8s_version  = "1.31"
}}

output "cluster_endpoint" {{
  value = module.gcp.cluster_endpoint
}}

output "cluster_name" {{
  value = module.gcp.cluster_name
}}

output "artifact_registry_url" {{
  value = module.gcp.artifact_registry_url
}}
'''

    backend_tf = f'''terraform {{
  backend "gcs" {{
    bucket = "portfolio-tfstate-gcp"
    prefix = "{name}/terraform.tfstate"
  }}
}}
'''

    versions_tf = '''terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
'''

    return {"main.tf": main_tf, "backend.tf": backend_tf, "versions.tf": versions_tf}


def generate_terraform_sap(target):
    name = target["name"]
    region = target["region"]
    cluster_name = target["cluster_name"]

    main_tf = f'''module "sap" {{
  source = "../../modules/sap"

  region         = "{region}"
  cluster_name   = "{cluster_name}"
  environment    = "{name}"
  project_name   = "portfolio"
  subaccount_id  = "placeholder-subaccount-id"
  globalaccount  = "placeholder-globalaccount"
}}

output "cluster_name" {{
  value = module.sap.cluster_name
}}

output "kubeconfig_url" {{
  value = module.sap.kubeconfig_url
}}
'''

    backend_tf = f'''terraform {{
  backend "s3" {{
    bucket       = "portfolio-tfstate-712416941115"
    key          = "{name}/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }}
}}
'''

    versions_tf = '''terraform {
  required_version = ">= 1.0"

  required_providers {
    btp = {
      source  = "sap/btp"
      version = "~> 1.0"
    }
  }
}
'''

    return {"main.tf": main_tf, "backend.tf": backend_tf, "versions.tf": versions_tf}


def generate_terraform_alicloud(target):
    name = target["name"]
    region = target["region"]
    cluster_name = target["cluster_name"]

    main_tf = f'''module "alicloud" {{
  source = "../../modules/alicloud"

  region       = "{region}"
  cluster_name = "{cluster_name}"
  environment  = "{name}"
  project_name = "portfolio"
  vpc_cidr     = "{target.get('_vpc_cidr', '10.4.0.0/16')}"
  k8s_version  = "1.30"
}}

output "cluster_endpoint" {{
  value = module.alicloud.cluster_endpoint
}}

output "cluster_name" {{
  value = module.alicloud.cluster_name
}}

output "acr_registry_url" {{
  value = module.alicloud.acr_registry_url
}}
'''

    backend_tf = f'''terraform {{
  backend "oss" {{
    bucket = "portfolio-tfstate-ali"
    prefix = "{name}/terraform.tfstate"
    region = "cn-hangzhou"
  }}
}}
'''

    versions_tf = '''terraform {
  required_version = ">= 1.0"

  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.200"
    }
  }
}
'''

    return {"main.tf": main_tf, "backend.tf": backend_tf, "versions.tf": versions_tf}


# ─── K8s generators ───────────────────────────────────────────────────────────

def generate_k8s(target):
    name = target["name"]
    provider = target["provider"]
    dns_subdomain = target.get("dns_subdomain", "")
    replicas = target.get("replicas", 1)
    resources = target.get("resources", {})

    # Determine host(s)
    domain = "orchidflow.io"
    if dns_subdomain:
        hosts = [f"{dns_subdomain}.{domain}"]
    else:
        hosts = [domain, f"www.{domain}"]

    # Determine TLS secret name
    tls_secret = f"portfolio-tls-{name}"

    # Build ingress host patch
    rules_yaml = ""
    for host in hosts:
        rules_yaml += f"""    - host: {host}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: portfolio-service
                port:
                  number: 5000
"""

    hosts_yaml = "\n".join(f"        - {h}" for h in hosts)

    ingress_patch = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: portfolio-ingress
  namespace: portfolio
spec:
  tls:
    - hosts:
{hosts_yaml}
      secretName: {tls_secret}
  rules:
{rules_yaml}"""

    # Build kustomization.yaml
    cpu_req = resources.get("cpu_request", "100m")
    cpu_lim = resources.get("cpu_limit", "500m")
    mem_req = resources.get("memory_request", "64Mi")
    mem_lim = resources.get("memory_limit", "256Mi")

    # Image override for ECR targets
    if provider == "aws":
        image_section = f"""images:
  - name: ltyang/portfolio
    newName: 712416941115.dkr.ecr.{target['region']}.amazonaws.com/portfolio
    newTag: latest"""
    else:
        image_section = """images:
  - name: ltyang/portfolio
    newName: ltyang/portfolio
    newTag: latest"""

    kustomization = f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../providers/{provider}
patches:
  - path: ingress-host-patch.yaml
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: portfolio
        namespace: portfolio
      spec:
        replicas: {replicas}
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: portfolio
        namespace: portfolio
      spec:
        template:
          spec:
            containers:
              - name: portfolio
                resources:
                  requests:
                    memory: "{mem_req}"
                    cpu: "{cpu_req}"
                  limits:
                    memory: "{mem_lim}"
                    cpu: "{cpu_lim}"
{image_section}
"""

    return {
        "kustomization.yaml": kustomization,
        "ingress-host-patch.yaml": ingress_patch,
    }


# ─── File writing ─────────────────────────────────────────────────────────────

def write_files(directory, files):
    """Write files to directory, creating it if needed."""
    directory.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        filepath = directory / filename
        filepath.write_text(content)


def main():
    targets = load_targets()

    if not targets:
        print("No targets found in deploy-targets.yml")
        sys.exit(1)

    # Derive values
    aws_targets = []
    alicloud_targets = []
    for t in targets:
        derive_values(t)
        if t["provider"] == "aws":
            aws_targets.append(t)
        elif t["provider"] == "alicloud":
            alicloud_targets.append(t)

    # Assign VPC CIDRs and first-AWS flag
    for i, t in enumerate(aws_targets):
        t["_vpc_cidr"] = f"10.{i + 1}.0.0/16"
        t["_is_first_aws"] = (i == 0)

    # Assign VPC CIDRs for Alibaba targets (starting from 10.4.0.0/16)
    for i, t in enumerate(alicloud_targets):
        t["_vpc_cidr"] = f"10.{i + 4}.0.0/16"

    # Validate
    validate_targets(targets)

    # Generate files
    print("Generating target files...")
    for t in targets:
        name = t["name"]
        provider = t["provider"]

        # Terraform
        tf_dir = ROOT / "infra" / "targets" / name
        if provider == "aws":
            tf_files = generate_terraform_aws(t)
        elif provider == "azure":
            tf_files = generate_terraform_azure(t)
        elif provider == "gcp":
            tf_files = generate_terraform_gcp(t)
        elif provider == "sap":
            tf_files = generate_terraform_sap(t)
        elif provider == "alicloud":
            tf_files = generate_terraform_alicloud(t)
        else:
            print(f"  ⚠ Unknown provider '{provider}' for target '{name}' — skipping Terraform")
            continue

        write_files(tf_dir, tf_files)
        print(f"  ✓ infra/targets/{name}/")

        # K8s
        k8s_dir = ROOT / "k8s" / "targets" / name
        k8s_files = generate_k8s(t)
        write_files(k8s_dir, k8s_files)
        print(f"  ✓ k8s/targets/{name}/")

    print(f"\nDone. Generated files for {len(targets)} target(s).")
    print("Review changes and commit.")


if __name__ == "__main__":
    main()
