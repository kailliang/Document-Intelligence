# Azure Deployment Plan for Patent Review System

## Overview

This document outlines a simplified Azure deployment strategy for the Patent Review System, optimized for 25 users with a monthly budget under $30.

## Architecture Overview

```
Internet → Azure App Service (Frontend + Backend)
                   ├── Azure Database for PostgreSQL flexible server
                   ├── Azure Storage Account (Blob containers for PDFs)
                   └── Azure Key Vault (API keys)
```

## Required Azure Services

### 1. Azure App Service
- **Purpose**: Host both React frontend and FastAPI backend in a single service
- **SKU**: B1 (Basic tier)
- **Features**: Built-in SSL, custom domains, auto-scaling, WebSocket support
- **Cost**: ~$13.14/month

### 2. Azure Database for PostgreSQL flexible server
- **Purpose**: Replace SQLite with managed PostgreSQL database
- **SKU**: Standard_B1ms (Burstable tier)
- **Features**: Automated backups, high availability options, connection pooling
- **Cost**: ~$12.41/month

### 3. Azure Storage Account
- **Purpose**: Store PDF exports in blob containers
- **Type**: General Purpose v2 (StorageV2)
- **Redundancy**: LRS (Locally Redundant Storage)
- **Features**: Private blob containers, access tiers, lifecycle management
- **Cost**: ~$2/month (for PDF storage)

### 4. Azure Key Vault
- **Purpose**: Secure storage for API keys (OpenAI, Gemini)
- **SKU**: Standard
- **Features**: Managed identity integration, secret versioning, access policies
- **Cost**: ~$1/month

**Total Monthly Cost: ~$28.50**

## Step-by-Step Deployment Process

### Phase 1: Azure Infrastructure Setup (30 minutes)

#### 1.1 Create Resource Group
```bash
az group create --name rg-patent-simple --location eastus2
```

#### 1.2 Create Azure Database for PostgreSQL flexible server
```bash
az postgres flexible-server create \
  --resource-group rg-patent-simple \
  --name psql-patent-simple \
  --admin-user patentuser \
  --admin-password "YourSecurePassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 14 \
  --storage-size 32 \
  --location eastus2

# Enable Azure services access
az postgres flexible-server firewall-rule create \
  --resource-group rg-patent-simple \
  --name psql-patent-simple \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

#### 1.3 Create Azure Storage Account
```bash
az storage account create \
  --resource-group rg-patent-simple \
  --name stpatentsimple001 \
  --location eastus2 \
  --sku Standard_LRS \
  --kind StorageV2

# Create blob container for PDFs
az storage container create \
  --account-name stpatentsimple001 \
  --name pdf-exports \
  --auth-mode login
```

#### 1.4 Create Azure Key Vault
```bash
az keyvault create \
  --resource-group rg-patent-simple \
  --name kv-patent-simple-001 \
  --location eastus2 \
  --sku standard
```

#### 1.5 Create Azure App Service
```bash
# Create App Service Plan
az appservice plan create \
  --resource-group rg-patent-simple \
  --name plan-patent-simple \
  --sku B1 \
  --is-linux \
  --location eastus2

# Create Web App
az webapp create \
  --resource-group rg-patent-simple \
  --plan plan-patent-simple \
  --name app-patent-simple-001 \
  --runtime "PYTHON|3.11"
```

### Phase 2: Configuration (15 minutes)

#### 2.1 Store Secrets in Azure Key Vault
```bash
az keyvault secret set \
  --vault-name kv-patent-simple-001 \
  --name openai-api-key \
  --value "your-openai-api-key-here"

az keyvault secret set \
  --vault-name kv-patent-simple-001 \
  --name gemini-api-key \
  --value "your-gemini-api-key-here"

az keyvault secret set \
  --vault-name kv-patent-simple-001 \
  --name database-url \
  --value "postgresql://patentuser:YourSecurePassword123!@psql-patent-simple.postgres.database.azure.com/postgres"
```

#### 2.2 Configure App Service Environment Variables
```bash
az webapp config appsettings set \
  --resource-group rg-patent-simple \
  --name app-patent-simple-001 \
  --settings \
    DATABASE_URL="@Microsoft.KeyVault(VaultName=kv-patent-simple-001;SecretName=database-url)" \
    AZURE_STORAGE_CONNECTION_STRING="$(az storage account show-connection-string --name stpatentsimple001 --resource-group rg-patent-simple --output tsv)" \
    AZURE_STORAGE_CONTAINER="pdf-exports" \
    OPENAI_API_KEY="@Microsoft.KeyVault(VaultName=kv-patent-simple-001;SecretName=openai-api-key)" \
    GEMINI_API_KEY="@Microsoft.KeyVault(VaultName=kv-patent-simple-001;SecretName=gemini-api-key)" \
    AI_MODEL="gemini-2.5-flash"
```

#### 2.3 Enable Managed Identity
```bash
az webapp identity assign \
  --resource-group rg-patent-simple \
  --name app-patent-simple-001

