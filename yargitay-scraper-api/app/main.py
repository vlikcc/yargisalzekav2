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
from .firestore_db import init_firestore, close_firestore, firestore_manager

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
    logger.info("Yargıtay Scraper API başlatıldı")
    
    # Firestore bağlantısını başlat (hata durumunda fallback)
    try:
        db_connected = init_firestore()
        if db_connected:
            logger.info("Firestore bağlantısı başarılı")
        else:
            logger.warning("Firestore bağlantısı başarısız - in-memory cache modunda çalışılacak")
    except Exception as e:
        logger.error(f"Firestore initialization hatası: {e} - fallback mode aktif")
        db_connected = False
    
    yield
    
    # Firestore bağlantısını güvenli şekilde kapat
    try:
        close_firestore()
        logger.info("Firestore bağlantısı kapatıldı")
    except Exception as e:
        logger.warning(f"Firestore kapatma hatası: {e}")
    logger.info("Yargıtay Scraper API kapatıldı")

# --- FastAPI Uygulaması ---
app = FastAPI(
    title="Yargıtay Scraper API",
    description="Yargıtay Karar Arama Servisi (Google Cloud Firestore)",
    version="2.1.0",
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
    
    # Firestore cache kontrolü
    cached_result = None
    if firestore_manager.client:
        try:
            cached_result = await firestore_manager.get_search_cache(search_request.keywords)
            if cached_result:
                logger.info(f"Firestore cache'den sonuç döndürüldü: {len(cached_result['search_results'])} sonuç")
                return schemas.SearchResponse(
                    results=cached_result['search_results'],
                    success=True,
                    message=f"Cache'den döndürüldü. {len(cached_result['search_results'])} sonuç bulundu.",
                    search_details={},
                    processing_time=cached_result.get('search_duration', 0),
                    total_keywords=len(search_request.keywords),
                    unique_results=len(cached_result['search_results'])
                )
        except Exception as e:
            logger.warning(f"Firestore cache kontrolü başarısız: {e}")
    
    # In-memory cache kontrolü (fallback)
    cache_key = generate_cache_key(search_request.keywords)
    if cache_key in search_cache:
        cached_result = search_cache[cache_key]
        logger.info(f"In-memory cache'den sonuç döndürüldü: {len(cached_result['results'])} sonuç")
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
            # ResultItem objesi ise dict'e çevir
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
            elif hasattr(result, 'dict'):
                result_dict = result.dict()
            else:
                result_dict = result
            
            case_number = result_dict.get("case_number", result_dict.get("esas_no", "unknown"))
            if case_number not in unique_results:
                # API uyumluluğu için ek alanlar ekle
                result_dict.update({
                    "case_number": result_dict.get("esas_no", ""),
                    "title": f"{result_dict.get('daire', '')} - {result_dict.get('karar_no', '')}",
                    "content": result_dict.get("karar_metni", ""),
                    "date": result_dict.get("karar_tarihi", ""),
                    "court": result_dict.get("daire", ""),
                    "url": f"https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/#{result_dict.get('esas_no', '')}"
                })
                unique_results[case_number] = result_dict
        
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
        
        # Firestore'a cache kaydet
        if firestore_manager.client and final_results:
            try:
                await firestore_manager.save_search_cache(
                    keywords=search_request.keywords,
                    results=final_results,
                    search_duration=elapsed_time
                )
                logger.info(f"Arama sonuçları Firestore cache'e kaydedildi")
            except Exception as e:
                logger.warning(f"Firestore cache kaydetme başarısız: {e}")
        
        # In-memory cache'e kaydet (fallback)
        if len(search_cache) < 100:
            search_cache[cache_key] = response_data
        
        # Arama sorgusunu logla
        if firestore_manager.client:
            try:
                await firestore_manager.log_search_query(
                    query_text=" ".join(search_request.keywords),
                    keywords=search_request.keywords,
                    results_count=len(final_results),
                    execution_time=elapsed_time
                )
            except Exception as e:
                logger.warning(f"Arama sorgusu loglama başarısız: {e}")
        
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
    stats = {
        "search_stats": search_stats,
        "cache_size": len(search_cache),
        "service_info": {
            "name": "Yargıtay Scraper API",
            "version": "2.1.0",
            "database": "Google Cloud Firestore",
            "rate_limit": settings.USER_RATE_LIMIT
        }
    }
    
    # Firestore istatistikleri ekle
    if firestore_manager.client:
        try:
            firestore_stats = await firestore_manager.get_scraper_stats()
            stats["firestore_stats"] = firestore_stats
        except Exception as e:
            logger.warning(f"Firestore istatistikleri alınamadı: {e}")
            stats["firestore_stats"] = {"error": str(e)}
    
    return stats

@app.delete("/cache", tags=["Cache"])
async def clear_cache():
    """Cache'i temizler"""
    global search_cache
    cache_size = len(search_cache)
    search_cache.clear()
    
    # Firestore cache'i de temizle
    firestore_cleared = 0
    if firestore_manager.client:
        try:
            firestore_cleared = await firestore_manager.cleanup_expired_cache()
            logger.info(f"Firestore cache temizlendi: {firestore_cleared} kayıt")
        except Exception as e:
            logger.warning(f"Firestore cache temizleme başarısız: {e}")
    
    logger.info(f"In-memory cache temizlendi: {cache_size} kayıt silindi")
    return {
        "message": f"Cache başarıyla temizlendi",
        "cleared_entries": {
            "in_memory": cache_size,
            "firestore": firestore_cleared
        }
    }

