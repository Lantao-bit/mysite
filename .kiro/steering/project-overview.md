---
inclusion: always
---

# Project Overview

This is a personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5.
Live at: https://orchidflow.io (Azure) | https://aws.orchidflow.io (AWS)

## Current Priority

**Multi-cloud deployment structure takes precedence over stability of the current deployment.**
When restructuring for multi-target deployment, freely move, rename, or refactor existing files and directories. The target architecture (described below) is the goal — do not preserve legacy structure at the expense of the scalable design.

## Tech Stack
- Python 3.14 / Flask 3.x
- SQLAlchemy via Flask-SQLAlchemy (models in `portfolio/models.py`)
- Flask-Migrate / Alembic for database migrations
- SQLite for persistence
- Flask-Login for authentication
- Flask-WTF + WTForms for forms and CSRF
- Werkzeug for password hashing and ProxyFix middleware
- Bootstrap 5 (CDN) for frontend
- Jinja2 templates

## Infrastructure & Deployment (Multi-Cloud Target Architecture)
- **Container:** Docker (Gunicorn, linux/amd64)
- **Orchestration:** Kubernetes (AKS on Azure, EKS on AWS) — all targets are equal peers
- **IaC:** Terraform per target under `infra/{target}/` (independent state backends)
- **CI/CD:** Configuration-driven pipeline that reads `deploy-targets.yml` and fans out to per-target stages in parallel
- **Ingress:** NGINX Ingress Controller (Helm) per cluster
- **TLS:** cert-manager + Let's Encrypt (auto-provisioned per cluster)
- **DNS:** Cloudflare (auto-updated per target: orchidflow.io → Azure, aws.orchidflow.io → AWS)
- **Domain:** orchidflow.io
- **Container Registries:** Docker Hub (ltyang/portfolio) + ECR (AWS)
- **Target Config:** `deploy-targets.yml` at project root defines all targets

## Project Structure (Target Layout)
- `portfolio/` — Flask application code (unchanged)
- `portfolio/app.py` — Flask app factory, config, Flask-Login + Migrate + ProxyFix setup
- `portfolio/models.py` — SQLAlchemy models: User, Project, Comment
- `portfolio/db.py` — Data access functions (wraps SQLAlchemy queries, returns dicts)
- `portfolio/auth.py` — Registration and login logic, Flask-Login User class
- `portfolio/routes.py` — All route handlers registered via `register_routes(app)`
- `portfolio/forms.py` — WTForms: RegistrationForm, LoginForm, CommentForm, ProjectForm
- `portfolio/templates/` — Jinja2 templates extending `base.html`
- `portfolio/static/` — CSS and images
- `tests/` — pytest + Hypothesis test suite
- `infra/modules/aws/` — Shared AWS Terraform module (VPC, EKS, ECR logic)
- `infra/modules/azure/` — Shared Azure Terraform module (VNet, AKS logic)
- `infra/targets/dev-aws-us-east-1/` — Thin root module (dev environment)
- `infra/targets/prod-aws-us-east-1/` — Thin root module (prod environment)
- `infra/targets/prod-azure-australiaeast/` — Thin root module (prod environment)
- `k8s/base/` — Cloud-agnostic shared Kubernetes manifests
- `k8s/providers/aws/` — AWS-specific patches (EBS StorageClass, NLB annotations)
- `k8s/providers/azure/` — Azure-specific patches (managed disk, Azure LB)
- `k8s/environments/dev/` — Dev patches (1 replica, debug logging, relaxed resources)
- `k8s/environments/qa/` — QA patches (production-like config, limited access)
- `k8s/environments/prod/` — Prod patches (multi-replica, strict resources)
- `k8s/targets/{target-name}/` — Optional target-specific overrides (usually minimal)
- `pipelines/deploy.yml` — Main deploy pipeline (reads deploy-targets.yml, fans out)
- `pipelines/teardown.yml` — Teardown pipeline
- `deploy-targets.yml` — Configuration file listing all deployment targets

## Key Patterns
- `db.py` functions return `dict` (not ORM objects) to keep routes/auth decoupled from SQLAlchemy
- `create_user()` raises `sqlite3.IntegrityError` on duplicates for backward compatibility
- App factory pattern: `create_app(config=None)`
- Single-page layout with anchor-based scrolling (#professional, #portfolio, #comments)
- ProxyFix middleware for correct HTTPS URL generation behind ingress proxy
- Custom validator `url_or_relative_path` allows both absolute URLs and `/static/` paths for images
- All deployment targets are equal peers — no primary/secondary distinction
- Deployments run in parallel and independently — one failure doesn't block others
- Three-level hierarchy: base → provider → environment → target (avoids duplication)
- Adding a new region for existing provider = thin `infra/targets/{name}/` + `deploy-targets.yml` entry
- Adding a new cloud provider = `infra/modules/{provider}/` + `k8s/providers/{provider}/` + target entry
- K8s manifests composed via 4-layer: base → provider → environment → target (Kustomize)
- Target naming convention: `{environment}-{provider}-{region}` (e.g., dev-aws-us-east-1)
- Environment triggers: dev→push to main, qa→release branch, prod→release tag/manual approval

## Pipeline Variables
- ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_SUBSCRIPTION_ID, ARM_TENANT_ID (Azure SP)
- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (AWS)
- DOCKERHUB_USERNAME, DOCKERHUB_TOKEN (Docker Hub)
- CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID (Cloudflare DNS)
