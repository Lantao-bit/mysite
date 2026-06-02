#!/usr/bin/env python3
"""Parse deploy-targets.yml and output selected targets as a JSON matrix.

Used by the Azure DevOps pipeline to determine which targets to deploy.
Outputs the target matrix as a pipeline variable for fan-out stages.

Usage:
    python pipelines/scripts/parse-targets.py --target-list "prod-aws-us-east-1,prod-azure-australiaeast"
    python pipelines/scripts/parse-targets.py --environment prod
    python pipelines/scripts/parse-targets.py  # all enabled targets
"""

import argparse
import json
import os
import sys

import yaml


def find_config_path(override_path=None):
    """Locate deploy-targets.yml relative to script or via override."""
    if override_path:
        return override_path

    # Default: two levels up from script location (pipelines/scripts/ -> project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "..", "..", "deploy-targets.yml")


def load_config(config_path):
    """Load and parse deploy-targets.yml. Exit with error if not found or invalid."""
    resolved = os.path.realpath(config_path)

    if not os.path.isfile(resolved):
        print(f"ERROR: deploy-targets.yml not found at: {resolved}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(resolved, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse deploy-targets.yml: {e}", file=sys.stderr)
        sys.exit(1)

    if not data or "targets" not in data:
        print("ERROR: deploy-targets.yml must contain a 'targets' key", file=sys.stderr)
        sys.exit(1)

    return data["targets"]


def validate_target_list(requested_names, available_targets):
    """Validate that all requested target names exist in config.

    Returns the list of matching target dicts (regardless of enabled status).
    Exits with error if any unknown target is found.
    """
    available_names = {t["name"] for t in available_targets}
    unknown = [name for name in requested_names if name not in available_names]

    if unknown:
        print(
            f"ERROR: Unknown target(s) in target_list: {', '.join(unknown)}. "
            f"Available targets: {', '.join(sorted(available_names))}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Return targets matching the requested names (regardless of enabled status)
    requested_set = set(requested_names)
    return [t for t in available_targets if t["name"] in requested_set]


def filter_by_environment(targets, environment):
    """Select all enabled targets matching the given environment."""
    return [t for t in targets if t.get("enabled") and t.get("environment") == environment]


def select_all_enabled(targets):
    """Select all enabled targets."""
    return [t for t in targets if t.get("enabled")]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse deploy-targets.yml and output target matrix for pipeline fan-out."
    )
    parser.add_argument(
        "--target-list",
        type=str,
        default="",
        help="Comma-separated list of target names to deploy (overrides enabled status)",
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="",
        help="Filter to select all enabled targets matching this environment",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="",
        help="Path to deploy-targets.yml (default: auto-detect from script location)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Load configuration
    config_path = find_config_path(args.config if args.config else None)
    targets = load_config(config_path)

    # Select targets based on arguments
    if args.target_list:
        # Parse comma-separated list, strip whitespace
        requested_names = [name.strip() for name in args.target_list.split(",") if name.strip()]
        selected = validate_target_list(requested_names, targets)
    elif args.environment:
        selected = filter_by_environment(targets, args.environment)
    else:
        selected = select_all_enabled(targets)

    # Fail if no targets selected
    if not selected:
        if args.target_list:
            msg = f"No targets selected from target_list: {args.target_list}"
        elif args.environment:
            msg = f"No enabled targets found for environment: {args.environment}"
        else:
            msg = "No enabled targets found in deploy-targets.yml"
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

    # Output as JSON array to stdout
    output = json.dumps(selected, indent=2)
    print(output)

    # Set Azure DevOps pipeline variable for fan-out
    # Use compact JSON for the pipeline variable
    compact_output = json.dumps(selected)
    print(f"##vso[task.setvariable variable=TARGET_MATRIX;isOutput=true]{compact_output}")


if __name__ == "__main__":
    main()
