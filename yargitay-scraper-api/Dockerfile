# Python 3.11 temel imajını kullan
FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /code

# Bağımlılık dosyalarını kopyala
COPY ./requirements.txt /code/requirements.txt

# Bağımlılıkları yükle
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Uygulama kodunu kopyala
COPY ./app /code/app

# Uygulamayı 8001 portunda çalıştır
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]