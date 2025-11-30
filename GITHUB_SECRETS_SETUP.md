# GitHub Secrets Setup Guide

This guide explains how to configure GitHub Secrets for the CI/CD pipeline to securely deploy your application to Azure VM with Minikube.

## Overview

The CI/CD pipeline automatically:
1. ✅ Builds Docker images for frontend and backend
2. ✅ Pushes images to Azure Container Registry (ACR)
3. ✅ SSHs into your Azure VM
4. ✅ Pulls images from ACR into Minikube
5. ✅ Deploys using Helm charts with injected secrets
6. ✅ Exposes services via NodePort for external access

## Required GitHub Secrets

You need to configure the following secrets in your GitHub repository:

### Navigation
Go to: **Repository → Settings → Secrets and variables → Actions → New repository secret**

---

## 1. Azure Container Registry Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AZURE_CLIENT_ID` | Service Principal Client ID (App Registration) | `12345678-1234-1234-1234-123456789abc` |
| `AZURE_TENANT_ID` | Azure Tenant ID | `87654321-4321-4321-4321-cba987654321` |
| `AZURE_CLIENT_SECRET` | Service Principal Client Secret | `your-client-secret-value` |

**How to get these:**
1. In Azure Portal, go to **App Registrations**
2. Select your app registration (or create a new one)
3. **Client ID**: Found on the Overview page
4. **Tenant ID**: Found on the Overview page
5. **Client Secret**: Go to "Certificates & secrets" → "New client secret"

**Grant ACR permissions:**
```bash
# Assign AcrPush role to the service principal
az role assignment create \
  --assignee <AZURE_CLIENT_ID> \
  --role AcrPush \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.ContainerRegistry/registries/scopingbotacr
```

---

## 2. Azure VM SSH Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `VM_HOST` | Azure VM public IP address | `20.123.45.67` |
| `VM_USER` | SSH username (default: azureuser) | `azureuser` |
| `VM_SSH_KEY` | **Complete private SSH key** | See below ⬇️ |

**VM_SSH_KEY Format:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
NhAAAAAwEAAQAAAYEA... (full key content)
... (multiple lines)
-----END OPENSSH PRIVATE KEY-----
```

**IMPORTANT:**
- Copy the **entire** private key including headers and footers
- Do NOT add quotes or modify the format
- Ensure the public key is added to `~/.ssh/authorized_keys` on the VM

---

## 3. Database Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `POSTGRES_PASSWORD` | PostgreSQL database password | `YourSecurePassword123!` |

**Generate a secure password:**
```bash
openssl rand -base64 32
```

---

## 4. Authentication Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `SECRET_KEY` | JWT signing key for authentication | `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6` |

**Generate SECRET_KEY:**
```bash
openssl rand -hex 32
```

---

## 5. SMTP Email Secrets (for password reset)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | Email address for sending | `your-email@gmail.com` |
| `SMTP_PASS` | Email password or app password | `your-gmail-app-password` |

**For Gmail:**
1. Go to Google Account → Security
2. Enable 2-Factor Authentication
3. Go to "App passwords"
4. Generate a new app password for "Mail"
5. Use the generated 16-character password as `SMTP_PASS`

---

## 6. Azure Storage Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AZURE_STORAGE_ACCOUNT` | Storage account name | `scopebot` |
| `AZURE_STORAGE_KEY` | Storage account access key | `za2pfLEOqo3WpVvbDuNTbm/wix...` |
| `AZURE_STORAGE_CONTAINER` | Blob container name | `botcontainer` |

**How to get Storage Key:**
1. Azure Portal → Storage Accounts → Your account
2. Go to "Access keys"
3. Copy "key1" value

---

## 7. Ollama Configuration (Optional)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `OLLAMA_HOST` | Ollama service URL | `http://172.190.86.69:11434` |

**Note:** Only set this if you're using an external Ollama service.

---

## Complete Secrets Checklist

Use this checklist to ensure all secrets are configured:

- [ ] `AZURE_CLIENT_ID` - Service Principal Client ID
- [ ] `AZURE_TENANT_ID` - Azure Tenant ID
- [ ] `AZURE_CLIENT_SECRET` - Service Principal Secret
- [ ] `VM_HOST` - Azure VM IP address
- [ ] `VM_USER` - SSH username (azureuser)
- [ ] `VM_SSH_KEY` - Complete private SSH key
- [ ] `POSTGRES_PASSWORD` - Database password
- [ ] `SECRET_KEY` - JWT signing key
- [ ] `SMTP_HOST` - SMTP server (smtp.gmail.com)
- [ ] `SMTP_PORT` - SMTP port (587)
- [ ] `SMTP_USER` - Email address
- [ ] `SMTP_PASS` - Email app password
- [ ] `AZURE_STORAGE_ACCOUNT` - Storage account name
- [ ] `AZURE_STORAGE_KEY` - Storage account key
- [ ] `AZURE_STORAGE_CONTAINER` - Blob container name
- [ ] `OLLAMA_HOST` - Ollama URL (optional)

---

## How to Deploy

### Automatic Deployment (Recommended)

