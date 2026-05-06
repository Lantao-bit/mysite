#!/bin/bash
# Deploy portfolio app to local Kubernetes (Docker Desktop)
set -e

echo "==> Building Docker image..."
docker build -t portfolio:latest ..

echo "==> Applying Kubernetes manifests..."
kubectl apply -f namespace.yaml
kubectl apply -f secret.yaml
kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

echo "==> Waiting for pod to be ready..."
kubectl -n portfolio rollout status deployment/portfolio --timeout=60s

echo ""
echo "Done! App is available at http://localhost:30080"
echo ""
echo "Useful commands:"
echo "  kubectl -n portfolio get pods          # check pod status"
echo "  kubectl -n portfolio logs -f deploy/portfolio  # view logs"
echo "  kubectl -n portfolio delete namespace portfolio # tear down everything"
