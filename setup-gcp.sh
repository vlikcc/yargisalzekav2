#!/bin/bash

# Yargısal Zeka için Google Cloud Setup Script
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Yargısal Zeka - Google Cloud Setup${NC}"
echo "=============================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI bulunamadı!${NC}"
    echo ""
    echo -e "${YELLOW}📥 gcloud CLI Kurulum Seçenekleri:${NC}"
    echo ""
    echo -e "${BLUE}Seçenek 1 - Homebrew (Önerilen):${NC}"
    echo "brew install --cask google-cloud-sdk"
    echo ""
    echo -e "${BLUE}Seçenek 2 - Manuel Kurulum:${NC}"
    echo "curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-456.0.0-darwin-x86_64.tar.gz"
    echo "tar -xf google-cloud-cli-456.0.0-darwin-x86_64.tar.gz"
    echo "./google-cloud-sdk/install.sh"
    echo ""
    echo -e "${BLUE}Seçenek 3 - Package Installer:${NC}"
    echo "https://cloud.google.com/sdk/docs/install-sdk#mac adresinden .pkg dosyasını indirin"
    echo ""
    echo "Kurulum sonrası bu scripti tekrar çalıştırın."
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI bulundu!${NC}"

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo -e "${YELLOW}⚠️  Google Cloud'a giriş yapmanız gerekiyor${NC}"
    echo ""
    read -p "Şimdi giriş yapmak istiyor musunuz? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud auth login
        echo -e "${GREEN}✅ Giriş başarılı!${NC}"
    else
        echo -e "${YELLOW}Manuel giriş için: gcloud auth login${NC}"
        exit 1
    fi
fi

# Get current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)

if [[ -z "$CURRENT_PROJECT" ]]; then
    echo -e "${YELLOW}⚠️  Aktif proje bulunamadı${NC}"
    echo ""
    echo "Mevcut projeleriniz:"
    gcloud projects list --format="table(projectId,name,lifecycleState)"
    echo ""
    read -p "Proje ID'sini girin: " PROJECT_ID
    gcloud config set project $PROJECT_ID
    echo -e "${GREEN}✅ Proje ayarlandı: $PROJECT_ID${NC}"
else
    echo -e "${GREEN}✅ Aktif proje: $CURRENT_PROJECT${NC}"
    PROJECT_ID=$CURRENT_PROJECT
fi

# Set default region
echo -e "${BLUE}🌍 Default region ayarlanıyor...${NC}"
gcloud config set compute/region europe-west1
gcloud config set compute/zone europe-west1-b
gcloud config set run/region europe-west1
echo -e "${GREEN}✅ Region ayarlandı: europe-west1${NC}"

# Enable required APIs
echo -e "${BLUE}🔧 Gerekli API'ler etkinleştiriliyor...${NC}"

REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "cloudfunctions.googleapis.com"
    "firestore.googleapis.com"
    "secretmanager.googleapis.com"
    "storage.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
    "compute.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    echo "  - $api etkinleştiriliyor..."
    gcloud services enable $api --quiet
done

echo -e "${GREEN}✅ Tüm API'ler etkinleştirildi!${NC}"

# Setup application default credentials
echo -e "${BLUE}🔑 Application Default Credentials ayarlanıyor...${NC}"
gcloud auth application-default login
echo -e "${GREEN}✅ Credentials ayarlandı!${NC}"

# Configure Docker for Container Registry
echo -e "${BLUE}🐳 Docker Container Registry için yapılandırılıyor...${NC}"
gcloud auth configure-docker gcr.io --quiet
echo -e "${GREEN}✅ Docker yapılandırıldı!${NC}"

# Create Firestore database if it doesn't exist
echo -e "${BLUE}🔥 Firestore database kontrol ediliyor...${NC}"
if ! gcloud firestore databases describe --database="(default)" >/dev/null 2>&1; then
    echo "Firestore database oluşturuluyor..."
    gcloud firestore databases create --database="(default)" --location=europe-west1 --type=firestore-native
    echo -e "${GREEN}✅ Firestore database oluşturuldu!${NC}"
else
    echo -e "${GREEN}✅ Firestore database mevcut!${NC}"
fi

# Show configuration summary
echo ""
echo -e "${BLUE}📋 Konfigürasyon Özeti:${NC}"
echo "=========================="
echo "Proje ID: $(gcloud config get-value project)"
echo "Hesap: $(gcloud config get-value account)"
echo "Region: $(gcloud config get-value compute/region)"
echo "Zone: $(gcloud config get-value compute/zone)"
echo ""

# Show next steps
echo -e "${GREEN}🎉 Google Cloud setup tamamlandı!${NC}"
echo ""
echo -e "${YELLOW}📝 Sonraki Adımlar:${NC}"
echo "1. Environment variables'ları ayarlayın:"
echo "   export GEMINI_API_KEY=\"your-gemini-api-key\""
echo "   export JWT_SECRET_KEY=\"your-jwt-secret-key\""
echo ""
echo "2. Deployment'ı başlatın:"
echo "   ./gcp/deploy.sh deploy"
echo ""
echo -e "${BLUE}💡 Yardım için: gcloud help${NC}"

