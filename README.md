# Personal Portfolio Site

A single-page personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5. Showcases professional information, project portfolio, and a visitor comment system with user authentication.

**Live:** https://orchidflow.io

## Features

- Professional profile section with bio, skills, and contact links
- Project portfolio displayed as a Bootstrap card grid
- User registration and login with secure password hashing
- Authenticated visitors can leave comments
- Comments displayed newest-first in a sidebar layout
- SQLite database with Flask-Migrate for schema versioning
- Admin panel for portfolio entry management (CRUD + JSON import/export)

## Tech Stack

- **Backend:** Python 3.14, Flask 3.x, SQLAlchemy, Flask-Login, Flask-WTF
- **Frontend:** Bootstrap 5 (CDN), Jinja2 templates
- **Database:** SQLite with Flask-Migrate / Alembic
- **Testing:** pytest, Hypothesis (property-based testing)
- **Infrastructure:** Terraform, AKS, Docker, Helm
- **CI/CD:** Azure Pipelines (Test → Terraform → Infra Setup → Build → Deploy)
- **DNS/TLS:** Cloudflare DNS (auto-updated), Let's Encrypt via cert-manager
- **Container Registry:** Docker Hub

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

# Stop
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

Best for testing the full K8s deployment locally before pushing to AKS.

**Prerequisites:** Docker Desktop with Kubernetes enabled (Settings → Kubernetes → Enable Kubernetes)

**Quick deploy using the convenience script:**

```bash
cd k8s
chmod +x deploy.sh
./deploy.sh
```

**Manual step-by-step:**

```bash
# Build the image locally
docker build -t portfolio:latest .

# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Wait for the pod to be ready
kubectl -n portfolio rollout status deployment/portfolio --timeout=60s
```

App is available at http://localhost (port 80) via the LoadBalancer service.

**Useful commands:**

```bash
kubectl -n portfolio get pods              # check pod status
kubectl -n portfolio logs -f deploy/portfolio  # view logs
kubectl -n portfolio describe pod <pod-name>   # debug a pod
```

**Tear down:**

```bash
kubectl delete namespace portfolio
```

> **Important:** Make sure your kubectl context is set to `docker-desktop` before running tear-down commands. If your context is pointing to AKS (`portfolio-aks-admin`), this will delete the production deployment. Check with `kubectl config current-context` and switch with `kubectl config use-context docker-desktop`. Use 'kubectl config get-contexts' or 'kubectl config get-contexts -o name' to list all available contexts.

> **Note:** The K8s deployment.yaml uses `ltyang/portfolio:__IMAGE_TAG__` as the image reference. For local K8s, update the image field to `portfolio:latest` and set `imagePullPolicy: Never`.

---

## Production Deployment (AKS + Terraform + Cloudflare)

The production environment is fully automated via Azure Pipelines.

### Architecture

```
User → Cloudflare DNS → Azure Load Balancer → NGINX Ingress Controller → Flask App (AKS Pod)
                                                      ↓
                                              cert-manager → Let's Encrypt (auto TLS)
```

### CI/CD Pipeline Stages

The `azure-pipelines.yml` pipeline runs automatically on push to `main`:

1. **Test** — Runs pytest (unit + property-based tests)
2. **Terraform Plan** — Plans infrastructure changes
3. **Terraform Apply** — Creates/updates AKS cluster, VNet, subnet
4. **Infra Setup** — Installs NGINX Ingress Controller + cert-manager via Helm, updates Cloudflare DNS with the new ingress IP
5. **Build & Push** — Builds linux/amd64 Docker image, pushes to Docker Hub
6. **Deploy** — Applies K8s manifests to AKS

### Infrastructure (Terraform)

Managed resources in `terraform/`:
- Resource group, VNet, subnet
- AKS cluster (1 node, Standard_dc2ads_v5)

### DNS & TLS

- **Cloudflare** manages DNS for `orchidflow.io` (auto-updated by pipeline)
- **cert-manager** + Let's Encrypt provides trusted HTTPS certificates (auto-renewed)
- DNS records are set to "DNS only" (no Cloudflare proxy) for cert-manager HTTP-01 challenges

### Pipeline Variables (Azure DevOps)

| Variable | Secret | Purpose |
|----------|--------|---------|
| ARM_CLIENT_ID | No | Azure service principal |
| ARM_CLIENT_SECRET | Yes | Azure service principal |
| ARM_SUBSCRIPTION_ID | No | Azure subscription |
| ARM_TENANT_ID | No | Azure tenant |
| DOCKERHUB_USERNAME | No | Docker Hub login |
| DOCKERHUB_TOKEN | Yes | Docker Hub access token |
| CLOUDFLARE_API_TOKEN | Yes | Cloudflare DNS API |
| CLOUDFLARE_ZONE_ID | No | Cloudflare zone for orchidflow.io |

### Cost Management

- **Stop cluster** (keep resources, stop billing for compute): `az aks stop --name portfolio-aks --resource-group portfolio-rg`
- **Start cluster**: `az aks start --name portfolio-aks --resource-group portfolio-rg`
- **Full teardown**: `terraform destroy` (pipeline will recreate everything on next push)

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

# Run with short output
python3 -m pytest tests/
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
portfolio/
├── app.py              # Flask app factory (with ProxyFix for HTTPS)
├── models.py           # SQLAlchemy models (User, Project, Comment)
├── db.py               # Data access layer (returns dicts)
├── auth.py             # Authentication logic
├── routes.py           # Route handlers
├── forms.py            # WTForms definitions
├── templates/          # Jinja2 templates
├── static/             # CSS and images
└── requirements.txt    # Python dependencies
tests/
├── test_db_and_auth.py           # Unit tests
├── test_admin_routes.py          # Admin route tests
├── test_property_admin_auth.py   # Property-based auth tests
├── test_property_export_import.py # Property-based export/import tests
└── test_property_project_crud.py # Property-based CRUD tests
k8s/
├── deploy.sh           # Local K8s deployment script
├── ingress/            # Ingress + cert-manager manifests
│   ├── setup-ingress.sh
│   ├── cert-manager-issuer.yaml
│   └── ingress.yaml
├── namespace.yaml
├── secret.yaml
├── pvc.yaml
├── deployment.yaml
└── service.yaml
terraform/
├── main.tf             # AKS cluster, VNet, subnet
├── variables.tf        # Configurable parameters
├── outputs.tf          # Useful output values
├── backend.tf          # Remote state configuration
└── terraform.tfvars.example
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
