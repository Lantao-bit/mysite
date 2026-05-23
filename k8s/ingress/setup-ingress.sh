#!/bin/bash
# Setup NGINX Ingress Controller + cert-manager on AKS
# Uses dynamic IP with Cloudflare DNS auto-update.
# Prerequisites: az cli logged in, kubectl configured, helm installed
set -e

CLUSTER_NAME="portfolio-aks"
RESOURCE_GROUP="portfolio-rg"
DOMAIN="orchidflow.io"

echo "==> Connecting to AKS cluster..."
az aks get-credentials --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --overwrite-existing

echo ""
echo "==> Step 1: Install NGINX Ingress Controller via Helm..."
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=1 \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz

echo ""
echo "==> Waiting for ingress controller to get an external IP..."
echo "    (this may take 1-2 minutes)"
for i in $(seq 1 30); do
  IP=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
  if [ -n "$IP" ] && [ "$IP" != "" ]; then
    echo "    External IP: $IP"
    break
  fi
  echo "    Attempt $i/30 - waiting..."
  sleep 10
done

if [ -z "$IP" ]; then
  echo "ERROR: Timed out waiting for external IP"
  exit 1
fi

echo ""
echo "==> Step 2: Install cert-manager via Helm..."
helm repo add jetstack https://charts.jetstack.io
helm repo update

kubectl delete validatingwebhookconfiguration cert-manager-webhook --ignore-not-found
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true \
  --set global.leaderElection.namespace=cert-manager

echo ""
echo "==> Waiting for cert-manager to be ready..."
kubectl -n cert-manager wait --for=condition=available deployment/cert-manager --timeout=120s
kubectl -n cert-manager wait --for=condition=available deployment/cert-manager-webhook --timeout=120s

echo ""
echo "==> Step 3: Apply ClusterIssuers..."
kubectl apply -f cert-manager-issuer.yaml

echo ""
echo "==> Step 4: Apply namespace and Ingress resource..."
kubectl apply -f ../namespace.yaml
kubectl apply -f ingress.yaml

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Ingress External IP: $IP"
echo "Domain: https://$DOMAIN"
echo ""
echo "Next: Update Cloudflare DNS A record for $DOMAIN -> $IP"
echo "  (The pipeline does this automatically via CLOUDFLARE_API_TOKEN)"
echo ""
