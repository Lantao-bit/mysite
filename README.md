# Personal Portfolio Site

A single-page personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5. Showcases professional information, project portfolio, and a visitor comment system with user authentication.

**Live:** https://orchidflow.io (Azure) | https://aws.orchidflow.io (AWS)

## Features

- Professional profile section with bio, skills, and contact links
- Project portfolio displayed as a Bootstrap card grid
- User registration and login with secure password hashing
- Authenticated visitors can leave comments
- Comments displayed newest-first in a sidebar layout
- SQLite database with Flask-Migrate for schema versioning
- Admin panel for portfolio entry management (CRUD + JSON import/export)
- Multi-cloud deployment (Azure AKS + AWS EKS) via unified GitHub Actions pipeline

## Tech Stack

- **Backend:** Python 3.14, Flask 3.x, SQLAlchemy, Flask-Login, Flask-WTF
- **Frontend:** Bootstrap 5 (CDN), Jinja2 templates
- **Database:** SQLite with Flask-Migrate / Alembic
- **Testing:** pytest, Hypothesis (property-based testing)
- **Infrastructure:** Terraform (AWS EKS + Azure AKS), Docker, Helm, Kustomize
- **CI/CD:** GitHub Actions (unified multi-cloud pipeline with dynamic matrix)
- **DNS/TLS:** Cloudflare DNS (auto-updated per target), Let's Encrypt via cert-manager
- **Container Registries:** Docker Hub + AWS ECR

## Running the App

There are four ways to run the application, from simplest to most production-like:

---

### Option 1: Local Python (Development)

Best for active development with hot-reload and debug mode.

**Prerequisites:** Python 3.12+

```bash
# Clone the repo
git clone <your-repo-url>
cd mysite

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r portfolio/requirements.txt

# Run the development server
flask --app portfolio.app run --debug
```

Open http://127.0.0.1:5000 in your browser.

The database file is created automatically on first run. To set a custom location:

```bash
export DATABASE_PATH=/path/to/portfolio.db
```

---

### Option 2: Docker Compose

Best for running the app in a container locally without managing Kubernetes.

**Prerequisites:** Docker Desktop running

```bash
# Build and start in the background
docker compose up -d

# View logs
docker compose logs -f

# Stop and remove (add -v to also remove the database volume)
docker compose down
```

App is available at http://localhost:8080.

The SQLite database is persisted to `./data/` on the host via a volume mount, so data survives container restarts.

To rebuild after code changes:

```bash
docker compose up -d --build
```

---

### Option 3: Docker (Manual Build & Run)

Same as above but without Compose — useful if you want more control over the container.

```bash
# Build the image
docker build -t portfolio .

# Run the container
docker run -d \
  --name portfolio \
  -p 8080:5000 \
  -v ./data:/app/data \
  -e SECRET_KEY=your-secret-key \
  portfolio

# Stop and remove
docker stop portfolio && docker rm portfolio
```

App is available at http://localhost:8080.

---

### Option 4: Kubernetes (Local — Docker Desktop)

Best for testing the full K8s deployment locally before pushing to cloud.

**Prerequisites:** Docker Desktop with Kubernetes enabled (Settings → Kubernetes → Enable Kubernetes)

```bash
# Build the image locally
docker build -t ltyang/portfolio:latest .

# Apply manifests using Kustomize (choose a target)
kubectl apply -k k8s/targets/prod-azure-eastus/

# Wait for the pod to be ready
kubectl -n portfolio rollout status deployment/portfolio --timeout=60s
```

App is available at http://localhost via the ingress or NodePort service.

**Useful commands:**

```bash
kubectl -n portfolio get pods                    # check pod status
kubectl -n portfolio logs -f deploy/portfolio    # view logs
kubectl -n portfolio describe pod <pod-name>     # debug a pod
```

**Tear down:**

```bash
kubectl delete namespace portfolio
```

> **Important:** Make sure your kubectl context is set to `docker-desktop` before running commands. Check with `kubectl config current-context` and switch with `kubectl config use-context docker-desktop`.

---

## Production Deployment (Multi-Cloud via GitHub Actions)

The production environment is fully automated via a unified GitHub Actions workflow that deploys to multiple cloud targets in parallel.

### Architecture

```
User → Cloudflare DNS → Load Balancer → NGINX Ingress Controller → Flask App (K8s Pod)
                                                  ↓
                                          cert-manager → Let's Encrypt (auto TLS)
```

Targets:
- `orchidflow.io` → Azure AKS (eastus)
- `aws.orchidflow.io` → AWS EKS (us-east-1)

### CI/CD Pipeline (GitHub Actions)

The `.github/workflows/deploy.yml` workflow runs on push to `release/*`, `v*` tags, or manual dispatch:

```
setup (parse deploy-targets.yml → build matrix)
  → test (pytest, once)
    → build (Docker image → Docker Hub + ECR, once)
      → deploy (fan-out per target, parallel):
          - Terraform apply (provision infra)
          - Helm: ingress-nginx + cert-manager
          - Kustomize: build + apply manifests
          - Verify rollout
          - Update Cloudflare DNS
```

