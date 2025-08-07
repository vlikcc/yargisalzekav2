# 🚀 Yargısal Zeka - Production Deployment Guide

Bu dokümanda Yargısal Zeka platformunun production ortamına güvenli bir şekilde nasıl deploy edileceği anlatılmaktadır.

## 📋 Production Hazırlık Listesi

### ✅ Güvenlik Gereksinimleri
- [ ] SSL/TLS sertifikaları hazırlandı
- [ ] Güçlü şifreler ve JWT secret'ları ayarlandı
- [ ] MongoDB Atlas production cluster'ı oluşturuldu
- [ ] Firewall kuralları yapılandırıldı
- [ ] Domain ve DNS ayarları tamamlandı
- [ ] Rate limiting ayarları gözden geçirildi

### ✅ Altyapı Gereksinimleri
- [ ] Production sunucusu hazırlandı (min 4 CPU, 8GB RAM)
- [ ] Docker ve Docker Compose kuruldu
- [ ] Monitoring araçları kuruldu
- [ ] Backup stratejisi belirlendi
- [ ] Log yönetimi ayarlandı

### ✅ Konfigürasyon Dosyaları
- [ ] `.env.prod` dosyası oluşturuldu
- [ ] `docker-compose.prod.yml` gözden geçirildi
- [ ] SSL sertifikaları `ssl/` klasörüne yerleştirildi
- [ ] Nginx konfigürasyonu özelleştirildi

## 🔧 Production Deployment

### 1. Sunucu Hazırlığı

```bash
# Gerekli paketleri yükle
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose nginx certbot

# Docker'ı başlat
sudo systemctl start docker
sudo systemctl enable docker

# Kullanıcıyı docker grubuna ekle
sudo usermod -aG docker $USER
```

### 2. SSL Sertifikaları

```bash
# Let's Encrypt ile ücretsiz SSL sertifikası al
sudo certbot certonly --nginx -d yargisalzeka.com -d www.yargisalzeka.com

# Sertifikaları proje klasörüne kopyala
sudo cp /etc/letsencrypt/live/yargisalzeka.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yargisalzeka.com/privkey.pem ssl/
sudo chown $USER:$USER ssl/*.pem
```

### 3. Environment Konfigürasyonu

```bash
# Production environment dosyasını oluştur
cp .env.prod.example .env.prod

# Dosyayı düzenle - ÖNEMLİ: Tüm placeholder değerleri değiştir!
nano .env.prod
```

**Kritik ayarlar:**
- `MONGODB_CONNECTION_STRING`: Production MongoDB Atlas connection string
- `GEMINI_API_KEY`: Production Google Gemini API key
- `JWT_SECRET_KEY`: 32+ karakter güçlü secret key
- `ALLOWED_HOSTS`: Production domain'leri
- `CORS_ORIGINS`: HTTPS domain'leri

### 4. Deployment

```bash
# Deployment script'ini çalıştır
./scripts/deploy.sh

# Veya manuel deployment
docker-compose -f docker-compose.prod.yml up -d --build
```

### 5. Health Check

```bash
# Servislerin durumunu kontrol et
curl https://yargisalzeka.com/health
curl https://api.yargisalzeka.com/health/detailed

# Monitoring dashboard'a erişim
# https://monitoring.yargisalzeka.com (Grafana)
```

## 🔒 Güvenlik Konfigürasyonu

### Firewall Ayarları

```bash
# UFW firewall'ı etkinleştir
sudo ufw enable

# Gerekli portları aç
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Gereksiz portları kapat
sudo ufw deny 8000/tcp   # Direct API access
sudo ufw deny 8001/tcp   # Direct Scraper access
```

### MongoDB Atlas Güvenlik

1. **Network Access**: Sadece production sunucu IP'sini whitelist'e ekle
2. **Database User**: Production için ayrı kullanıcı oluştur
3. **Backup**: Otomatik backup'ları etkinleştir
4. **Monitoring**: Atlas monitoring'i aktifleştir

### Rate Limiting

Production ortamında varsayılan rate limiting ayarları:
- API endpoints: 100 req/hour per IP
- Authentication: 5 req/minute per IP
- AI operations: 10 req/minute per user

## 📊 Monitoring ve Logging

### Prometheus Metrics

Metrics endpoint: `https://api.yargisalzeka.com/metrics`

Önemli metrikler:
- `http_requests_total`: Toplam HTTP istekleri
- `http_request_duration_seconds`: İstek süreleri
- `ai_requests_total`: AI servis istekleri
- `database_operations_total`: Database operasyonları

