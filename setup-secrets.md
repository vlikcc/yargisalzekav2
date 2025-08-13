# GitHub Secrets ve Google Cloud Setup Rehberi

## 🔐 GitHub Repository Secrets Kurulumu

### 1. GitHub Repository'ye Git
- GitHub'da `vlikcc/yargisalzeka` repository'sine git
- **Settings** > **Secrets and variables** > **Actions** sekmesine tıkla

### 2. Gerekli Secrets'ları Ekle

#### Google Cloud Secrets
```
GCP_PROJECT_ID
Değer: yargisalzeka-prod (veya seçtiğiniz proje ID'si)

GCP_SA_KEY
Değer: Service Account JSON key (aşağıda nasıl oluşturulacağı açıklanmış)

GCP_HASH
Değer: Cloud Run URL'indeki hash (örn: abc123def456)
```

#### API Keys
```
GEMINI_API_KEY
Değer: Google Gemini API anahtarınız

JWT_SECRET_KEY
Değer: Güçlü bir secret key (örn: openssl rand -base64 32)
```

## 🔧 Google Cloud Service Account Oluşturma

### 1. Google Cloud Console'a Git
```bash
# Terminal'de giriş yap
gcloud auth login

# Proje oluştur (eğer yoksa)
gcloud projects create yargisalzeka-prod --name="Yargısal Zeka"
gcloud config set project yargisalzeka-prod

# Gerekli API'leri etkinleştir
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Service Account Oluştur
```bash
# Service account oluştur
gcloud iam service-accounts create github-actions \
    --description="GitHub Actions deployment service account" \
    --display-name="GitHub Actions"

# Gerekli rolleri ver
gcloud projects add-iam-policy-binding yargisalzeka-prod \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding yargisalzeka-prod \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding yargisalzeka-prod \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding yargisalzeka-prod \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# JSON key oluştur
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions@yargisalzeka-prod.iam.gserviceaccount.com
```

### 3. JSON Key'i GitHub'a Ekle
```bash
# JSON dosyasının içeriğini kopyala
cat github-actions-key.json
```
Bu çıktıyı `GCP_SA_KEY` secret'ına yapıştır.

## 🔒 Google Cloud Secret Manager Setup

### 1. Secrets Oluştur
```bash
# Gemini API Key
echo -n "YOUR_ACTUAL_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# JWT Secret Key
openssl rand -base64 32 | gcloud secrets create jwt-secret-key --data-file=-

# GCP Project ID
echo -n "yargisalzeka-prod" | gcloud secrets create gcp-project-id --data-file=-
```

### 2. Secret Access Permissions
```bash
# GitHub Actions service account'a secret erişimi ver
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding jwt-secret-key \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gcp-project-id \
    --member="serviceAccount:github-actions@yargisalzeka-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## 🗄️ Firestore Database Setup

### 1. Firestore Database Oluştur
```bash
# Firestore Native mode'da database oluştur
gcloud firestore databases create --region=europe-west1
```

### 2. Firestore Security Rules
```javascript
// Google Cloud Console > Firestore > Rules sekmesinde bu kuralları ekle:
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users collection - sadece kendi verilerine erişim
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Search history - sadece kendi arama geçmişine erişim
    match /search_history/{searchId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Analysis results - sadece kendi analiz sonuçlarına erişim
    match /analysis_results/{resultId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Public read access for some collections (if needed)
    match /public_data/{document} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

## 🚀 İlk Deployment

### 1. Kodu GitHub'a Push Et
```bash
cd yargisalzeka-updated
git add .
git commit -m "feat: Add CI/CD pipeline and production setup"
git push origin main
```

### 2. GitHub Actions'ı İzle
- GitHub repository'de **Actions** sekmesine git
- Workflow'un çalışmasını izle
- Hata varsa logs'ları kontrol et

### 3. Deployment Sonrası Kontroller
```bash
# Cloud Run services'ları kontrol et
gcloud run services list --region=europe-west1

# URL'leri al
gcloud run services describe yargisalzeka-frontend --region=europe-west1 --format='value(status.url)'
gcloud run services describe yargisalzeka-backend --region=europe-west1 --format='value(status.url)'
```

## 🌐 Custom Domain Setup (Opsiyonel)

### 1. Domain Mapping
```bash
# Frontend için domain mapping
gcloud run domain-mappings create \
  --service yargisalzeka-frontend \
  --domain yargisalzeka.com \
  --region europe-west1

# Backend için subdomain
gcloud run domain-mappings create \
  --service yargisalzeka-backend \
  --domain api.yargisalzeka.com \
  --region europe-west1
```

### 2. DNS Ayarları
Domain sağlayıcınızda şu kayıtları ekleyin:
```
A Record: yargisalzeka.com -> [Cloud Run IP]
CNAME: www.yargisalzeka.com -> yargisalzeka.com
CNAME: api.yargisalzeka.com -> [Backend Cloud Run URL]
```

## 🔍 Troubleshooting

### Common Issues

1. **Service Account Permissions**
   ```bash
   # Tüm gerekli rolleri kontrol et
   gcloud projects get-iam-policy yargisalzeka-prod
   ```

2. **Secret Access Issues**
   ```bash
   # Secret'ların varlığını kontrol et
   gcloud secrets list
   ```

3. **Docker Build Failures**
   ```bash
   # Local'de test et
   docker build -t test-image ./hukuk-asistan-main
   ```

4. **Cloud Run Deployment Issues**
   ```bash
   # Logs'ları kontrol et
   gcloud run services logs read yargisalzeka-backend --region=europe-west1
   ```

## ✅ Kurulum Tamamlandı!

Bu adımları tamamladıktan sonra:
- Her `main` branch'e push'ta otomatik deployment
- Test'ler otomatik çalışacak
- Production'da güvenli secret management
- Monitoring ve logging aktif

🎉 **Artık CI/CD pipeline'ınız hazır!**