### Configuration-Driven Targets

All deployment targets are defined in `deploy-targets.yml`. Adding a new target:

```bash
# 1. Edit deploy-targets.yml
# 2. Regenerate Terraform + K8s files
python scripts/generate-targets.py
# 3. Commit and push
```

### Infrastructure (Terraform)

```
infra/
├── modules/
│   ├── aws/       # VPC, EKS, ECR, EBS CSI driver
│   └── azure/     # Resource Group, AKS
└── targets/       # Generated thin root modules per target
    ├── prod-azure-eastus/
    ├── prod-aws-us-east-1/
    └── dev-aws-us-east-1/
```

### DNS & TLS

- **Cloudflare** manages DNS for `orchidflow.io` (auto-updated per target by pipeline)
- **cert-manager** + Let's Encrypt provides trusted HTTPS certificates (auto-renewed)
- DNS records are set to "DNS only" (no Cloudflare proxy) for cert-manager HTTP-01 challenges

### GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM access |
| `AWS_ACCOUNT_ID` | ECR registry URL |
| `AZURE_CLIENT_ID` | Azure Service Principal |
| `AZURE_CLIENT_SECRET` | Azure Service Principal |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `DOCKERHUB_USERNAME` | Docker Hub push/pull |
| `DOCKERHUB_TOKEN` | Docker Hub auth |
| `CLOUDFLARE_API_TOKEN` | DNS management |
| `CLOUDFLARE_ZONE_ID` | DNS zone for orchidflow.io |

### Teardown

Infrastructure teardown is manual-only via `.github/workflows/teardown.yml`:

1. Go to **Actions → Teardown → Run workflow**
2. Enter the target name (e.g., `prod-aws-us-east-1`)
3. Type `destroy` to confirm
4. Optionally preserve container registry

### Cost Management

- **Stop AKS cluster** (keep resources, stop billing): `az aks stop --name portfolio-prod-azure-eastus --resource-group portfolio-rg-prod-azure-eastus`
- **Start AKS cluster**: `az aks start --name portfolio-prod-azure-eastus --resource-group portfolio-rg-prod-azure-eastus`
- **Full teardown**: Use the teardown workflow (pipeline will recreate everything on next deploy)

---

## Running Tests

**Prerequisites:** Virtual environment activated with dependencies installed (see Option 1 above).

```bash
# Run the full test suite
python3 -m pytest tests/ -v

# Run only property-based tests
python3 -m pytest tests/test_property_*.py -v

# Run a specific test file
python3 -m pytest tests/test_db_and_auth.py -v

# Run with coverage
python3 -m pytest tests/ --cov=portfolio --cov-report=term-missing
```

The test suite includes:
- Unit tests for database operations and authentication
- Property-based tests (Hypothesis) for admin auth, project CRUD, and export/import

---

## Database Migrations

```bash
export FLASK_APP=portfolio.app

# Initialize migrations (first time only)
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

For subsequent schema changes:

```bash
flask db migrate -m "describe your change"
flask db upgrade
```

---

## Project Structure

```
portfolio/                          # Flask application
├── app.py                          # App factory (ProxyFix for HTTPS)
├── models.py                       # SQLAlchemy models (User, Project, Comment)
├── db.py                           # Data access layer (returns dicts)
├── auth.py                         # Authentication logic
├── routes.py                       # Route handlers
├── forms.py                        # WTForms definitions
├── templates/                      # Jinja2 templates
├── static/                         # CSS and images
└── requirements.txt                # Python dependencies
tests/                              # pytest + Hypothesis test suite
scripts/
└── generate-targets.py             # Generate Terraform/K8s files from config
infra/
├── modules/
│   ├── aws/                        # Shared AWS module (VPC, EKS, ECR, EBS CSI)
│   └── azure/                      # Shared Azure module (RG, AKS)
└── targets/                        # Per-target root modules (generated)
k8s/
├── base/                           # Shared K8s manifests
├── providers/
│   ├── aws/                        # AWS patches (EBS StorageClass, NLB)
│   └── azure/                      # Azure patches (managed-premium, LB)
├── environments/                   # Environment patches (replicas, resources)
└── targets/                        # Per-target overlays (generated)
.github/workflows/
├── deploy.yml                      # Unified multi-cloud deploy
└── teardown.yml                    # Manual teardown
deploy-targets.yml                  # Single source of truth for all targets
docs/                               # Architecture and deployment docs
```

## Deployment (PythonAnywhere)

An alternative hosting option for demo and showcase purposes.

1. Upload the `portfolio/` directory to `~/mysite/`
2. Create a virtualenv and install dependencies
3. Configure the WSGI file to import `create_app()` from `portfolio.app`
4. Set `SECRET_KEY` and `DATABASE_PATH` environment variables
5. Map `/static` to `~/mysite/portfolio/static`
6. Reload the web app

## License

MIT
