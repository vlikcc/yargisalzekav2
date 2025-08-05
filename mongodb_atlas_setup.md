# MongoDB Atlas Kurulum Rehberi

## 🚀 Yargısal Zeka Projesi - MongoDB Atlas Entegrasyonu (18 Collection)

Bu rehber, Yargısal Zeka projesini MongoDB Atlas veritabanı ile çalıştırmak için gerekli adımları açıklar. Proje **18 farklı collection** ile kapsamlı bir database altyapısına sahiptir.

## 📋 Gereksinimler

- MongoDB Atlas hesabı (ücretsiz M0 tier)
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
   # MongoDB Atlas (ZORUNLU)
   MONGODB_CONNECTION_STRING=mongodb+srv://vlikcc:<YOUR_PASSWORD>@yargisalzeka.boxnr1v.mongodb.net/?retryWrites=true&w=majority&appName=yargisalzeka
   MONGODB_DATABASE_NAME=yargisalzeka
   
   # Google Gemini AI (ZORUNLU)
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

## 📊 Database Yapısı (18 Collection)

### 🔑 Core Collections (Temel Sistem)

#### 1. **users** - Kullanıcı Hesapları
- **Alanlar**: user_id, email, password_hash, first_name, last_name
- **Abonelik**: subscription_plan, subscription_start/end, is_active
- **Limitler**: monthly_search_limit, monthly_searches_used
- **Metadata**: created_at, updated_at, last_login

#### 2. **subscriptions** - Abonelik Yönetimi
- **Plan Bilgileri**: subscription_id, user_id, plan (TEMEL/STANDART/PREMIUM)
- **Fiyatlandırma**: monthly_price, currency
- **Özellikler**: search_limit, petition_limit, api_access, priority_support
- **Durum**: is_active, auto_renewal, start_date, end_date

#### 3. **payments** - Ödeme Geçmişi
- **Ödeme**: payment_id, user_id, subscription_id, amount, currency
- **Yöntem**: payment_method, transaction_id
- **Durum**: status (PENDING/COMPLETED/FAILED/REFUNDED)
- **Fatura**: billing_period_start/end, processed_at

### 📝 Content Collections (İçerik Yönetimi)

#### 4. **yargitay_decisions** - Yargıtay Kararları
- **Karar**: decision_id, court, date, number, title, content
- **Kategoriler**: keywords, category
- **Puanlama**: search_score, ai_score
- **Kaynak**: source_url, created_at, updated_at

#### 5. **petition_templates** - Dilekçe Şablonları
- **Şablon**: template_id, user_id, title, category
- **İçerik**: template_content, case_text, referenced_decisions
- **AI**: ai_model, generation_prompt
- **İstatistik**: usage_count, rating_sum, rating_count
- **Durum**: is_public, is_approved

### 🔍 Search & Analysis Collections (Arama ve Analiz)

#### 6. **search_queries** - Arama Sorguları
- **Sorgu**: query_id, user_id, query_text, keywords
- **Sonuçlar**: results_count, results, execution_time
- **Zaman**: created_at

#### 7. **analysis_results** - AI Analiz Sonuçları
- **Analiz**: analysis_id, user_id, case_text, extracted_keywords
- **Sonuçlar**: search_results, scored_results, ai_analysis
- **Çıktı**: petition_template, execution_time

#### 8. **keywords_cache** - Anahtar Kelime Önbelleği
- **Cache**: cache_id, case_text_hash, case_text, extracted_keywords
- **AI**: ai_model, confidence_score
- **Kullanım**: hit_count, last_used, expires_at (30 gün)

#### 9. **search_cache** - Arama Sonuçları Önbelleği
- **Cache**: cache_id, keywords_hash, keywords, search_results
- **Metadata**: total_results, search_duration
- **Kullanım**: hit_count, last_used, expires_at (7 gün)

#### 10. **ai_analysis_cache** - AI Analiz Önbelleği
- **Cache**: cache_id, analysis_hash, case_text, decision_text
- **Sonuç**: ai_score, explanation, similarity, ai_model
- **Kullanım**: hit_count, last_used, expires_at (30 gün)

### 👥 User Management Collections (Kullanıcı Yönetimi)

#### 11. **user_sessions** - Kullanıcı Oturumları
- **Oturum**: session_id, user_id, ip_address, user_agent
- **Veri**: session_data
- **Zaman**: created_at, last_activity, expires_at

#### 12. **user_activities** - Kullanıcı Aktiviteleri
- **Aktivite**: user_id, activity_type, activity_data
- **Konum**: ip_address, user_agent
- **Zaman**: created_at

#### 13. **api_usage** - API Kullanım İstatistikleri
- **İstek**: usage_id, endpoint, method, user_id
- **Boyut**: request_size, response_size
- **Performans**: response_time, status_code
- **Zaman**: created_at

### 🔔 Communication Collections (İletişim)

#### 14. **notifications** - Bildirimler
- **Bildirim**: notification_id, user_id, title, message
- **Tür**: notification_type, priority
- **Kanal**: channels (web/email/sms), is_read, read_at
- **Zamanlama**: scheduled_for, sent_at, expires_at
- **Aksiyon**: action_url, action_text

#### 15. **feedback** - Kullanıcı Geri Bildirimleri
- **Geri Bildirim**: feedback_id, user_id, feedback_type, title, description
- **Değerlendirme**: rating (1-5)
- **Bağlam**: page_url, feature_name, search_query_id
- **Durum**: status (open/in_progress/resolved/closed), priority
- **Yanıt**: admin_response, response_date

### ⚙️ System Collections (Sistem Yönetimi)

