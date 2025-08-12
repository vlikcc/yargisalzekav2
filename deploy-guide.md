# Yargısal Zeka - Google Cloud Deployment Rehberi

## 🚀 Deployment Seçenekleri

### 1. Google Cloud Run (Önerilen)
Serverless, otomatik ölçeklendirme, kullandıkça öde

### 2. Google App Engine
Tam yönetilen platform, kolay deployment

### 3. Google Kubernetes Engine (GKE)
Tam kontrol, karmaşık uygulamalar için

## 📋 Ön Gereksinimler

### Google Cloud Setup
```bash
# Google Cloud SDK kurulumu
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Giriş yapma
gcloud auth login

# Proje oluşturma
gcloud projects create yargisalzeka-prod --name="Yargısal Zeka"
gcloud config set project yargisalzeka-prod

# Gerekli API'leri etkinleştirme
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Environment Variables Setup
```bash
# Secret Manager'da environment variables oluşturma
gcloud secrets create gemini-api-key --data-file=<(echo -n "YOUR_GEMINI_API_KEY")
gcloud secrets create jwt-secret-key --data-file=<(echo -n "YOUR_JWT_SECRET_KEY")
gcloud secrets create gcp-project-id --data-file=<(echo -n "yargisalzeka-prod")
```

## 🔧 Google Cloud Run Deployment

### Backend Deployment
```bash
cd hukuk-asistan-main

# Docker image build ve push
gcloud builds submit --tag gcr.io/yargisalzeka-prod/backend

# Cloud Run'a deploy
gcloud run deploy yargisalzeka-backend \
  --image gcr.io/yargisalzeka-prod/backend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --set-secrets JWT_SECRET_KEY=jwt-secret-key:latest \
  --set-secrets GCP_PROJECT_ID=gcp-project-id:latest \
  --memory 2Gi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 1
```

### Frontend Deployment
```bash
cd yargisalzeka-frontend

# Build için environment variables
echo "VITE_API_BASE_URL=https://yargisalzeka-backend-xxx-ew.a.run.app" > .env.production

# Docker image build ve push
gcloud builds submit --tag gcr.io/yargisalzeka-prod/frontend

# Cloud Run'a deploy
gcloud run deploy yargisalzeka-frontend \
  --image gcr.io/yargisalzeka-prod/frontend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --port 80 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 5
```

### Scraper API Deployment
```bash
cd yargitay-scraper-api

# Docker image build ve push
gcloud builds submit --tag gcr.io/yargisalzeka-prod/scraper

# Cloud Run'a deploy
gcloud run deploy yargisalzeka-scraper \
  --image gcr.io/yargisalzeka-prod/scraper \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 3
```

## 🌐 Domain ve SSL Setup

### Custom Domain
```bash
# Domain mapping
gcloud run domain-mappings create \
  --service yargisalzeka-frontend \
  --domain yargisalzeka.com \
  --region europe-west1

# API subdomain
gcloud run domain-mappings create \
  --service yargisalzeka-backend \
  --domain api.yargisalzeka.com \
  --region europe-west1
```

### DNS Ayarları
```
# A Records
yargisalzeka.com -> Cloud Run IP
www.yargisalzeka.com -> Cloud Run IP
api.yargisalzeka.com -> Cloud Run IP

# CNAME Records
www -> yargisalzeka.com
```

## 🔒 Firestore Database Setup

### Database Oluşturma
```bash
# Firestore Native mode'da database oluşturma
gcloud firestore databases create --region=europe-west1

# Index'ler oluşturma (firestore.indexes.json)
gcloud firestore indexes create --index-file=firestore.indexes.json
```

### Security Rules
```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users collection
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Search history
    match /search_history/{searchId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Analysis results
    match /analysis_results/{resultId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
  }
}
```

## 📊 Monitoring ve Logging

### Cloud Monitoring Setup
```bash
# Alerting policies oluşturma
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

### Log-based Metrics
```bash
# Error rate metric
gcloud logging metrics create error_rate \
  --description="Application error rate" \
  --log-filter='resource.type="cloud_run_revision" AND severity>=ERROR'
```

## 🔄 CI/CD Pipeline (Cloud Build)

### cloudbuild.yaml
```yaml
steps:
  # Backend build
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/backend', './hukuk-asistan-main']
  
  # Frontend build
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/frontend', './yargisalzeka-frontend']
  
  # Deploy backend
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'yargisalzeka-backend', 
           '--image', 'gcr.io/$PROJECT_ID/backend',
           '--region', 'europe-west1',
           '--platform', 'managed']
  
  # Deploy frontend
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'yargisalzeka-frontend',
           '--image', 'gcr.io/$PROJECT_ID/frontend',
           '--region', 'europe-west1',
           '--platform', 'managed']

images:
  - 'gcr.io/$PROJECT_ID/backend'
  - 'gcr.io/$PROJECT_ID/frontend'
```

### GitHub Integration
```bash
# Cloud Build trigger oluşturma
gcloud builds triggers create github \
  --repo-name=yargisalzeka \
  --repo-owner=vlikcc \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## 💰 Maliyet Optimizasyonu

### Cloud Run Ayarları
- **Min instances**: 1 (cold start'ı önlemek için)
- **Max instances**: 10 (maliyet kontrolü)
- **CPU allocation**: Request sırasında (maliyet tasarrufu)
- **Memory**: İhtiyaca göre optimize

### Firestore Optimizasyonu
- **Read/Write limits**: Rate limiting ile kontrol
- **Index optimization**: Gereksiz index'leri kaldırma
- **Data retention**: Eski verileri temizleme

## 🧪 Testing ve Validation

### Health Checks
```bash
# Backend health check
curl https://api.yargisalzeka.com/health

# Frontend health check
curl https://yargisalzeka.com/health
```

### Load Testing
```bash
# Apache Bench ile load test
ab -n 1000 -c 10 https://api.yargisalzeka.com/health
```

## 🔧 Troubleshooting

### Common Issues
1. **Cold Start**: Min instances ayarlayın
2. **Memory Issues**: Memory limitlerini artırın
3. **Timeout**: Request timeout'ları kontrol edin
4. **CORS Errors**: Domain ayarlarını kontrol edin

### Logs
```bash
# Cloud Run logs
gcloud logs read --service=yargisalzeka-backend --limit=50

# Real-time logs
gcloud logs tail --service=yargisalzeka-backend
```

## 📈 Scaling Considerations

### Traffic Patterns
- **Peak hours**: 09:00-18:00 (iş saatleri)
- **Geographic**: Türkiye odaklı
- **Seasonal**: Hukuki dönemler

### Auto-scaling
- **CPU threshold**: %60
- **Memory threshold**: %80
- **Request latency**: <2s

## 🔐 Security Checklist

- [x] HTTPS enforced
- [x] CORS properly configured
- [x] Environment variables secured
- [x] Database access controlled
- [x] API rate limiting enabled
- [x] Input validation implemented
- [x] Error messages sanitized

## 📞 Support ve Maintenance

### Monitoring Dashboards
- Cloud Run metrics
- Firestore usage
- Error rates
- Response times

### Backup Strategy
- Firestore automatic backups
- Code repository backups
- Configuration backups

Bu rehber ile Yargısal Zeka projesini Google Cloud'a başarıyla deploy edebilirsiniz!

