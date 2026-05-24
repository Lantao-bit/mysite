---
inclusion: always
---

# Project Overview

This is a personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5.
Live at: https://orchidflow.io

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

## Infrastructure & Deployment
- **Container:** Docker (Gunicorn, linux/amd64)
- **Orchestration:** Azure Kubernetes Service (AKS), 1-node cluster
- **IaC:** Terraform (resource group, VNet, subnet, AKS cluster)
- **CI/CD:** Azure Pipelines (Test → Terraform → Infra Setup → Build → Deploy)
- **Ingress:** NGINX Ingress Controller (Helm)
- **TLS:** cert-manager + Let's Encrypt (auto-provisioned)
- **DNS:** Cloudflare (auto-updated by pipeline on each deploy)
- **Domain:** orchidflow.io
- **Container Registry:** Docker Hub (ltyang/portfolio)

## Project Structure
- `portfolio/app.py` — Flask app factory, config, Flask-Login + Migrate + ProxyFix setup
- `portfolio/models.py` — SQLAlchemy models: User, Project, Comment
- `portfolio/db.py` — Data access functions (wraps SQLAlchemy queries, returns dicts)
- `portfolio/auth.py` — Registration and login logic, Flask-Login User class
- `portfolio/routes.py` — All route handlers registered via `register_routes(app)`
- `portfolio/forms.py` — WTForms: RegistrationForm, LoginForm, CommentForm, ProjectForm
- `portfolio/templates/` — Jinja2 templates extending `base.html`
- `portfolio/static/` — CSS and images
- `tests/` — pytest + Hypothesis test suite
- `k8s/` — Kubernetes manifests + ingress setup
- `k8s/ingress/` — NGINX ingress, cert-manager issuer, setup script
- `terraform/` — Infrastructure as Code (AKS, VNet, subnet)
- `azure-pipelines.yml` — Full CI/CD pipeline

## Key Patterns
- `db.py` functions return `dict` (not ORM objects) to keep routes/auth decoupled from SQLAlchemy
- `create_user()` raises `sqlite3.IntegrityError` on duplicates for backward compatibility
- App factory pattern: `create_app(config=None)`
- Single-page layout with anchor-based scrolling (#professional, #portfolio, #comments)
- ProxyFix middleware for correct HTTPS URL generation behind ingress proxy
- Custom validator `url_or_relative_path` allows both absolute URLs and `/static/` paths for images

## Pipeline Variables (Azure DevOps)
- ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_SUBSCRIPTION_ID, ARM_TENANT_ID (Azure SP)
- DOCKERHUB_USERNAME, DOCKERHUB_TOKEN (Docker Hub)
- CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID (Cloudflare DNS)
