#!/usr/bin/env python3
"""Kustomize build validation script.

Runs `kustomize build` (or `kubectl kustomize`) for each target in k8s/targets/
and validates the output contains expected resources with correct configuration.

Validates:
- Required resource kinds are present (Namespace, Deployment, Service, PersistentVolumeClaim, Ingress)
- Prod targets have replicas: 2, dev targets have replicas: 1
- AWS targets have StorageClass named "ebs-gp3"
- Azure targets have StorageClass named "managed-premium"

Requirements: 3.1, 3.2, 8.12
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# Project root is one level up from the scripts/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
K8S_TARGETS_DIR = PROJECT_ROOT / "k8s" / "targets"

REQUIRED_KINDS = {"Namespace", "Deployment", "Service", "PersistentVolumeClaim", "Ingress"}


def find_kustomize_command():
    """Determine which command to use for kustomize build."""
    # Try kustomize binary first
    try:
        subprocess.run(
            ["kustomize", "version"],
            capture_output=True,
            check=True,
        )
        return ["kustomize", "build"]
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Fall back to kubectl kustomize
    try:
        subprocess.run(
            ["kubectl", "version", "--client"],
            capture_output=True,
            check=True,
        )
        return ["kubectl", "kustomize"]
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return None


def run_kustomize_build(target_dir, kustomize_cmd):
    """Run kustomize build for a target directory and return parsed YAML documents."""
    cmd = kustomize_cmd + [str(target_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return None, result.stderr

    documents = list(yaml.safe_load_all(result.stdout))
    # Filter out None documents (empty YAML separators)
    documents = [doc for doc in documents if doc is not None]
    return documents, None


def get_resource_kinds(documents):
    """Extract all resource kinds from parsed YAML documents."""
    kinds = set()
    for doc in documents:
        if isinstance(doc, dict) and "kind" in doc:
            kinds.add(doc["kind"])
    return kinds


def get_deployment_replicas(documents):
    """Get the replicas value from the Deployment resource."""
    for doc in documents:
        if isinstance(doc, dict) and doc.get("kind") == "Deployment":
            spec = doc.get("spec", {})
            return spec.get("replicas")
    return None


def get_storageclass_names(documents):
    """Get all StorageClass names from the documents."""
    names = []
    for doc in documents:
        if isinstance(doc, dict) and doc.get("kind") == "StorageClass":
            metadata = doc.get("metadata", {})
            name = metadata.get("name")
            if name:
                names.append(name)
    return names


def validate_target(target_name, documents):
    """Validate a single target's kustomize build output. Returns list of (check, passed, message)."""
    results = []

    # Check 1: Required resource kinds
    kinds = get_resource_kinds(documents)
    missing_kinds = REQUIRED_KINDS - kinds
    if missing_kinds:
        results.append((
            "Required resource kinds",
            False,
            f"Missing kinds: {', '.join(sorted(missing_kinds))}",
        ))
    else:
        results.append((
            "Required resource kinds",
            True,
            f"All present: {', '.join(sorted(REQUIRED_KINDS))}",
        ))

    # Check 2: Replica count based on environment
    replicas = get_deployment_replicas(documents)
    if "prod" in target_name:
        expected_replicas = 2
        if replicas == expected_replicas:
            results.append(("Prod replicas", True, f"replicas={replicas}"))
        else:
            results.append((
                "Prod replicas",
                False,
                f"Expected replicas=2, got replicas={replicas}",
            ))
    elif "dev" in target_name:
        expected_replicas = 1
        if replicas == expected_replicas:
            results.append(("Dev replicas", True, f"replicas={replicas}"))
        else:
            results.append((
                "Dev replicas",
                False,
                f"Expected replicas=1, got replicas={replicas}",
            ))

    # Check 3: StorageClass based on provider
    storageclass_names = get_storageclass_names(documents)
    if "aws" in target_name:
        expected_sc = "ebs-gp3"
        if expected_sc in storageclass_names:
            results.append(("AWS StorageClass", True, f"Found StorageClass '{expected_sc}'"))
        else:
            results.append((
                "AWS StorageClass",
                False,
                f"Expected StorageClass '{expected_sc}', found: {storageclass_names or 'none'}",
            ))
    elif "azure" in target_name:
        expected_sc = "managed-premium"
        if expected_sc in storageclass_names:
            results.append(("Azure StorageClass", True, f"Found StorageClass '{expected_sc}'"))
        else:
            results.append((
                "Azure StorageClass",
                False,
                f"Expected StorageClass '{expected_sc}', found: {storageclass_names or 'none'}",
            ))

    return results


def main():
    print("=" * 60)
    print("Kustomize Build Validation")
    print("=" * 60)

    # Find kustomize command
    kustomize_cmd = find_kustomize_command()
    if kustomize_cmd is None:
        print("\nERROR: Neither 'kustomize' nor 'kubectl' found in PATH.")
        print("Install kustomize or kubectl to run this validation.")
        sys.exit(1)

    print(f"\nUsing command: {' '.join(kustomize_cmd)}")

    # Find all target directories
    if not K8S_TARGETS_DIR.is_dir():
        print(f"\nERROR: Targets directory not found: {K8S_TARGETS_DIR}")
        sys.exit(1)

    target_dirs = sorted([
        d for d in K8S_TARGETS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    if not target_dirs:
        print(f"\nERROR: No target directories found in {K8S_TARGETS_DIR}")
        sys.exit(1)

    print(f"Found {len(target_dirs)} target(s): {', '.join(d.name for d in target_dirs)}\n")

    all_passed = True
    total_checks = 0
    passed_checks = 0

    for target_dir in target_dirs:
        target_name = target_dir.name
        print(f"\n{'─' * 60}")
        print(f"Target: {target_name}")
        print(f"{'─' * 60}")

        # Run kustomize build
        documents, error = run_kustomize_build(target_dir, kustomize_cmd)

        if error is not None:
            print(f"  ✗ FAIL: kustomize build failed")
            print(f"    Error: {error.strip()}")
            all_passed = False
            total_checks += 1
            continue

        if not documents:
            print(f"  ✗ FAIL: kustomize build produced no output")
            all_passed = False
            total_checks += 1
            continue

        print(f"  Build successful ({len(documents)} resources)")

        # Validate the output
        results = validate_target(target_name, documents)

        for check_name, passed, message in results:
            total_checks += 1
            if passed:
                passed_checks += 1
                print(f"  ✓ PASS: {check_name} — {message}")
            else:
                all_passed = False
                print(f"  ✗ FAIL: {check_name} — {message}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Summary: {passed_checks}/{total_checks} checks passed")
    print(f"{'=' * 60}")

    if all_passed:
        print("\n✓ All validations PASSED")
        sys.exit(0)
    else:
        print("\n✗ Some validations FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
