#!/bin/bash
# Setup NGINX Ingress Controller + cert-manager on AKS
# Uses the static IP from Terraform to ensure DNS stability across cluster recreations.
# Prerequisites: az cli logged in, kubectl configured, helm installed, terraform applied
set -e

CLUSTER_NAME="portfolio-aks"
RESOURCE_GROUP="portfolio-rg"

echo "==> Connecting to AKS cluster..."
az aks get-credentials --name "$CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --overwrite-existing

echo ""
echo "==> Getting static IP from Terraform..."
STATIC_IP=$(cd ../../terraform && terraform output -raw ingress_public_ip 2>/dev/null || echo "")

if [ -z "$STATIC_IP" ]; then
  echo "    WARNING: Could not get static IP from Terraform output."
  echo "    The ingress controller will get a dynamic IP from Azure."
  echo "    You can set it manually: STATIC_IP=x.x.x.x ./setup-ingress.sh"
  STATIC_IP_FLAG=""
else
  echo "    Static IP: $STATIC_IP"
  STATIC_IP_FLAG="--set controller.service.loadBalancerIP=$STATIC_IP --set controller.service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-resource-group=$RESOURCE_GROUP"
fi

echo ""
echo "==> Step 1: Install NGINX Ingress Controller via Helm..."
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

if [ -n "$STATIC_IP_FLAG" ]; then
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx \
    --create-namespace \
    --set controller.replicaCount=1 \
    --set controller.service.loadBalancerIP="$STATIC_IP" \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-resource-group"="$RESOURCE_GROUP" \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
else
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx \
    --create-namespace \
    --set controller.replicaCount=1 \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
fi

echo ""
echo "==> Waiting for ingress controller to be ready..."
kubectl -n ingress-nginx wait --for=condition=available deployment/ingress-nginx-controller --timeout=120s

echo ""
echo "==> Step 2: Install cert-manager via Helm..."
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true

echo ""
echo "==> Waiting for cert-manager to be ready..."
kubectl -n cert-manager wait --for=condition=available deployment/cert-manager --timeout=120s
kubectl -n cert-manager wait --for=condition=available deployment/cert-manager-webhook --timeout=120s

echo ""
echo "==> Step 3: Apply ClusterIssuers..."
kubectl apply -f cert-manager-issuer.yaml

echo ""
echo "==> Step 4: Apply Ingress resource..."
kubectl apply -f ingress.yaml

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""

EXTERNAL_IP=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "<pending>")
echo "Ingress External IP: $EXTERNAL_IP"
echo "Domain: https://orchidpay.io"
echo ""
echo "If this is a fresh cluster with a new static IP, update your DNS:"
echo "  Hostinger → DNS → A record @ → $EXTERNAL_IP"
echo ""
