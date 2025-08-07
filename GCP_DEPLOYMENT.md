# 🌟 Google Cloud Serverless Deployment Guide

Bu dokümanda Yargısal Zeka projesinin Google Cloud Platform'da serverless olarak nasıl deploy edileceği anlatılmaktadır.

## 🏗️ Serverless Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │ Cloud CDN + │    │  Cloud Run   │    │ Cloud Functions │ │
│  │Load Balancer│◄──►│  Main API    │◄──►│ Yargıtay Scraper│ │
│  │ (Frontend)  │    │  (FastAPI)   │    │   (Selenium)    │ │
│  └─────────────┘    └──────────────┘    └─────────────────┘ │
│                              │                              │
│                              ▼                              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │Cloud Storage│    │  Firestore   │    │ Secret Manager  │ │
│  │(Static/Backup)│  │ (Database)   │    │ (API Keys)      │ │
│  └─────────────┘    └──────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Hızlı Başlangıç

### Ön Gereksinimler

1. **Google Cloud hesabı** ve aktif bir proje
2. **gcloud CLI** kurulu ve yapılandırılmış
3. **Docker** kurulu
4. **Terraform** kurulu (isteğe bağlı, manuel deployment için)

### 1. GCP Setup

```bash
# gcloud CLI'yi yükle ve yapılandır
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set compute/region europe-west1

# Gerekli API'leri etkinleştir
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Environment Variables

```bash
# Gerekli environment variables'ı ayarla
export GEMINI_API_KEY="your-gemini-api-key"
export JWT_SECRET_KEY="your-super-secure-jwt-secret-32-chars-min"
export PROJECT_ID="your-gcp-project-id"
export DOMAIN_NAME="yargisalzeka.com"  # İsteğe bağlı
```

### 3. Otomatik Deployment

```bash
# Tek komutla tam deployment
./gcp/deploy.sh deploy
```

## 📋 Deployment Seçenekleri

### Seçenek 1: Otomatik Deployment (Önerilen)

```bash
# Tam otomatik deployment
GEMINI_API_KEY="your-key" JWT_SECRET_KEY="your-secret" ./gcp/deploy.sh deploy
```

### Seçenek 2: Cloud Build ile CI/CD

```bash
# Cloud Build trigger'ı oluştur
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY="your-key",_JWT_SECRET_KEY="your-secret"
```

### Seçenek 3: Manuel Adım Adım

```bash
# 1. Docker images'ları build et ve push et
./gcp/deploy.sh build

# 2. Infrastructure'ı deploy et
./gcp/deploy.sh infrastructure

# 3. Cloud Functions'ları deploy et
./gcp/deploy.sh functions

# 4. Deployment'ı doğrula
./gcp/deploy.sh verify
```

### Seçenek 4: Terraform ile Infrastructure as Code

```bash
cd gcp/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="project_id=your-project" \
               -var="gemini_api_key=your-key" \
               -var="jwt_secret_key=your-secret"

# Apply infrastructure
terraform apply
```

## 🔧 Servis Detayları

### Cloud Run - Main API

```yaml
Service: yargisalzeka-api
Memory: 2Gi
CPU: 2 vCPU
Max Instances: 100
Min Instances: 1
Concurrency: 80
Timeout: 300s
```

**Özellikler:**
- JWT Authentication
- Rate Limiting
- Firestore Integration
- Secret Manager Integration
- Auto-scaling

### Cloud Run - Frontend

```yaml
Service: yargisalzeka-frontend
Memory: 512Mi
CPU: 1 vCPU
Max Instances: 50
Min Instances: 0
Concurrency: 1000
Timeout: 60s
```

**Özellikler:**
- React SPA
- Nginx reverse proxy
- Static asset caching
- API proxy to backend

### Cloud Functions - Scraper

```yaml
Function: yargitay-scraper
Memory: 2GB
Timeout: 540s
Max Instances: 10
Runtime: Python 3.11
```

**Özellikler:**
- Selenium web scraping
- Firestore caching
- Parallel processing
- Error handling

### Firestore Database

```yaml
Type: Native Mode
Location: europe-west1
Collections:
  - users
  - api_usage
  - analysis_results
  - keywords_cache
  - search_cache
  - system_logs
```

## 🔒 Güvenlik Konfigürasyonu

### Secret Manager

Tüm hassas bilgiler Secret Manager'da saklanır:

```bash
# Secret'ları oluştur
gcloud secrets create gemini-api-key --data-file=-
gcloud secrets create jwt-secret-key --data-file=-

# Service account'lara erişim ver
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:your-service-account@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### IAM Permissions

Service account'lar minimum gerekli izinlerle:

- `roles/datastore.user` - Firestore erişimi
- `roles/secretmanager.secretAccessor` - Secret erişimi
- `roles/storage.objectAdmin` - Storage erişimi
- `roles/logging.logWriter` - Log yazma
- `roles/monitoring.metricWriter` - Metrics yazma

### Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // API usage logs - only service can write
    match /api_usage/{document} {
      allow read: if request.auth != null;
      allow write: if false; // Only backend can write
    }
    
    // Cache collections - read/write for authenticated users
    match /{collection}/{document} {
      allow read, write: if request.auth != null && 
        collection in ['keywords_cache', 'search_cache', 'analysis_results'];
    }
  }
}
```

## 🌐 Custom Domain Setup

### SSL Sertifikası ve Load Balancer

```bash
# Load balancer IP'sini al
LB_IP=$(gcloud compute addresses describe yargisalzeka-ip --global --format='value(address)')
echo "Load Balancer IP: $LB_IP"
```

### DNS Konfigürasyonu

Domain sağlayıcınızda aşağıdaki kayıtları ekleyin:

```dns
# A Record
yargisalzeka.com.     300   IN   A      35.190.XXX.XXX

