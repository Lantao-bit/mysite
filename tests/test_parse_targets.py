"""Unit tests for pipelines/scripts/parse-targets.py."""

import json
import os
import subprocess
import sys
import tempfile

import pytest
import yaml


SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pipelines",
    "scripts",
    "parse-targets.py",
)


def write_config(targets, tmpdir):
    """Write a deploy-targets.yml config to a temp file and return its path."""
    config_path = os.path.join(tmpdir, "deploy-targets.yml")
    with open(config_path, "w") as f:
        yaml.dump({"targets": targets}, f)
    return config_path


def run_script(args, config_path=None):
    """Run parse-targets.py with given args and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT_PATH]
    if config_path:
        cmd.extend(["--config", config_path])
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


SAMPLE_TARGETS = [
    {
        "name": "prod-azure-australiaeast",
        "enabled": True,
        "provider": "azure",
        "region": "australiaeast",
        "environment": "prod",
        "trigger": {"branches": ["release/*"], "tags": ["v*"]},
        "dns": {"subdomain": "", "record_type": "A"},
        "registry": "dockerhub",
        "cluster_name": "portfolio-aks",
        "resource_group": "portfolio-rg",
    },
    {
        "name": "prod-aws-us-east-1",
        "enabled": True,
        "provider": "aws",
        "region": "us-east-1",
        "environment": "prod",
        "trigger": {"branches": ["release/*"], "tags": ["v*"]},
        "dns": {"subdomain": "aws", "record_type": "A"},
        "registry": "ecr",
        "cluster_name": "portfolio-eks",
        "ecr_repo": "portfolio",
    },
    {
        "name": "dev-aws-us-east-1",
        "enabled": False,
        "provider": "aws",
        "region": "us-east-1",
        "environment": "dev",
        "trigger": {"branches": ["main"]},
        "dns": {"subdomain": "dev-aws", "record_type": "A"},
        "registry": "ecr",
        "cluster_name": "portfolio-eks-dev",
        "ecr_repo": "portfolio",
    },
]


@pytest.fixture
def config_dir(tmp_path):
    """Create a temp directory with a sample deploy-targets.yml."""
    config_path = write_config(SAMPLE_TARGETS, str(tmp_path))
    return config_path


class TestNoArguments:
    """When no arguments provided, select all enabled targets."""

    def test_returns_enabled_targets(self, config_dir):
        rc, stdout, stderr = run_script([], config_path=config_dir)
        assert rc == 0
        # Parse the JSON output (before the ##vso line)
        lines = stdout.strip().split("\n")
        # Find where the JSON ends and the vso line begins
        json_lines = [l for l in lines if not l.startswith("##vso")]
        result = json.loads("\n".join(json_lines))
        names = [t["name"] for t in result]
        assert "prod-azure-australiaeast" in names
        assert "prod-aws-us-east-1" in names
        assert "dev-aws-us-east-1" not in names

    def test_excludes_disabled_targets(self, config_dir):
        rc, stdout, stderr = run_script([], config_path=config_dir)
        assert rc == 0
        json_lines = [l for l in stdout.strip().split("\n") if not l.startswith("##vso")]
        result = json.loads("\n".join(json_lines))
        for t in result:
            assert t["enabled"] is True


class TestTargetList:
    """When --target-list is provided, validate and select those targets."""

    def test_selects_specified_targets(self, config_dir):
        rc, stdout, stderr = run_script(
            ["--target-list", "prod-aws-us-east-1"], config_path=config_dir
        )
        assert rc == 0
        json_lines = [l for l in stdout.strip().split("\n") if not l.startswith("##vso")]
        result = json.loads("\n".join(json_lines))
        assert len(result) == 1
        assert result[0]["name"] == "prod-aws-us-east-1"

    def test_includes_disabled_targets(self, config_dir):
        """target_list overrides enabled status per requirement 5.4."""
        rc, stdout, stderr = run_script(
            ["--target-list", "dev-aws-us-east-1"], config_path=config_dir
        )
        assert rc == 0
        json_lines = [l for l in stdout.strip().split("\n") if not l.startswith("##vso")]
        result = json.loads("\n".join(json_lines))
        assert len(result) == 1
        assert result[0]["name"] == "dev-aws-us-east-1"
        assert result[0]["enabled"] is False

    def test_unknown_target_fails(self, config_dir):
        rc, stdout, stderr = run_script(
            ["--target-list", "nonexistent-target"], config_path=config_dir
        )
        assert rc == 1
        assert "nonexistent-target" in stderr
        assert "Unknown target" in stderr

    def test_multiple_targets(self, config_dir):
        rc, stdout, stderr = run_script(
            ["--target-list", "prod-aws-us-east-1,prod-azure-australiaeast"],
            config_path=config_dir,
        )
        assert rc == 0
        json_lines = [l for l in stdout.strip().split("\n") if not l.startswith("##vso")]
        result = json.loads("\n".join(json_lines))
        names = [t["name"] for t in result]
        assert "prod-aws-us-east-1" in names
        assert "prod-azure-australiaeast" in names


class TestEnvironmentFilter:
    """When --environment is provided, select enabled targets matching that environment."""

    def test_filters_by_environment(self, config_dir):
        rc, stdout, stderr = run_script(
            ["--environment", "prod"], config_path=config_dir
        )
        assert rc == 0
        json_lines = [l for l in stdout.strip().split("\n") if not l.startswith("##vso")]
        result = json.loads("\n".join(json_lines))
        for t in result:
            assert t["environment"] == "prod"
            assert t["enabled"] is True

    def test_no_enabled_targets_for_environment_fails(self, config_dir):
        """dev-aws-us-east-1 is disabled, so environment=dev should fail."""
        rc, stdout, stderr = run_script(
            ["--environment", "dev"], config_path=config_dir
        )
        assert rc == 1
        assert "No enabled targets found for environment: dev" in stderr

    def test_nonexistent_environment_fails(self, config_dir):
        rc, stdout, stderr = run_script(
            ["--environment", "staging"], config_path=config_dir
        )
        assert rc == 1
        assert "No enabled targets found for environment: staging" in stderr


class TestErrorHandling:
    """Test error conditions."""

    def test_missing_config_file(self):
        rc, stdout, stderr = run_script(
            ["--config", "/nonexistent/deploy-targets.yml"], config_path=None
        )
        assert rc == 1
        assert "not found" in stderr

    def test_invalid_yaml(self, tmp_path):
        config_path = os.path.join(str(tmp_path), "deploy-targets.yml")
        with open(config_path, "w") as f:
            f.write("{{invalid yaml content")
        rc, stdout, stderr = run_script([], config_path=config_path)
        assert rc == 1
        assert "Failed to parse" in stderr

    def test_missing_targets_key(self, tmp_path):
        config_path = os.path.join(str(tmp_path), "deploy-targets.yml")
        with open(config_path, "w") as f:
            yaml.dump({"other_key": []}, f)
        rc, stdout, stderr = run_script([], config_path=config_path)
        assert rc == 1
        assert "must contain a 'targets' key" in stderr

    def test_no_enabled_targets_fails(self, tmp_path):
        """All targets disabled and no target_list → should fail."""
        targets = [{"name": "t1", "enabled": False, "provider": "aws",
                    "region": "us-east-1", "environment": "dev",
                    "trigger": {"branches": ["main"]}}]
        config_path = write_config(targets, str(tmp_path))
        rc, stdout, stderr = run_script([], config_path=config_path)
        assert rc == 1
        assert "No enabled targets" in stderr


class TestPipelineVariable:
    """Test that the Azure DevOps pipeline variable is set correctly."""

    def test_vso_variable_output(self, config_dir):
        rc, stdout, stderr = run_script(
            ["--target-list", "prod-aws-us-east-1"], config_path=config_dir
        )
        assert rc == 0
        vso_lines = [l for l in stdout.strip().split("\n") if l.startswith("##vso")]
        assert len(vso_lines) == 1
        assert "TARGET_MATRIX" in vso_lines[0]
        assert "isOutput=true" in vso_lines[0]
        # Extract the JSON value from the vso line
        json_str = vso_lines[0].split("]", 1)[1]
        targets = json.loads(json_str)
        assert isinstance(targets, list)
        assert targets[0]["name"] == "prod-aws-us-east-1"
