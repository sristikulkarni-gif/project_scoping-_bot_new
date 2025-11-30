# GitHub Secrets - Quick Reference

## Copy this list and create these secrets in your GitHub repository

**Location:** Repository → Settings → Secrets and variables → Actions → New repository secret

---

## All Required Secrets

| # | Secret Name | Your Value | Status |
|---|-------------|------------|--------|
| 1 | `AZURE_CLIENT_ID` | (your app registration client ID) | ⬜ |
| 2 | `AZURE_TENANT_ID` | (your Azure tenant ID) | ⬜ |
| 3 | `AZURE_CLIENT_SECRET` | (your app registration client secret) | ⬜ |
| 4 | `VM_HOST` | (your Azure VM public IP) | ⬜ |
| 5 | `VM_USER` | `azureuser` | ⬜ |
| 6 | `VM_SSH_KEY` | (your complete private SSH key) | ⬜ |
| 7 | `POSTGRES_PASSWORD` | (generate with: `openssl rand -base64 32`) | ⬜ |
| 8 | `SECRET_KEY` | (generate with: `openssl rand -hex 32`) | ⬜ |
| 9 | `SMTP_HOST` | `smtp.gmail.com` | ⬜ |
| 10 | `SMTP_PORT` | `587` | ⬜ |
| 11 | `SMTP_USER` | (your email address) | ⬜ |
| 12 | `SMTP_PASS` | (your Gmail app password) | ⬜ |
| 13 | `AZURE_STORAGE_ACCOUNT` | `scopebot` | ⬜ |
| 14 | `AZURE_STORAGE_KEY` | (from Azure Portal → Storage Accounts → Access keys) | ⬜ |
| 15 | `AZURE_STORAGE_CONTAINER` | `botcontainer` | ⬜ |
| 16 | `OLLAMA_HOST` | (optional - your Ollama service URL) | ⬜ |

---

## Quick Commands

### Generate secure passwords:
```bash
# PostgreSQL password
openssl rand -base64 32

# JWT secret key
openssl rand -hex 32
```

### View your SSH private key:
```bash
cat ~/.ssh/id_rsa
# Copy the ENTIRE output including -----BEGIN and -----END lines
```

### Get Azure Storage Key:
```bash
az storage account keys list --account-name scopebot --resource-group <your-rg> --query '[0].value' -o tsv
```

---

## ACR Configuration (Already Set)

Your Azure Container Registry is: `scopingbotacr.azurecr.io`

This is already configured in the pipeline. You just need to ensure your Service Principal has the `AcrPush` role.

---

## Application Access After Deployment

- **Frontend**: `http://<VM_IP>:30080`
- **Backend API**: `http://<VM_IP>:30800`

---

## Checklist

After adding all secrets:

- [ ] All 16 secrets added to GitHub
- [ ] Service Principal has AcrPush role for ACR
- [ ] VM allows inbound traffic on ports 22, 30080, 30800
- [ ] SSH public key added to VM's `~/.ssh/authorized_keys`
- [ ] Minikube is installed and running on VM
- [ ] Docker is installed on VM

Ready to deploy! Push to `main` or `develop` branch to trigger the pipeline.

---

For detailed information, see `GITHUB_SECRETS_SETUP.md`