#### 16. **system_logs** - Sistem Logları
- **Log**: log_id, level (DEBUG/INFO/WARNING/ERROR/CRITICAL), message
- **Bağlam**: module, function, user_id
- **İstek**: request_id, ip_address, user_agent
- **Hata**: error_type, stack_trace
- **Performans**: execution_time, memory_usage

#### 17. **admin_users** - Admin Kullanıcıları
- **Admin**: admin_id, email, password_hash, first_name, last_name
- **Yetki**: role (super_admin/admin/moderator), permissions
- **Durum**: is_active, is_super_admin
- **Güvenlik**: last_login, failed_login_attempts, locked_until
- **Metadata**: created_at, created_by

#### 18. **system_settings** - Sistem Ayarları
- **Ayar**: setting_id, key, value, category, description
- **Tür**: data_type (string/int/float/bool/json)
- **Doğrulama**: is_required, default_value, validation_rules
- **Erişim**: is_public, requires_restart
- **Versiyon**: version, previous_value, updated_by

## 🎯 Abonelik Planları Detayları

### 💰 Plan Özellikleri

| Özellik | Temel (99₺) | Standart (299₺) | Premium (999₺) |
|---------|-------------|-----------------|----------------|
| Aylık Arama | 50 | 500 | Sınırsız |
| Dilekçe Şablonu | - | 10/ay | Sınırsız |
| AI Analiz | ✅ | ✅ | ✅ |
| Öncelikli Destek | - | ✅ | ✅ |
| API Erişimi | - | - | ✅ |

### 🔄 Otomatik Yönetim
- **Limit Takibi**: Aylık arama sayısı otomatik takip
- **Reset**: Her ay başında limitler sıfırlanır
- **Uyarılar**: Limit dolduğunda bildirim
- **Upgrade**: Plan yükseltme önerileri

## 🔍 Test Etme

### API Health Check
```bash
curl http://localhost:8000/health
```

### Database Stats (18 Collection)
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

### Admin Panel Test
```bash
# Varsayılan admin bilgileri
Email: admin@yargisalzeka.com
Şifre: admin123
```

## 🛠️ Troubleshooting

### MongoDB Bağlantı Sorunları

1. **Connection string kontrolü**:
   ```bash
   # Şifrede özel karakterler varsa URL encode edin
   # Örnek: şifre123! → şifre123%21
   ```

2. **Network erişimi**:
   - IP whitelist'te `0.0.0.0/0` var mı?
   - Firewall ayarları kontrol edin

3. **Credentials**:
   - Kullanıcı adı: `vlikcc`
   - Şifre doğru mu?
   - Database user'ın yetkileri yeterli mi?

### Docker Sorunları

```bash
# Container'ları yeniden başlat
docker-compose down
docker-compose up -d --build

# Logları detaylı incele
docker-compose logs --tail=100 main-api
docker-compose logs --tail=100 scraper-api

# Database bağlantısını test et
docker-compose exec main-api python -c "
import asyncio
from app.database import init_database
asyncio.run(init_database())
"
```

### Collection Oluşturma Kontrolü

```bash
# MongoDB Atlas'ta collection'ları kontrol et
# Compass veya Atlas UI kullanarak:
# 1. yargisalzeka database'ine git
# 2. 18 collection'ın oluştuğunu kontrol et
# 3. Index'lerin oluştuğunu kontrol et
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
MONGODB_CONNECTION_STRING=mongodb+srv://vlikcc:STRONG_PASSWORD@...

# Admin şifresini değiştirin
# Varsayılan: admin123 → Güçlü şifre
```

### Performance
```env
# Connection pool ayarları
MONGODB_MAX_POOL_SIZE=10
MONGODB_MIN_POOL_SIZE=5

# Timeout ayarları
MONGODB_CONNECT_TIMEOUT=5000
MONGODB_SERVER_SELECTION_TIMEOUT=5000

# Cache ayarları
KEYWORDS_CACHE_DURATION=30  # gün
SEARCH_CACHE_DURATION=7     # gün
AI_ANALYSIS_CACHE_DURATION=30  # gün
```

### Monitoring
```env
# Log seviyeleri
LOG_LEVEL=INFO  # Development: DEBUG, Production: INFO

# Sistem ayarları
MAINTENANCE_MODE=false
MAX_SEARCH_RESULTS=50
```

## 🎯 Sonuç

MongoDB Atlas entegrasyonu ile Yargısal Zeka projesi:

### ✅ **18 Collection ile Kapsamlı Altyapı**
- **Core**: Kullanıcı, abonelik, ödeme yönetimi
- **Content**: Yargıtay kararları, dilekçe şablonları
- **Search**: Arama, analiz, cache sistemleri
- **User**: Oturum, aktivite, API kullanım takibi
- **Communication**: Bildirim, geri bildirim sistemleri
- **System**: Log, admin, ayar yönetimi

### ✅ **Enterprise Seviye Özellikler**
- Scalable cloud database
- Otomatik backup ve monitoring
- Global erişim ve yüksek performans
- Ücretsiz tier ile başlangıç
- Production'a hazır altyapı
- Comprehensive indexing ve optimization

### ✅ **Monetization Ready**
- 3 seviyeli abonelik sistemi
- Otomatik limit yönetimi
- Ödeme takibi ve faturalama
- Kullanım istatistikleri

Herhangi bir sorun yaşarsanız loglara bakın ve gerekirse MongoDB Atlas support'a başvurun.

## 📞 Destek

- **Email**: info@yargisalzeka.com
- **GitHub**: https://github.com/vlikcc/yargisalzeka
- **MongoDB Atlas Docs**: https://docs.atlas.mongodb.com/