# CNAME Record  
www.yargisalzeka.com. 300   IN   CNAME  yargisalzeka.com.
```

### SSL Sertifika Doğrulama

```bash
# SSL sertifika durumunu kontrol et
gcloud compute ssl-certificates describe yargisalzeka-ssl-cert --global
```

## 📊 Monitoring ve Logging

### Cloud Monitoring

Otomatik oluşturulan metrikler:

- **API Response Time**: Cloud Run latency metrics
- **Error Rate**: HTTP 5xx error count
- **Request Count**: Total requests per service
- **Resource Usage**: CPU, Memory utilization

### Cloud Logging

Log sorguları:

```sql
-- API Errors
resource.type="cloud_run_revision" 
AND resource.labels.service_name="yargisalzeka-api"
AND severity>=ERROR

-- High Latency Requests
resource.type="cloud_run_revision"
AND httpRequest.latency>2000ms

-- Authentication Failures
textPayload:"authentication failed"
OR textPayload:"invalid token"
```

### Alerting

```bash
# Error rate alert
gcloud alpha monitoring policies create --policy-from-file=monitoring/error-rate-policy.yaml

# High latency alert  
gcloud alpha monitoring policies create --policy-from-file=monitoring/latency-policy.yaml
```

## 💰 Cost Optimization

### Cloud Run Pricing

```yaml
# Cost-optimized configuration
Main API:
  Min Instances: 1      # Keep warm instance
  Max Instances: 100    # Scale up when needed
  CPU: 2 vCPU          # Adequate for AI processing
  Memory: 2Gi          # Sufficient for workload

Frontend:
  Min Instances: 0      # Scale to zero when idle
  Max Instances: 50     # Reasonable limit
  CPU: 1 vCPU          # Light workload
  Memory: 512Mi        # Minimal for static serving
```

### Cloud Functions Pricing

```yaml
# Optimized for cost and performance
Memory: 2GB            # Balance between speed and cost
Timeout: 540s          # Maximum for complex scraping
Max Instances: 10      # Prevent runaway costs
```

### Firestore Pricing

```yaml
# Efficient usage patterns
- Read/Write optimization with caching
- Composite indexes for efficient queries
- TTL for cache collections
- Batch operations where possible
```

### Tahmini Aylık Maliyetler

```
Cloud Run (Main API):     $20-50   (1M requests)
Cloud Run (Frontend):     $5-15    (Static serving)
Cloud Functions:          $10-30   (Scraping operations)
Firestore:               $5-20    (Read/Write operations)
Load Balancer:           $18      (Fixed cost)
Storage:                 $1-5     (Minimal usage)
Monitoring/Logging:      $5-15    (Standard usage)

Total Estimated:         $64-153  per month
```

## 🔄 CI/CD Pipeline

### GitHub Actions Integration

```yaml
# .github/workflows/deploy.yml
name: Deploy to Google Cloud
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - id: 'auth'
        uses: 'google-github-actions/auth@v1'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      
      - name: 'Deploy to Cloud Run'
        run: |
          gcloud builds submit --config cloudbuild.yaml
```

### Cloud Build Triggers

```bash
# GitHub trigger oluştur
gcloud builds triggers create github \
  --repo-name=yargisalzeka \
  --repo-owner=your-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## 🚨 Troubleshooting

### Common Issues

1. **Cold Start Latency**
   ```bash
   # Min instances ayarla
   gcloud run services update yargisalzeka-api \
     --min-instances=1 --region=europe-west1
   ```

2. **Memory Limits**
   ```bash
   # Memory'yi artır
   gcloud run services update yargisalzeka-api \
     --memory=4Gi --region=europe-west1
   ```

3. **SSL Certificate Issues**
   ```bash
   # SSL durumunu kontrol et
   gcloud compute ssl-certificates list
   ```

4. **Function Timeout**
   ```bash
   # Timeout'u artır
   gcloud functions deploy yargitay-scraper \
     --timeout=540s --memory=2GB
   ```

### Debug Commands

```bash
# Service logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50

# Function logs
gcloud functions logs read yargitay-scraper --limit=50

# Build logs
gcloud builds log --stream

# Service status
gcloud run services describe yargisalzeka-api --region=europe-west1
```

## 📞 Support

### Monitoring Dashboards

- **Cloud Console**: https://console.cloud.google.com/run
- **Monitoring**: https://console.cloud.google.com/monitoring
- **Logging**: https://console.cloud.google.com/logs

### Performance Optimization

1. **Database Optimization**
   - Composite indexes for complex queries
   - Caching frequently accessed data
   - Batch operations for bulk writes

2. **API Optimization**
   - Request/response caching
   - Connection pooling
   - Async processing for heavy operations

3. **Frontend Optimization**
   - CDN for static assets
   - Service worker for caching
   - Code splitting and lazy loading

---

Bu deployment guide ile Yargısal Zeka projenizi Google Cloud'da serverless olarak çalıştırabilir, otomatik ölçeklendirme, yüksek kullanılabilirlik ve cost-effectiveness avantajlarından yararlanabilirsiniz! 🚀