### Grafana Dashboards

1. **System Overview**: CPU, Memory, Disk kullanımı
2. **API Performance**: Response times, error rates
3. **Business Metrics**: User activity, AI usage
4. **Security**: Failed logins, rate limit hits

### Log Management

```bash
# Log dosyalarını görüntüle
docker-compose -f docker-compose.prod.yml logs -f main-api
docker-compose -f docker-compose.prod.yml logs -f scraper-api

# Log dosyaları lokasyonu
/var/log/yargisalzeka/
├── deploy.log
├── backup.log
├── main-api/
└── scraper-api/
```

## 🔄 Backup ve Recovery

### Otomatik Backup

```bash
# Crontab'a backup job'u ekle
crontab -e

# Her gece saat 02:00'de backup al
0 2 * * * /path/to/yargisalzeka/scripts/backup.sh backup
```

### Manuel Backup

```bash
# Full backup oluştur
./scripts/backup.sh backup

# Backup'ı doğrula
./scripts/backup.sh verify /backups/backup_20241215_020000.tar.gz
```

### Recovery

```bash
# Backup'tan geri yükle
./scripts/backup.sh restore /backups/backup_20241215_020000.tar.gz

# Servisleri yeniden başlat
docker-compose -f docker-compose.prod.yml restart
```

## 🚨 Incident Response

### Acil Durum Prosedürleri

1. **Service Down**
   ```bash
   # Health check yap
   ./scripts/deploy.sh health-check
   
   # Logları kontrol et
   docker-compose -f docker-compose.prod.yml logs --tail=100
   
   # Gerekirse rollback yap
   ./scripts/deploy.sh rollback
   ```

2. **Database Issues**
   ```bash
   # Database connectivity test
   docker-compose -f docker-compose.prod.yml exec main-api python -c "
   import asyncio
   from app.database import init_database
   result = asyncio.run(init_database())
   print('DB OK' if result else 'DB ERROR')
   "
   ```

3. **High CPU/Memory**
   ```bash
   # Container resource usage
   docker stats
   
   # Scale services if needed
   docker-compose -f docker-compose.prod.yml up -d --scale chrome-node=4
   ```

### Alert Thresholds

- **Critical**: API down, DB connection lost, SSL certificate expired
- **Warning**: High response time (>2s), High error rate (>5%), High memory usage (>80%)
- **Info**: Deployment completed, Backup completed

## 🔧 Maintenance

### Rutin Bakım Görevleri

**Günlük:**
- [ ] Health check sonuçlarını gözden geçir
- [ ] Error log'larını kontrol et
- [ ] Disk kullanımını kontrol et

**Haftalık:**
- [ ] Backup'ları doğrula
- [ ] Security log'larını gözden geçir
- [ ] Performance metriklerini analiz et
- [ ] SSL sertifika süresini kontrol et

**Aylık:**
- [ ] Dependencies'i güncelle
- [ ] Security scan yap
- [ ] Capacity planning yap
- [ ] Disaster recovery test yap

### Güncelleme Prosedürü

```bash
# 1. Backup al
./scripts/backup.sh backup

# 2. Yeni versiyonu test et (staging'de)

# 3. Production'a deploy et
git pull origin main
./scripts/deploy.sh

# 4. Health check yap
./scripts/deploy.sh health-check

# 5. Monitoring'i kontrol et
```

## 📞 Destek ve İletişim

### Acil Durum İletişimi
- **System Admin**: [admin@yargisalzeka.com]
- **DevOps Team**: [devops@yargisalzeka.com]
- **On-call**: [+90-XXX-XXX-XXXX]

### Monitoring Dashboards
- **Grafana**: https://monitoring.yargisalzeka.com
- **Prometheus**: https://prometheus.yargisalzeka.com
- **Logs**: https://logs.yargisalzeka.com

### Documentation
- **API Docs**: https://api.yargisalzeka.com/docs
- **Architecture**: [ARCHITECTURE.md]
- **Security**: [SECURITY.md]

---

## ⚠️ Önemli Notlar

1. **Asla production'da debug mode açmayın**
2. **Tüm secret'ları güvenli saklayın**
3. **Regular backup alın ve test edin**
4. **Monitoring'i sürekli takip edin**
5. **Security güncellemelerini kaçırmayın**

Bu dokümandaki adımları takip ederek Yargısal Zeka platformunu güvenli ve stabil bir şekilde production'da çalıştırabilirsiniz.