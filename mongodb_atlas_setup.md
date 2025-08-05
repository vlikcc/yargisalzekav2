# MongoDB Atlas Kurulum Rehberi

## 🚀 Yargısal Zeka Projesi - MongoDB Atlas Entegrasyonu

Bu rehber, Yargısal Zeka projesini MongoDB Atlas veritabanı ile çalıştırmak için gerekli adımları açıklar.

## 📋 Gereksinimler

- MongoDB Atlas hesabı (ücretsiz)
- Docker ve Docker Compose
- Google Gemini AI API anahtarı

## 🔧 Kurulum Adımları

### 1. MongoDB Atlas Cluster Oluşturma

1. [MongoDB Atlas](https://cloud.mongodb.com/) hesabı oluşturun
2. Yeni bir cluster oluşturun (M0 Sandbox - ücretsiz)
3. Database kullanıcısı oluşturun:
   - Username: `vlikcc`
   - Password: Güçlü bir şifre belirleyin
4. Network Access'te IP whitelist'e `0.0.0.0/0` ekleyin (geliştirme için)

### 2. Connection String Alma

1. Atlas dashboard'da "Connect" butonuna tıklayın
2. "Connect your application" seçeneğini seçin
3. Driver: Node.js, Version: 4.1 or later
4. Connection string'i kopyalayın:
   ```
   mongodb+srv://vlikcc:<password>@yargisalzeka.boxnr1v.mongodb.net/?retryWrites=true&w=majority&appName=yargisalzeka
   ```

### 3. Environment Variables Ayarlama

1. Proje ana dizininde `.env` dosyası oluşturun:
   ```bash
   cp .env.example .env
   ```

2. `.env` dosyasını düzenleyin:
   ```env
   # MongoDB Atlas
   MONGODB_CONNECTION_STRING=mongodb+srv://vlikcc:<YOUR_PASSWORD>@yargisalzeka.boxnr1v.mongodb.net/?retryWrites=true&w=majority&appName=yargisalzeka
   MONGODB_DATABASE_NAME=yargisalzeka
   
   # Google Gemini AI
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Diğer ayarlar
   LOG_LEVEL=INFO
   SCRAPER_API_URL=http://scraper-api:8001
   ```

### 4. Projeyi Çalıştırma

```bash
# Docker container'ları başlat
docker-compose up -d

# Logları kontrol et
docker-compose logs -f main-api
docker-compose logs -f scraper-api
```

## 📊 Database Yapısı

### Collections

1. **yargitay_decisions** - Yargıtay kararları
   - decision_id, court, date, number, title, content
   - keywords, category, search_score, ai_score
   - created_at, updated_at, source_url

2. **search_queries** - Arama sorguları
   - query_id, user_id, query_text, keywords
   - results_count, execution_time, results
   - created_at

3. **user_activities** - Kullanıcı aktiviteleri
   - user_id, activity_type, activity_data
   - ip_address, user_agent, created_at

4. **analysis_results** - AI analiz sonuçları
   - analysis_id, user_id, case_text
   - extracted_keywords, search_results, scored_results
   - ai_analysis, petition_template, execution_time

5. **user_sessions** - Kullanıcı oturumları
   - session_id, user_id, ip_address, user_agent
   - session_data, created_at, last_activity, expires_at

6. **api_usage** - API kullanım istatistikleri
   - usage_id, endpoint, method, user_id
   - ip_address, response_time, status_code
   - request_size, response_size, created_at

## 🔍 Test Etme

### API Health Check
```bash
curl http://localhost:8000/health
```

### Database Stats
```bash
curl http://localhost:8000/api/v1/stats
```

### Smart Search Test
```bash
curl -X POST http://localhost:8000/api/v1/smart-search \
  -H "Content-Type: application/json" \
  -d '{
    "case_text": "Trafik kazası sonucu maddi hasar oluştu",
    "max_results": 5
  }'
```

## 🛠️ Troubleshooting

### MongoDB Bağlantı Sorunları

1. **Connection string kontrolü**:
   - Şifrede özel karakterler varsa URL encode edin
   - Cluster adı doğru mu kontrol edin

2. **Network erişimi**:
   - IP whitelist'te `0.0.0.0/0` var mı?
   - Firewall ayarları kontrol edin

3. **Credentials**:
   - Kullanıcı adı ve şifre doğru mu?
   - Database user'ın yetkileri yeterli mi?

### Docker Sorunları

```bash
# Container'ları yeniden başlat
docker-compose down
docker-compose up -d --build

# Logları detaylı incele
docker-compose logs --tail=100 main-api
docker-compose logs --tail=100 scraper-api
```

### Fallback Mode

MongoDB bağlantısı başarısız olursa, sistem otomatik olarak cache modunda çalışır:
- Veriler memory'de saklanır
- Restart sonrası veriler kaybolur
- Temel işlevsellik korunur

## 📈 Production Ayarları

### Güvenlik
```env
# Production'da spesifik IP'leri whitelist'e ekleyin
# 0.0.0.0/0 yerine gerçek IP adreslerinizi kullanın

# Güçlü şifreler kullanın
# Environment variables'ı güvenli şekilde saklayın
```

### Performance
```env
# Connection pool ayarları
MONGODB_MAX_POOL_SIZE=10
MONGODB_MIN_POOL_SIZE=5

# Timeout ayarları
MONGODB_CONNECT_TIMEOUT=5000
MONGODB_SERVER_SELECTION_TIMEOUT=5000
```

## 🎯 Sonuç

MongoDB Atlas entegrasyonu ile Yargısal Zeka projesi:
- ✅ Scalable cloud database
- ✅ Otomatik backup ve monitoring
- ✅ Global erişim ve yüksek performans
- ✅ Ücretsiz tier ile başlangıç
- ✅ Production'a hazır altyapı

Herhangi bir sorun yaşarsanız loglara bakın ve gerekirse MongoDB Atlas support'a başvurun.

