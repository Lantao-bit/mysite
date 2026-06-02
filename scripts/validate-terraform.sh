#!/usr/bin/env bash
#
# Terraform Validation Script
# Runs terraform validate on each module and target directory,
# and verifies expected outputs are declared in each module.
#
# Requirements: 1.7, 8.1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
FAILURES=()

print_pass() {
  echo -e "  ${GREEN}PASS${NC}: $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

print_fail() {
  echo -e "  ${RED}FAIL${NC}: $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  FAILURES+=("$1")
}

print_header() {
  echo ""
  echo -e "${YELLOW}=== $1 ===${NC}"
}

# --- Terraform validate ---

validate_terraform_dir() {
  local dir="$1"
  local label="$2"

  if [ ! -d "$dir" ]; then
    print_fail "$label — directory not found: $dir"
    return
  fi

  # Initialize without backend
  if terraform -chdir="$dir" init -backend=false -input=false -no-color > /dev/null 2>&1; then
    # Run validate
    if terraform -chdir="$dir" validate -no-color > /dev/null 2>&1; then
      print_pass "$label — terraform validate"
    else
      print_fail "$label — terraform validate failed"
    fi
  else
    print_fail "$label — terraform init -backend=false failed"
  fi
}

# --- Output verification ---

verify_outputs() {
  local outputs_file="$1"
  local label="$2"
  shift 2
  local expected_outputs=("$@")

  if [ ! -f "$outputs_file" ]; then
    print_fail "$label — outputs.tf not found"
    return
  fi

  for output_name in "${expected_outputs[@]}"; do
    if grep -q "output \"${output_name}\"" "$outputs_file"; then
      print_pass "$label — output '${output_name}' declared"
    else
      print_fail "$label — output '${output_name}' NOT declared in outputs.tf"
    fi
  done
}

# ============================================================
# Main
# ============================================================

echo "Terraform Validation Script"
echo "Project root: $PROJECT_ROOT"

# --- Module directories ---
MODULES=(
  "infra/modules/aws"
  "infra/modules/azure"
)

# --- Target directories ---
TARGETS=(
  "infra/targets/prod-azure-eastus"
  "infra/targets/prod-aws-us-east-1"
  "infra/targets/dev-aws-us-east-1"
)

# --- Expected outputs per module ---
AWS_OUTPUTS=(
  "cluster_endpoint"
  "cluster_ca_data"
  "cluster_name"
  "ecr_repository_url"
  "node_role_arn"
)

AZURE_OUTPUTS=(
  "cluster_endpoint"
  "cluster_ca_data"
  "cluster_name"
  "resource_group_name"
)

# ============================================================
# Step 1: Validate modules
# ============================================================

print_header "Validating Terraform Modules"

for module in "${MODULES[@]}"; do
  validate_terraform_dir "$PROJECT_ROOT/$module" "$module"
done

# ============================================================
# Step 2: Validate targets
# ============================================================

print_header "Validating Terraform Targets"

for target in "${TARGETS[@]}"; do
  validate_terraform_dir "$PROJECT_ROOT/$target" "$target"
done

# ============================================================
# Step 3: Verify module outputs
# ============================================================

print_header "Verifying Module Outputs"

echo ""
echo "  Checking infra/modules/aws/outputs.tf..."
verify_outputs \
  "$PROJECT_ROOT/infra/modules/aws/outputs.tf" \
  "infra/modules/aws" \
  "${AWS_OUTPUTS[@]}"

echo ""
echo "  Checking infra/modules/azure/outputs.tf..."
verify_outputs \
  "$PROJECT_ROOT/infra/modules/azure/outputs.tf" \
  "infra/modules/azure" \
  "${AZURE_OUTPUTS[@]}"

# ============================================================
# Summary
# ============================================================

print_header "Summary"

echo ""
echo -e "  Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "  Failed: ${RED}${FAIL_COUNT}${NC}"

if [ ${FAIL_COUNT} -gt 0 ]; then
  echo ""
  echo -e "${RED}Failures:${NC}"
  for failure in "${FAILURES[@]}"; do
    echo -e "  - $failure"
  done
  echo ""
  exit 1
fi

echo ""
echo -e "${GREEN}All validations passed!${NC}"
exit 0
