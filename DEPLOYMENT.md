# Scopebot Helm Deployment Guide

Complete guide to deploy Scopebot (frontend, backend, postgres, qdrant) to Minikube using Helm umbrella chart.

## Prerequisites

- Docker
- Minikube
- kubectl
- Helm 3.x

---

## Step-by-Step Deployment

### 1. Start Minikube

```bash
minikube start --cpus=4 --memory=8192
```

### 2. Configure Environment Variables

Before deploying, you MUST configure the values in `helm/scopebot/values.yaml`. Update these required fields:

```yaml
backend:
  secrets:
    GEMINI_API_KEY: "your-gemini-api-key"
    JINA_API_KEY: "your-jina-api-key"
    POSTGRES_PASSWORD: "your-secure-password"
    DATABASE_URL: "postgresql://scopebot:your-secure-password@postgres:5432/scopebot"
    SECRET_KEY: "your-secret-key-generate-with-openssl-rand-hex-32"
```

**Generate secure secrets:**
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate POSTGRES_PASSWORD
openssl rand -base64 32
```

### 3. Build Docker Images for Minikube

**Option A: Build directly in Minikube's Docker daemon (recommended)**

```bash
# Point your shell to Minikube's Docker daemon
eval $(minikube docker-env)

# Build frontend image
docker build -t scopebot-frontend:latest ./frontend

# Build backend image
docker build -t scopebot-backend:latest ./backend

# Verify images are in Minikube
docker images | grep scopebot
```

**Option B: Build locally and load into Minikube**

```bash
# Build images locally
docker build -t scopebot-frontend:latest ./frontend
docker build -t scopebot-backend:latest ./backend

# Load images into Minikube
minikube image load scopebot-frontend:latest
minikube image load scopebot-backend:latest

# Verify
minikube image ls | grep scopebot
```

### 4. Create Namespace

```bash
kubectl create namespace scopebot
```

### 5. Update Helm Dependencies

```bash
cd helm/scopebot
helm dependency update
cd ../..
```

### 6. Install/Upgrade Helm Chart

**First-time installation:**

```bash
helm install scopebot ./helm/scopebot \
  --namespace scopebot \
  --create-namespace
```

**Upgrade existing deployment:**

```bash
helm upgrade scopebot ./helm/scopebot \
  --namespace scopebot
```

**Install/Upgrade (combined command):**

```bash
helm upgrade --install scopebot ./helm/scopebot \
  --namespace scopebot \
  --create-namespace
```

### 7. Verify Deployment

**Check all pods are running:**

```bash
kubectl get pods -n scopebot
```

Expected output (all pods should be Running):
```
NAME                                 READY   STATUS    RESTARTS   AGE
scopebot-backend-xxxxx               1/1     Running   0          2m
scopebot-frontend-xxxxx              1/1     Running   0          2m
scopebot-postgres-xxxxx              1/1     Running   0          2m
scopebot-qdrant-xxxxx                1/1     Running   0          2m
```

**Check services:**

```bash
kubectl get services -n scopebot
```

Expected output:
```
NAME                 TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
scopebot-backend     ClusterIP   10.x.x.x        <none>        8000/TCP         2m
scopebot-frontend    ClusterIP   10.x.x.x        <none>        80/TCP           2m
scopebot-postgres    ClusterIP   10.x.x.x        <none>        5432/TCP         2m
scopebot-qdrant      ClusterIP   10.x.x.x        <none>        6333/TCP,6334/TCP 2m
```

### 8. Troubleshooting Failed Pods

**Describe pod to see events:**

```bash
kubectl describe pod <pod-name> -n scopebot
```

**View pod logs:**

```bash
kubectl logs <pod-name> -n scopebot
```

**View logs with follow:**

```bash
kubectl logs -f <pod-name> -n scopebot
```

**Get all events in namespace:**

```bash
kubectl get events -n scopebot --sort-by='.lastTimestamp'
```

### 9. Access Services via Port-Forward

**Access Frontend (port 3000):**

```bash
kubectl port-forward -n scopebot service/scopebot-frontend 3000:80
```

Visit: http://localhost:3000

**Access Backend API (port 8000):**

```bash
kubectl port-forward -n scopebot service/scopebot-backend 8000:8000
```

Visit: http://localhost:8000/docs (FastAPI Swagger UI)

**Access Qdrant Dashboard (port 6333):**

```bash
kubectl port-forward -n scopebot service/scopebot-qdrant 6333:6333
```

Visit: http://localhost:6333/dashboard

**Access Postgres (port 5432):**

```bash
kubectl port-forward -n scopebot service/scopebot-postgres 5432:5432
```

Connect with: `psql -h localhost -p 5432 -U scopebot -d scopebot`

### 10. Health Checks

**Backend API health check:**

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

**Qdrant health check:**

```bash
curl http://localhost:6333/health
```

Expected response:
```json
{"status": "ok"}
```

**Backend API docs:**

```bash
curl http://localhost:8000/api/docs
```

**Check Qdrant collections:**

```bash
curl http://localhost:6333/collections
```

---

## Alternative: Using Kubernetes Secrets from .env File

If you prefer to keep secrets in a `.env` file instead of `values.yaml`:

### 1. Create `.env` file

```bash
cat > .env << 'EOF'
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-pro
JINA_API_KEY=your-jina-api-key
JINA_MODEL=jina-embeddings-v2-base-en
POSTGRES_DB=scopebot
POSTGRES_USER=scopebot
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://scopebot:your-secure-password@postgres:5432/scopebot
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
EOF
```

### 2. Create Kubernetes secret from .env

```bash
kubectl create secret generic backend-env-secrets \
  --from-env-file=.env \
  --namespace=scopebot