# Grant Key Vault access (replace with actual principal ID)
az keyvault set-policy \
  --name kv-patent-simple-001 \
  --object-id "managed-identity-principal-id" \
  --secret-permissions get list
```

### Phase 3: Code Modifications Required

#### 3.1 Update Dependencies
Add to `server/requirements.txt`:
```
azure-storage-blob>=12.19.0
azure-identity>=1.14.0
azure-keyvault-secrets>=4.7.0
psycopg2-binary>=2.9.0
```

#### 3.2 Database Configuration Changes
Update `server/app/internal/db.py`:
```python
import os
from sqlalchemy import create_engine

# Use environment variable for database connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
engine = create_engine(DATABASE_URL)
```

#### 3.3 Azure Blob Storage Integration
Create `server/app/internal/azure_storage.py`:
```python
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import os
from datetime import datetime

class AzureBlobStorage:
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_service = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER", "pdf-exports")
    
    async def upload_pdf(self, pdf_content: bytes, document_id: int, version_number: int) -> str:
        """Upload PDF to Azure Blob Storage and return blob URL"""
        blob_name = f"patent-{document_id}-v{version_number}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name, 
            blob=blob_name
        )
        
        blob_client.upload_blob(pdf_content, overwrite=True)
        return blob_client.url
    
    async def get_pdf_url(self, blob_name: str) -> str:
        """Get signed URL for PDF download"""
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name, 
            blob=blob_name
        )
        return blob_client.url
```

#### 3.4 Update PDF Export Service
Modify `server/app/internal/pdf_export_simple.py`:
```python
from app.internal.azure_storage import AzureBlobStorage

class SimplePDFExporter:
    def __init__(self):
        self.azure_storage = AzureBlobStorage()
    
    async def export_document(self, document, current_version):
        # Generate PDF (existing logic)
        pdf_content = self.generate_pdf_content(document, current_version)
        
        # Upload to Azure Blob Storage
        blob_url = await self.azure_storage.upload_pdf(
            pdf_content, 
            document.id, 
            current_version.version_number
        )
        
        return blob_url
```

#### 3.5 Serve React App from FastAPI
Update `server/app/__main__.py`:
```python
from fastapi.staticfiles import StaticFiles
import os

# Add static file serving for React app
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/", StaticFiles(directory="static", html=True), name="frontend")
```

### Phase 4: Build and Deployment Process

#### 4.1 Build Script
Create `deploy.sh`:
```bash
#!/bin/bash

# Build React frontend
echo "Building React frontend..."
cd client
npm run build

