# Personal Portfolio Site

A single-page personal portfolio website built with Flask, SQLAlchemy, and Bootstrap 5. Showcases professional information, project portfolio, and a visitor comment system with user authentication.

## Features

- Professional profile section with bio, skills, and contact links
- Project portfolio displayed as a Bootstrap card grid
- User registration and login with secure password hashing
- Authenticated visitors can leave comments
- Comments displayed newest-first in a sidebar layout
- SQLite database with Flask-Migrate for schema versioning

## Tech Stack

- **Backend:** Python 3.14, Flask 3.x, SQLAlchemy, Flask-Login, Flask-WTF
- **Frontend:** Bootstrap 5 (CDN), Jinja2 templates
- **Database:** SQLite with Flask-Migrate / Alembic
- **Testing:** pytest, Hypothesis

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
# Build the image locally (Docker Desktop K8s uses local images)
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

> **Note:** The K8s deployment.yaml uses `ltyang/portfolio:__IMAGE_TAG__` as the image reference. The `deploy.sh` script uses a locally-built `portfolio:latest` image. For local K8s, you may need to update the image field in `k8s/deployment.yaml` to `portfolio:latest` and set `imagePullPolicy: Never`.

---

## CI/CD (Azure Pipelines → AKS)

The `azure-pipelines.yml` pipeline runs automatically on push to `main`:

1. **Build stage** — Builds a linux/amd64 Docker image and pushes to Docker Hub (`ltyang/portfolio:<build-id>`)
2. **Deploy stage** — Applies K8s manifests to AKS with the new image tag

This is not a local run method, but it's how the app reaches production. See `azure-pipelines.yml` for full details.

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
├── app.py              # Flask app factory
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
├── namespace.yaml      # Namespace definition
├── secret.yaml         # Secret for app config
├── pvc.yaml            # Persistent volume claim for SQLite
├── deployment.yaml     # Deployment manifest
└── service.yaml        # LoadBalancer service
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
