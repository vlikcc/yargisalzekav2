# 🏛️ Yargısal Zeka - Yapay Zeka Destekli Yargıtay Kararı Arama Platformu

## 📋 Proje Hakkında

Yargısal Zeka, avukatların ve hukuk profesyonellerinin Yargıtay kararlarını hızlı ve etkili bir şekilde bulmasını sağlayan yapay zeka destekli bir platformdur.

### 🚀 Ana Özellikler

- **🤖 AI Destekli Anahtar Kelime Çıkarma**: Google Gemini AI ile olay metninizden otomatik anahtar kelime çıkarma
- **⚡ Paralel Arama Teknolojisi**: Çoklu anahtar kelimelerle eş zamanlı arama
- **🎯 Akıllı Puanlama Sistemi**: AI ile kararları olay metninizle ilişkisine göre puanlama
- **📝 Otomatik Dilekçe Şablonu**: En alakalı kararlardan dilekçe şablonu oluşturma
- **🔄 Mikroservis Mimarisi**: Ölçeklenebilir ve modüler yapı

## 🏗️ Sistem Mimarisi

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React         │    │   FastAPI       │    │   Scraper API   │
│   Frontend      │◄──►│   Main API      │◄──►│   (Selenium)    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Google        │
                       │   Gemini AI     │
                       └─────────────────┘
```

## 🛠️ Teknoloji Stack'i

### Backend
- **FastAPI**: Modern, hızlı web framework
- **Google Gemini AI**: Doğal dil işleme ve analiz
- **Selenium**: Web scraping için
- **Pydantic**: Veri validasyonu
- **Loguru**: Gelişmiş loglama

### Frontend
- **React**: Modern UI framework
- **Vite**: Hızlı build tool
- **Tailwind CSS**: Utility-first CSS framework
- **Shadcn/ui**: Modern UI bileşenleri

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

## 🚀 Hızlı Başlangıç

### Ön Gereksinimler
- Docker ve Docker Compose
- Google Gemini AI API Key

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/vlikcc/yargisalzeka.git
cd yargisalzeka
```

### 2. Environment Variables Ayarlayın
```bash
cp .env.example .env
# .env dosyasını düzenleyin ve GEMINI_API_KEY'i ekleyin
```

### 3. Servisleri Başlatın
```bash
docker-compose up -d
```

### 4. Uygulamaya Erişin
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Scraper API**: http://localhost:8001/docs

## 📚 API Endpoints

### AI Mikroservisleri
- `POST /api/v1/ai/extract-keywords` - Anahtar kelime çıkarma
- `POST /api/v1/ai/analyze-decision` - Karar analizi
- `POST /api/v1/ai/generate-petition` - Dilekçe şablonu oluşturma
- `POST /api/v1/ai/smart-search` - Akıllı arama

### Workflow Mikroservisi
- `POST /api/v1/workflow/complete-analysis` - Tam analiz workflow'u

## 🔧 Geliştirme

### Backend Geliştirme
```bash
cd hukuk-asistan-main
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Geliştirme
```bash
cd yargisalzeka-frontend
npm install
npm run dev
```

### Scraper API Geliştirme
```bash
cd yargitay-scraper-api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## 🧪 Test Etme

### API Test
```bash
# Sağlık kontrolü
curl http://localhost:8000/health

# Anahtar kelime çıkarma testi
curl -X POST http://localhost:8000/api/v1/ai/extract-keywords \
  -H "Content-Type: application/json" \
  -d '{"case_text": "Müvekkilim A şirketi ile B şirketi arasında imzalanan satış sözleşmesinde..."}'

# Tam workflow testi
curl -X POST http://localhost:8000/api/v1/workflow/complete-analysis \
  -H "Content-Type: application/json" \
  -d '{"case_text": "Test olay metni", "max_results": 5, "include_petition": true}'
```

## 📦 Deployment

### Docker ile Production
```bash
# Production build
docker-compose up -d

# Logları izleme
docker-compose logs -f
```

## 🔐 Güvenlik

- API key'leri environment variables'da saklayın
- Production'da CORS ayarlarını sınırlandırın
- Rate limiting aktif
- Input validation ile güvenlik

## 📊 Performans

- **Anahtar kelime çıkarma**: ~1-2 saniye
- **Yargıtay arama**: ~5-10 saniye
- **AI analizi**: ~2-3 saniye/karar
- **Tam workflow**: ~10-20 saniye

## 🔄 Changelog

### v2.0.0 (Güncel)
- ✅ n8n bağımlılığı kaldırıldı
- ✅ Mikroservis mimarisi implement edildi
- ✅ Workflow servisi eklendi
- ✅ Performance iyileştirmeleri
- ✅ Docker konfigürasyonu güncellendi

### v1.0.0
- ✅ İlk versiyon
- ✅ Temel AI özellikleri
- ✅ React frontend

## 📞 İletişim

- **Website**: https://yargisalzeka.com
- **GitHub**: https://github.com/vlikcc/yargisalzeka

## 📄 Lisans

Bu proje özel kullanım için geliştirilmiştir. 