# Copy build files to server static directory
echo "Copying frontend build to server..."
mkdir -p ../server/app/static
cp -r dist/* ../server/app/static/

# Create deployment package
echo "Creating deployment package..."
cd ../server
zip -r ../deployment.zip . -x "*.pyc" "__pycache__/*" ".env" "*.sqlite" "database.db"

echo "Deployment package ready: deployment.zip"
```

#### 4.2 Deploy to Azure App Service
```bash
az webapp deployment source config-zip \
  --resource-group rg-patent-simple \
  --name app-patent-simple-001 \
  --src deployment.zip
```

### Phase 5: Database Migration

#### 5.1 Create Migration Script
Create `migrate_to_postgres.py`:
```python
import sqlite3
import psycopg2
import os
from datetime import datetime

def migrate_sqlite_to_postgres():
    # SQLite connection
    sqlite_conn = sqlite3.connect('database.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # PostgreSQL connection
    postgres_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    postgres_cursor = postgres_conn.cursor()
    
    # Migrate documents table
    sqlite_cursor.execute("SELECT * FROM document")
    documents = sqlite_cursor.fetchall()
    
    for doc in documents:
        postgres_cursor.execute("""
            INSERT INTO document (id, title, current_version_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, doc)
    
    # Migrate document_version table
    sqlite_cursor.execute("SELECT * FROM document_version")
    versions = sqlite_cursor.fetchall()
    
    for version in versions:
        postgres_cursor.execute("""
            INSERT INTO document_version (id, document_id, version_number, content, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, version)
    
    # Migrate chat_history table
    sqlite_cursor.execute("SELECT * FROM chat_history")
    chats = sqlite_cursor.fetchall()
    
    for chat in chats:
        postgres_cursor.execute("""
            INSERT INTO chat_history (id, document_id, document_version, message_type, content, suggestion_cards, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, chat)
    
    postgres_conn.commit()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_sqlite_to_postgres()
```

## Testing and Validation

### 1. Health Checks
Add health endpoint to `server/app/__main__.py`:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected",
            "blob_storage": "connected",
            "key_vault": "connected"
        }
    }
```

### 2. Test URLs
- **Application**: `https://app-patent-simple-001.azurewebsites.net`
- **Health Check**: `https://app-patent-simple-001.azurewebsites.net/health`
- **API Docs**: `https://app-patent-simple-001.azurewebsites.net/docs`

### 3. Verification Steps
1. Test document upload and editing
2. Verify AI analysis with both OpenAI and Gemini
3. Test PDF export to Azure Blob Storage
4. Verify WebSocket connections for real-time chat
5. Test version management functionality

## Security Considerations

### 1. Network Security
- App Service uses HTTPS by default
- PostgreSQL allows only Azure services
- Blob storage is private by default

### 2. Secrets Management
- All API keys stored in Azure Key Vault
- Managed identity for secure access
- No secrets in code or environment

### 3. Database Security
- SSL-encrypted connections
- Azure AD authentication available
- Network isolation options

## Monitoring and Logging

### 1. Application Insights
```bash
az monitor app-insights component create \
  --resource-group rg-patent-simple \
  --app patent-review-insights \
  --location eastus2 \
  --application-type web
```

### 2. Key Metrics to Monitor
- Application response time
- Database connection pool usage
- Blob storage operations
- WebSocket connection count
- Error rates and exceptions

## Scaling Considerations

### Current Capacity (B1 App Service)
- **Concurrent Users**: ~100
- **CPU**: 1 core
- **Memory**: 1.75 GB
- **Storage**: 10 GB

### Upgrade Paths
1. **S1 Standard**: $74/month - 100 daily active users
2. **P1V2 Premium**: $146/month - 500+ users with better performance
3. **Container Apps**: For microservices architecture

## Backup and Disaster Recovery

### 1. Database Backups
- Automated daily backups (7-day retention)
- Point-in-time restore available
- Cross-region backup replication option

### 2. Application Backups
- App Service automatic backups
- Source code in Git repository
- Blob storage geo-redundancy option

### 3. Recovery Procedures
1. Database restore from backup
2. App Service restore from snapshot
3. Redeploy from Git repository
4. Restore blob storage if needed

## Cost Optimization Tips

### 1. Development Environment
- Use **Free tier** App Service for testing
- **Basic tier** PostgreSQL for development
- Separate resource group for easy cleanup

### 2. Production Optimizations
- Enable **auto-pause** for PostgreSQL during low usage
- Use **cool storage tier** for old PDF files
- Configure **auto-scaling** rules for traffic spikes

### 3. Monthly Cost Breakdown
```
Azure App Service (B1):           $13.14
PostgreSQL flexible server:      $12.41
Storage Account + Blob:           $2.00
Key Vault operations:             $1.00
Data transfer:                    $0.50
Total:                           $29.05/month
```

## Troubleshooting Guide

### Common Issues

#### 1. Database Connection Errors
```bash
# Check PostgreSQL firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group rg-patent-simple \
  --name psql-patent-simple

# Test connection string
psql "postgresql://patentuser:password@psql-patent-simple.postgres.database.azure.com/postgres"
```

#### 2. App Service Deployment Issues
```bash
# Check deployment logs
az webapp log tail --resource-group rg-patent-simple --name app-patent-simple-001

# Check app settings
az webapp config appsettings list \
  --resource-group rg-patent-simple \
  --name app-patent-simple-001
```

#### 3. Blob Storage Access Issues
```bash
# Check storage account access
az storage container list --account-name stpatentsimple001 --auth-mode login

# Test blob upload
az storage blob upload \
  --account-name stpatentsimple001 \
  --container-name pdf-exports \
  --name test.txt \
  --file test.txt
```

#### 4. Key Vault Access Issues
```bash
# Check access policies
az keyvault show --name kv-patent-simple-001 --query properties.accessPolicies

# Test secret retrieval
az keyvault secret show --vault-name kv-patent-simple-001 --name openai-api-key
```

## Deployment Timeline

### Day 1: Infrastructure (2 hours)
- Create Azure services
- Configure networking and security
- Set up Key Vault secrets

### Day 2: Code Changes (4 hours)
- Update database configuration
- Implement Azure Blob Storage
- Add static file serving
- Test locally with Azure services

### Day 3: Deployment (2 hours)
- Build and package application
- Deploy to App Service
- Configure custom domain (optional)
- Test all functionality

### Day 4: Migration (2 hours)
- Migrate data from SQLite to PostgreSQL
- Verify data integrity
- Configure monitoring
- Go live!

## Support and Maintenance

### Regular Tasks
- **Weekly**: Review application logs and performance metrics
- **Monthly**: Check security updates and patches
- **Quarterly**: Review costs and optimize resources

### Azure Support Options
- **Basic**: Free - Basic support and documentation
- **Standard**: $100/month - Technical support with 8-hour response
- **Professional**: $1000/month - 24/7 support with 1-hour response

## Conclusion

This deployment plan provides a simple, cost-effective solution for hosting the Patent Review System on Azure for 25 users. The architecture leverages managed Azure services to minimize operational overhead while maintaining security and scalability.

**Key Benefits:**
- ✅ Under $30/month cost
- ✅ Single App Service for simplicity
- ✅ Managed database and storage
- ✅ Secure secrets management
- ✅ Built-in monitoring and backups
- ✅ Easy scaling path for growth

The deployment can be completed in 4 days with minimal code changes and provides a solid foundation for future growth.