The pipeline automatically triggers on:
- Push to `main` branch
- Push to `develop` branch
- Manual trigger via GitHub Actions UI

**Manual Trigger:**
1. Go to **Actions** tab in GitHub
2. Select "Build and Deploy to Azure VM"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### Deployment Flow

```mermaid
graph LR
    A[Push Code] --> B[Build Docker Images]
    B --> C[Push to ACR]
    C --> D[SSH to VM]
    D --> E[Pull Images to Minikube]
    E --> F[Deploy with Helm]
    F --> G[Expose NodePort Services]
```

---

## Accessing Your Application

After successful deployment, your application is exposed via NodePort:

### Get VM Public IP
```bash
# Already configured in VM_HOST secret
VM_IP=<your-vm-ip>
```

### Access Services

**Frontend:**
```
http://<VM_IP>:30080
```

**Backend API:**
```
http://<VM_IP>:30800
```

### Verify Deployment

SSH into your VM and check:
```bash
ssh azureuser@<VM_IP>

# Check pods
kubectl get pods -n scopebot

# Check services
kubectl get svc -n scopebot

# Check persistent volumes
kubectl get pvc -n scopebot

# View logs
kubectl logs -n scopebot deployment/scopebot-backend
kubectl logs -n scopebot deployment/scopebot-frontend
```

---

## Troubleshooting

### 1. Pipeline Fails at "Login to ACR"
**Issue:** Authentication failed to Azure Container Registry

**Solution:**
- Verify `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` are correct
- Ensure Service Principal has `AcrPush` role assigned

### 2. SSH Connection Fails
**Issue:** Permission denied or connection refused

**Solution:**
- Verify `VM_SSH_KEY` contains the complete private key
- Ensure public key is in `~/.ssh/authorized_keys` on VM
- Check VM network security group allows SSH (port 22)
- Verify `VM_HOST` IP is correct

### 3. Image Pull Errors in Kubernetes
**Issue:** `ImagePullBackOff` or `ErrImagePull`

**Solution:**
- Check ACR credentials are correct
- Verify Minikube can access ACR:
  ```bash
  minikube ssh "docker pull scopingbotacr.azurecr.io/scopebot-frontend:latest"
  ```

### 4. Database Connection Errors
**Issue:** Backend cannot connect to PostgreSQL

**Solution:**
- Verify `POSTGRES_PASSWORD` matches in both backend and postgres configs
- Check database pod is running: `kubectl get pods -n scopebot`

### 5. Services Not Accessible
**Issue:** Cannot access frontend/backend via browser

**Solution:**
- Check Azure NSG allows inbound traffic on ports 30080 and 30800
- Verify services are exposed:
  ```bash
  kubectl get svc -n scopebot
  ```
- Check Minikube is running: `minikube status`

### 6. Data Loss After Restart
**Issue:** Database/Qdrant data is lost after pod restart

**Solution:**
- Verify PVCs are created: `kubectl get pvc -n scopebot`
- Check storage class is available: `kubectl get storageclass`
- Ensure `persistence.enabled: true` in values.yaml

---

## Security Best Practices

1. ✅ **Never commit secrets to git**
2. ✅ **Rotate secrets regularly** (every 90 days)
3. ✅ **Use strong passwords** (minimum 32 characters)
4. ✅ **Limit Service Principal permissions** (principle of least privilege)
5. ✅ **Enable Azure Key Vault** for production environments
6. ✅ **Use managed identities** when possible
7. ✅ **Monitor access logs** for suspicious activity
8. ✅ **Implement network security groups** to restrict access

---

## Data Persistence

Your deployment uses PersistentVolumeClaims (PVC) for:

- **PostgreSQL**: 10Gi volume at `/var/lib/postgresql/data`
- **Qdrant**: 10Gi volume at `/qdrant/storage`

**Data is preserved across:**
- ✅ Pod restarts
- ✅ Helm upgrades
- ✅ Application updates

**Data is NOT preserved if:**
- ❌ PVC is manually deleted
- ❌ Namespace is deleted
- ❌ Minikube cluster is destroyed

**Backup Strategy:**
```bash
# Backup PostgreSQL
kubectl exec -n scopebot deployment/scopebot-postgres -- pg_dump -U scopebot scopebot_db > backup.sql

# Backup Qdrant (copy storage)
kubectl cp scopebot/scopebot-qdrant-xxx:/qdrant/storage ./qdrant-backup
```

---

## Support

If you encounter issues:

1. Check pipeline logs in GitHub Actions
2. Check pod logs: `kubectl logs -n scopebot <pod-name>`
3. Review this documentation
4. Check Helm deployment status: `helm status scopebot -n scopebot`

---

## Next Steps

After successful deployment:

1. ✅ Verify all pods are running
2. ✅ Test frontend access at `http://<VM_IP>:30080`
3. ✅ Test backend API at `http://<VM_IP>:30800`
4. ✅ Configure DNS (optional) for friendly URLs
5. ✅ Set up SSL/TLS certificates (recommended for production)
6. ✅ Configure monitoring and alerts
7. ✅ Set up automated backups

---

**Last Updated:** 2025-11-30
