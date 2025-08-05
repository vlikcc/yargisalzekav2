# /yargitay-scraper-api/app/main.py dosyasının NİHAİ HALİ (MongoDB'siz)

import sys
import time
import asyncio
import concurrent.futures
import hashlib

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette import status
from contextlib import asynccontextmanager

# Yerel importlar
from . import schemas
from .config import settings
from .search_logic import search_single_keyword

# --- Loglama Yapılandırması ---
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level=settings.LOG_LEVEL.upper())

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

# --- In-memory cache for search results ---
search_cache = {}
search_stats = {"total_searches": 0, "total_results": 0}

# --- Uygulama Yaşam Döngüsü ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Yargıtay Scraper API başlatıldı (MongoDB'siz)")
    yield
    logger.info("Yargıtay Scraper API kapatıldı")

# --- FastAPI Uygulaması ---
app = FastAPI(
    title="Yargıtay Scraper API",
    description="Yargıtay Karar Arama Servisi (MongoDB'siz)",
    version="2.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Helper Functions ---
def generate_cache_key(keywords):
    """Anahtar kelimelerden cache key oluşturur"""
    keywords_str = ",".join(sorted(keywords))
    return hashlib.md5(keywords_str.encode()).hexdigest()

# --- API Endpoints ---

@app.get("/health", tags=["Health"])
async def health_check():
    """API sağlık kontrolü"""
    return {
        "status": "healthy",
        "service": "Yargıtay Scraper API",
        "version": "2.0.0",
        "stats": search_stats
    }

@app.get("/", tags=["Root"])
async def root():
    """Ana sayfa"""
    return {
        "message": "Yargıtay Scraper API'sine hoş geldiniz",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "search": "/search",
            "docs": "/docs"
        }
    }

@app.post("/search", response_model=schemas.SearchResponse, tags=["Search"])
@limiter.limit(settings.USER_RATE_LIMIT)
async def search_yargitay_parallel(
    request: Request,
    search_request: schemas.SearchRequest
):
    """Anahtar kelimelerle Yargıtay'da paralel arama yapar."""
    logger.info(f"Arama başlatıldı: {len(search_request.keywords)} anahtar kelime")
    start_time = time.time()
    
    # Cache kontrolü
    cache_key = generate_cache_key(search_request.keywords)
    if cache_key in search_cache:
        cached_result = search_cache[cache_key]
        logger.info(f"Cache'den sonuç döndürüldü: {len(cached_result['results'])} sonuç")
        return schemas.SearchResponse(**cached_result)
    
    max_workers = min(len(search_request.keywords), 10)
    all_results = []
    search_details = {}

    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                loop.run_in_executor(executor, search_single_keyword, keyword, idx)
                for idx, keyword in enumerate(search_request.keywords)
            ]
            for future in asyncio.as_completed(futures):
                keyword, results, success, message = await future
                all_results.extend(results)
                search_details[keyword] = {
                    "success": success, 
                    "count": len(results), 
                    "message": message
                }

        # Sonuçları unique hale getir (aynı case_number'a sahip olanları birleştir)
        unique_results = {}
        for result in all_results:
            case_number = result.get("case_number", "unknown")
            if case_number not in unique_results:
                unique_results[case_number] = result
        
        final_results = list(unique_results.values())
        
        # İstatistikleri güncelle
        search_stats["total_searches"] += 1
        search_stats["total_results"] += len(final_results)

        elapsed_time = time.time() - start_time
        logger.info(f"Toplam arama süresi: {elapsed_time:.2f} saniye. Sonuç sayısı: {len(final_results)}")

        response_data = {
            "results": final_results,
            "success": True,
            "message": f"Paralel arama {elapsed_time:.2f} saniyede tamamlandı. {len(final_results)} unique sonuç bulundu.",
            "search_details": search_details,
            "processing_time": elapsed_time,
            "total_keywords": len(search_request.keywords),
            "unique_results": len(final_results)
        }
        
        # Cache'e kaydet (en fazla 100 arama sonucu cache'de tutalım)
        if len(search_cache) < 100:
            search_cache[cache_key] = response_data
        
        return schemas.SearchResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Arama hatası: {str(e)}")
        return schemas.SearchResponse(
            results=[],
            success=False,
            message=f"Arama sırasında hata oluştu: {str(e)}",
            search_details={},
            processing_time=time.time() - start_time,
            total_keywords=len(search_request.keywords),
            unique_results=0
        )

@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """API istatistiklerini döndürür"""
    return {
        "search_stats": search_stats,
        "cache_size": len(search_cache),
        "service_info": {
            "name": "Yargıtay Scraper API",
            "version": "2.0.0",
            "database": "In-Memory Cache",
            "rate_limit": settings.USER_RATE_LIMIT
        }
    }

@app.delete("/cache", tags=["Cache"])
async def clear_cache():
    """Cache'i temizler"""
    global search_cache
    cache_size = len(search_cache)
    search_cache.clear()
    logger.info(f"Cache temizlendi: {cache_size} kayıt silindi")
    return {
        "message": f"Cache başarıyla temizlendi",
        "cleared_entries": cache_size
    }