```

### 3. Verify secret was created

```bash
kubectl get secret backend-env-secrets -n scopebot
kubectl describe secret backend-env-secrets -n scopebot
```

### 4. Modify backend deployment to use this secret

Edit `helm/scopebot/charts/backend/templates/deployment.yaml` and add:

```yaml
        envFrom:
        - secretRef:
            name: backend-env-secrets
```

This will load all environment variables from the secret instead of using Helm values.

---

## Service Connectivity

The services are configured to communicate using Kubernetes service DNS names:

- **Frontend → Backend**: `http://backend:8000` (via nginx proxy at `/api`)
- **Backend → Postgres**: `postgresql://scopebot:PASSWORD@postgres:5432/scopebot`
- **Backend → Qdrant**: `http://qdrant:6333`

Service names resolve automatically within the namespace.

---

## Production Considerations

### 1. Enable Persistent Volumes

For production, enable persistence in `values.yaml`:

```yaml
postgres:
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "standard"

qdrant:
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "standard"
```

### 2. Create PersistentVolumeClaims

Create PVC templates in the chart templates:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### 3. Update Volume Mounts

Change from `emptyDir: {}` to `persistentVolumeClaim: { claimName: postgres-pvc }` in deployment.yaml

---

## Cleanup

**Delete Helm release:**

```bash
helm uninstall scopebot -n scopebot
```

**Delete namespace:**

```bash
kubectl delete namespace scopebot
```

**Delete Minikube cluster:**

```bash
minikube delete
```

---

## Common Issues

### Issue: ImagePullBackOff

**Solution:** Ensure images are built in Minikube's Docker daemon or loaded via `minikube image load`

```bash
eval $(minikube docker-env)
docker images | grep scopebot
```

### Issue: CrashLoopBackOff

**Solution:** Check logs for application errors

```bash
kubectl logs <pod-name> -n scopebot
```

### Issue: Service not accessible

**Solution:** Verify port-forward is active and service is running

```bash
kubectl get services -n scopebot
kubectl get pods -n scopebot
```

### Issue: Backend can't connect to Postgres/Qdrant

**Solution:** Verify service names match in configuration and all pods are running

```bash
kubectl get services -n scopebot
kubectl exec -it <backend-pod> -n scopebot -- ping postgres
```

---

## Quick Reference Commands

```bash
# View all resources
kubectl get all -n scopebot

# Watch pod status
kubectl get pods -n scopebot -w

# Execute command in pod
kubectl exec -it <pod-name> -n scopebot -- /bin/bash

# Copy files to/from pod
kubectl cp <pod-name>:/path/to/file ./local-file -n scopebot

# View Helm release
helm list -n scopebot

# View Helm values
helm get values scopebot -n scopebot

# Rollback Helm release
helm rollback scopebot -n scopebot

# Update specific values
helm upgrade scopebot ./helm/scopebot \
  --namespace scopebot \
  --set backend.secrets.GEMINI_API_KEY="new-key"
```

---

## Development Workflow

1. Make code changes
2. Rebuild Docker images (with Minikube Docker daemon active)
3. Delete pods to force recreation with new images:
   ```bash
   kubectl delete pod -l app.kubernetes.io/name=backend -n scopebot
   kubectl delete pod -l app.kubernetes.io/name=frontend -n scopebot
   ```
4. Or do a Helm upgrade:
   ```bash
   helm upgrade scopebot ./helm/scopebot -n scopebot
   ```

---

## Summary of Files

```
.
├── frontend/
│   ├── Dockerfile                      # Multi-stage build with nginx
│   └── nginx/
│       └── default.conf                # Nginx config with /api proxy to backend
├── backend/
│   └── Dockerfile                      # FastAPI with uvicorn
├── helm/
│   └── scopebot/                       # Umbrella chart
│       ├── Chart.yaml                  # Umbrella chart definition
│       ├── values.yaml                 # Top-level values with all env vars
│       └── charts/
│           ├── frontend/               # Frontend subchart
│           │   ├── Chart.yaml
│           │   ├── values.yaml
│           │   └── templates/
│           │       ├── _helpers.tpl
│           │       ├── deployment.yaml
│           │       └── service.yaml
│           ├── backend/                # Backend subchart
│           │   ├── Chart.yaml
│           │   ├── values.yaml
│           │   └── templates/
│           │       ├── _helpers.tpl
│           │       ├── secret.yaml
│           │       ├── deployment.yaml
│           │       └── service.yaml
│           ├── postgres/               # Postgres subchart
│           │   ├── Chart.yaml
│           │   ├── values.yaml
│           │   └── templates/
│           │       ├── _helpers.tpl
│           │       ├── deployment.yaml
│           │       └── service.yaml
│           └── qdrant/                 # Qdrant subchart
│               ├── Chart.yaml
│               ├── values.yaml
│               └── templates/
│                   ├── _helpers.tpl
│                   ├── deployment.yaml
│                   └── service.yaml
└── DEPLOYMENT.md                       # This file
```
