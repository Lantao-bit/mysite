#!/bin/bash
# Setup NGINX Ingress Controller + cert-manager on AKS
# Prerequisites: az cli logged in, kubectl configured for your cluster
set -e

CLUSTER_NAME="portfolio-aks"
RESOURCE_GROUP="portfolio-rg"

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
echo "Get your external IP:"
echo "  kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
echo ""
echo "Access your app at: http://<EXTERNAL-IP>"
echo ""
echo "Next steps when you have a domain:"
echo "  1. Point your domain's A record to the external IP"
echo "  2. Edit k8s/ingress/ingress.yaml:"
echo "     - Uncomment the tls block"
echo "     - Replace 'yourdomain.com' with your actual domain"
echo "     - Add: cert-manager.io/cluster-issuer: letsencrypt-prod"
echo "     - Set ssl-redirect to 'true'"
echo "  3. Re-apply: kubectl apply -f ingress.yaml"
echo "  4. cert-manager will automatically provision a Let's Encrypt certificate"
echo ""
