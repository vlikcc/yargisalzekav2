# /yargitay-scraper-api/app/main.py dosyasının NİHAİ HALİ

import sys
import time
import asyncio
import concurrent.futures

from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette import status
from contextlib import asynccontextmanager

# Yerel importlar
from . import crud, models, schemas
from .database import init_db
from .config import settings
from .search_logic import search_single_keyword

# --- Loglama Yapılandırması ---
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level=settings.LOG_LEVEL.upper())
logger.add("/code/logs/scraper-api.log", level="INFO", rotation="10 MB", retention="7 days", compression="zip")

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

# --- Uygulama Yaşam Döngüsü (veritabanı bağlantısı için) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

# --- FastAPI Uygulaması ---
app = FastAPI(
    title="Yargıtay Scraper API (MongoDB)",
    description="Yargıtay Karar Arama Servisi",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Güvenlik ---
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_current_user(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key is missing")

    user = await crud.get_user_by_api_key(api_key=api_key)
    if not user or not user.is_active or user.subscription_status == "inactive":
        logger.warning(f"Geçersiz, aktif olmayan veya aboneliği bulunmayan API anahtarı denemesi: {api_key}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid, inactive, or unsubscribed API Key")

    return user

# --- API Endpoints ---
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def create_user_endpoint(user: schemas.UserCreate):
    """Yeni bir kullanıcı oluşturur ve API anahtarı atar."""
    db_user = await crud.get_user_by_email(email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
    return await crud.create_user(user=user)

@app.post("/search", response_model=schemas.SearchResponse, tags=["Search"])
@limiter.limit(settings.USER_RATE_LIMIT)
async def search_yargitay_parallel(
    request: Request,
    search_request: schemas.SearchRequest,
    current_user: models.User = Depends(get_current_user)
):
    """Anahtar kelimelerle Yargıtay'da paralel arama yapar."""
    logger.info(f"Kullanıcı '{current_user.email}' tarafından arama başlatıldı.")
    start_time = time.time()
    max_workers = min(len(search_request.keywords), 10)

    all_results = []
    search_details = {}

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            loop.run_in_executor(executor, search_single_keyword, keyword, idx)
            for idx, keyword in enumerate(search_request.keywords)
        ]
        for future in asyncio.as_completed(futures):
            keyword, results, success, message = await future
            all_results.extend(results)
            search_details[keyword] = {"success": success, "count": len(results), "message": message}

    await crud.increment_search_count(user_id=current_user.id)

    elapsed_time = time.time() - start_time
    logger.info(f"Toplam arama süresi: {elapsed_time:.2f} saniye. Sonuç sayısı: {len(all_results)}")

    return schemas.SearchResponse(
        results=all_results, success=True, 
        message=f"Paralel arama {elapsed_time:.2f} saniyede tamamlandı.", 
        search_details=search_details
    )