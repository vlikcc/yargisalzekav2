# Yargısal Zeka API

Bu proje, hukuki veri analizi ve yargı kararları için yapay zeka destekli API'ler içermektedir.

## Proje Yapısı

```
yargısalzeka-api/
├── docker-compose.yml
├── hukuk-asistan-main/          # Hukuk asistanı uygulaması
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   └── templates/
│   ├── Dockerfile
│   └── requirements.txt
├── yargitay-scraper-api/        # Yargıtay veri çekme API'si
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── crud.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── search_logic.py
│   ├── Dockerfile
│   ├── logs/
│   └── requirements.txt
└── My workflow.json
```

## Özellikler

### Hukuk Asistanı (hukuk-asistan-main)
- Hukuki sorulara yanıt verme
- Yargı kararları analizi
- Web arayüzü

### Yargıtay Scraper API (yargitay-scraper-api)
- Yargıtay kararlarını çekme
- Veritabanı entegrasyonu
- Arama ve filtreleme özellikleri

## Kurulum

### Docker ile Çalıştırma

```bash
# Tüm servisleri başlat
docker-compose up -d

# Servisleri durdur
docker-compose down
```

### Manuel Kurulum

#### Hukuk Asistanı
```bash
cd hukuk-asistan-main
pip install -r requirements.txt
python app/main.py
```

#### Yargıtay Scraper API
```bash
cd yargitay-scraper-api
pip install -r requirements.txt
python app/main.py
```

## API Endpoints

### Hukuk Asistanı
- `GET /` - Ana sayfa
- `POST /ask` - Hukuki soru sorma

### Yargıtay Scraper API
- `GET /health` - Sağlık kontrolü
- `GET /search` - Karar arama
- `POST /scrape` - Yeni karar çekme

## Geliştirme

Bu proje Python ve FastAPI kullanılarak geliştirilmiştir. Docker containerization ile kolay deployment sağlanmıştır.

## Lisans

Bu proje özel kullanım için geliştirilmiştir. 