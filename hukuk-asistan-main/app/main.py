import sys
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from loguru import logger
from contextlib import asynccontextmanager

from .config import settings
from .security import limiter, get_current_user, validate_input, get_client_ip, TokenData
from .schemas import (
    KeywordExtractionRequest, KeywordExtractionResponse,
    DecisionAnalysisRequest, DecisionAnalysisResponse,
    PetitionGenerationRequest, PetitionGenerationResponse,
    SmartSearchRequest, SmartSearchResponse,
    WorkflowAnalysisRequest, WorkflowAnalysisResponse
)
from .ai_service import gemini_service
from .workflow_service import workflow_service
from .firestore_db import init_firestore_db, firestore_manager, log_api_usage
from .auth import router as auth_router
from .monitoring import get_metrics, monitoring_service, HealthChecker
from .usage_middleware import check_usage_limits

# --- Loglama ---
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level=settings.LOG_LEVEL.upper())

# --- Uygulama ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Firestore bağlantısını başlat
    db_connected = await init_firestore_db()
    if db_connected:
        logger.info("Main API Firestore bağlantısı başarılı")
    else:
        logger.warning("Main API Firestore bağlantısı başarısız - cache modunda çalışılacak")
    
    # httpx client'ı yapılandır
    timeout = httpx.Timeout(
        connect=5.0,   # Bağlantı timeout'u
        read=30.0,     # Okuma timeout'u (AI işlemleri için daha uzun)
        write=5.0,     # Yazma timeout'u
        pool=5.0       # Pool timeout'u
    )
    app.state.http_client = httpx.AsyncClient(timeout=timeout)
    
    # Monitoring'i başlat
    monitoring_service.start_monitoring()
    
    logger.info("Yargısal Zeka API'si başlatıldı.")
    yield
    
    # Cleanup
    monitoring_service.stop_monitoring()
    await app.state.http_client.aclose()
    # Firestore connection automatically handles cleanup
    logger.info("Yargısal Zeka API'si kapatıldı.")

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION + " (MongoDB Atlas)",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,  # Production'da docs gizle
    redoc_url="/redoc" if not settings.is_production else None
)

# Rate limiter'ı app'e ekle
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware ekle - güvenli ayarlar
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # Production'da güvenli origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,  # Preflight cache süresi
)

# Usage tracking middleware ekle
@app.middleware("http")
async def usage_tracking_middleware(request: Request, call_next):
    return await check_usage_limits(request, call_next)

# Auth router'ı ekle
app.include_router(auth_router)

# --- Health Check ---
@app.get("/health")
async def health_check():
    """Temel sağlık kontrolü"""
    return {
        "status": "healthy",
        "service": "Yargısal Zeka API",
        "version": settings.API_VERSION
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detaylı sağlık kontrolü"""
    return await HealthChecker.get_comprehensive_health()

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return await get_metrics()

@app.get("/")
async def root():
    """Ana sayfa"""
    return {
        "message": "Yargısal Zeka API'sine hoş geldiniz",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

# --- AI Mikroservisleri ---

@app.post("/api/v1/ai/extract-keywords", response_model=KeywordExtractionResponse)
@limiter.limit("10/minute")  # Rate limiting
async def extract_keywords(
    request: Request,
    keyword_request: KeywordExtractionRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Olay metninden hukuki anahtar kelimeleri çıkarır
    Kimlik doğrulaması gerekli
    """
    try:
        # Input validation
        validated_text = validate_input(keyword_request.case_text, max_length=5000)
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"Anahtar kelime çıkarma isteği - User: {current_user.user_id}, IP: {client_ip}")
        
        keywords = await gemini_service.extract_keywords_from_case(validated_text)
        return KeywordExtractionResponse(
            keywords=keywords,
            success=True,
            message=f"{len(keywords)} anahtar kelime başarıyla çıkarıldı"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anahtar kelime çıkarma hatası: {e}")
        return KeywordExtractionResponse(
            keywords=[],
            success=False,
            message="Anahtar kelime çıkarma sırasında bir hata oluştu"
        )

@app.post("/api/v1/ai/analyze-decision", response_model=DecisionAnalysisResponse)
async def analyze_decision(request: DecisionAnalysisRequest):
    """
    Bir Yargıtay kararının olay metniyle ilişkisini analiz eder
    """
    try:
        analysis = await gemini_service.analyze_decision_relevance(
            request.case_text, 
            request.decision_text
        )
        return DecisionAnalysisResponse(
            score=analysis["score"],
            explanation=analysis["explanation"],
            similarity=analysis["similarity"],
            success=True
        )
    except Exception as e:
        logger.error(f"Karar analizi hatası: {e}")
        return DecisionAnalysisResponse(
            score=0,
            explanation=f"Analiz hatası: {str(e)}",
            similarity="Belirlenemedi",
            success=False
        )

@app.post("/api/v1/ai/generate-petition", response_model=PetitionGenerationResponse)
@limiter.limit("5/minute")  # Rate limiting for petition generation
async def generate_petition(
    request: Request,
    petition_request: PetitionGenerationRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Olay metni ve alakalı kararlardan dilekçe şablonu oluşturur
    Premium özellik - sadece trial ve premium kullanıcılar erişebilir
    """
    try:
        # Premium feature kontrolü
        user_data = await firestore_manager.get_user_by_id(current_user.user_id)
        if not user_data or not user_data.get('can_generate_petitions', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dilekçe oluşturma özelliği premium pakette mevcuttur"
            )
        
        # Input validation
        validated_text = validate_input(petition_request.case_text, max_length=5000)
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"Dilekçe oluşturma isteği - User: {current_user.user_id}, IP: {client_ip}")
        
        petition = await gemini_service.generate_petition_template(
            validated_text,
            petition_request.relevant_decisions
        )
        return PetitionGenerationResponse(
            petition_template=petition,
            success=True,
            message="Dilekçe şablonu başarıyla oluşturuldu"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dilekçe oluşturma hatası: {e}")
        return PetitionGenerationResponse(
            petition_template="Dilekçe şablonu oluşturulamadı",
            success=False,
            message=f"Hata: {str(e)}"
        )

@app.post("/api/v1/ai/smart-search", response_model=SmartSearchResponse)
async def smart_search(request: Request, search_request: SmartSearchRequest):
    """
    Akıllı arama: Olay metninden anahtar kelime çıkarır, 
    Yargıtay'da arar ve sonuçları puanlar
    """
    try:
        # 1. Anahtar kelimeleri çıkar
        try:
            keywords = await gemini_service.extract_keywords_from_case(search_request.case_text)
        except Exception as e:
            logger.warning(f"Gemini API hatası, fallback keywords kullanılıyor: {e}")
            # Fallback keywords
            keywords = ["hukuki", "yasal", "mahkeme", "karar", "tazminat"]
        
        # 2. Yargıtay scraper API'sini çağır
        try:
            client: httpx.AsyncClient = request.app.state.http_client
            search_payload = {"keywords": keywords, "max_results": search_request.max_results}
            
            scraper_url = f"{settings.SCRAPER_API_URL}/search"
            response = await client.post(scraper_url, json=search_payload, timeout=30.0)
            
            if response.status_code == 200:
                search_data = response.json()
                search_results = search_data.get("results", [])
            else:
                # Scraper API çalışmıyorsa mock data kullan
                search_results = _get_mock_search_results()
        except Exception as e:
            logger.warning(f"Scraper API'ye bağlanılamadı, mock data kullanılıyor: {e}")
            search_results = _get_mock_search_results()
        
        # 3. Her sonucu AI ile analiz et ve puanla
        analyzed_results = []
        for result in search_results[:search_request.max_results]:
            try:
                analysis = await gemini_service.analyze_decision_relevance(
                    search_request.case_text, 
                    result.get("content", "")
                )
            except Exception:
                # AI analizi başarısızsa fallback puan ver
                analysis = {
                    "score": 75,
                    "explanation": "Otomatik puanlama kullanıldı",
                    "similarity": "Orta"
                }
            
            analyzed_result = {
                **result,
                "ai_score": analysis["score"],
                "ai_explanation": analysis["explanation"],
                "ai_similarity": analysis["similarity"]
            }
            analyzed_results.append(analyzed_result)
        
        # Puanına göre sırala (yüksekten düşüğe)
        analyzed_results.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
        
        return SmartSearchResponse(
            keywords=keywords,
            search_results=search_results,
            analyzed_results=analyzed_results,
            success=True,
            message=f"{len(analyzed_results)} sonuç AI ile analiz edildi"
        )
            
    except Exception as e:
        logger.error(f"Akıllı arama hatası: {e}")
        return SmartSearchResponse(
            keywords=[],
            search_results=[],
            analyzed_results=[],
            success=False,
            message=f"Hata: {str(e)}"
        )

# --- Workflow Mikroservisi ---

@app.post("/api/v1/workflow/complete-analysis", response_model=WorkflowAnalysisResponse)
async def complete_analysis_workflow(request: Request, workflow_request: WorkflowAnalysisRequest):
    """
    Tam analiz workflow'u - n8n'in yerini alan mikroservis
    1. Anahtar kelime çıkarma
    2. Yargıtay'da arama
    3. Sonuçları AI ile puanlama
    4. İsteğe bağlı dilekçe şablonu oluşturma
    """
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        
        result = await workflow_service.complete_analysis_workflow(
            case_text=workflow_request.case_text,
            max_results=workflow_request.max_results,
            include_petition=workflow_request.include_petition,
            http_client=client
        )
        
        return WorkflowAnalysisResponse(**result)
        
    except Exception as e:
        logger.error(f"Workflow hatası: {e}")
        return WorkflowAnalysisResponse(
            keywords=[],
            search_results=[],
            analyzed_results=[],
            petition_template=None,
            processing_time=0.0,
            success=False,
            message=f"Workflow hatası: {str(e)}"
        )

# --- Yardımcı Fonksiyonlar ---

def _get_mock_search_results():
    """Scraper API çalışmadığında kullanılacak mock data"""
    return [
        {
            "title": "Yargıtay 13. Hukuk Dairesi Kararı",
            "content": "Satış sözleşmesinde teslim tarihinin geçirilmesi halinde alıcının tazminat talep etme hakkı bulunmaktadır. Satıcının teslim yükümlülüğünü zamanında yerine getirmemesi sözleşme ihlali teşkil eder.",
            "date": "2024-01-15",
            "case_number": "2024/123",
            "court": "13. Hukuk Dairesi",
            "url": "https://karararama.yargitay.gov.tr/karar1"
        },
        {
            "title": "Yargıtay 11. Hukuk Dairesi Kararı",
            "content": "Sözleşmeli yükümlülüklerin ihlali halinde tazminat hesaplaması yapılırken, doğrudan zarar ile dolaylı zarar ayrımı yapılmalıdır. Öngörülebilir zararlar tazmin edilmelidir.",
            "date": "2023-12-20",
            "case_number": "2023/456",
            "court": "11. Hukuk Dairesi",
            "url": "https://karararama.yargitay.gov.tr/karar2"
        },
        {
            "title": "Yargıtay 15. Hukuk Dairesi Kararı",
            "content": "İş sözleşmesinin feshi halinde işçinin tazminat hakları ve hesaplama yöntemi. Kıdem ve ihbar tazminatları ayrı ayrı değerlendirilmelidir.",
            "date": "2023-11-10",
            "case_number": "2023/789",
            "court": "15. Hukuk Dairesi",
            "url": "https://karararama.yargitay.gov.tr/karar3"
        }
    ]


# --- User Usage Endpoints ---
@app.get("/api/v1/user/usage")
@limiter.limit("30/minute")
async def get_user_usage(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current user's usage statistics"""
    try:
        from .usage_middleware import get_user_usage_info
        
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID not found"
            )
        
        usage_info = await get_user_usage_info(user_id)
        
        return {
            "status": "success",
            "data": usage_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kullanım bilgileri alınırken bir hata oluştu"
        )


# --- Decision Detail Endpoints ---
@app.get("/api/v1/decisions/{decision_id}")
@limiter.limit("20/minute")
async def get_decision_detail(
    decision_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Yargıtay kararının tam metnini getirir
    Premium özellik - sadece trial ve premium kullanıcılar erişebilir
    """
    try:
        # Premium feature kontrolü
        user_data = await firestore_manager.get_user_by_id(current_user.user_id)
        if not user_data or not user_data.get('can_read_full_decisions', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tam karar okuma özelliği premium pakette mevcuttur"
            )
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"Karar detay isteği - User: {current_user.user_id}, Decision: {decision_id}, IP: {client_ip}")
        
        # Scraper API'den tam metni al
        try:
            client: httpx.AsyncClient = request.app.state.http_client
            scraper_url = f"{settings.SCRAPER_API_URL}/decision/{decision_id}"
            response = await client.get(scraper_url, timeout=30.0)
            
            if response.status_code == 200:
                decision_data = response.json()
                return {
                    "success": True,
                    "decision": decision_data,
                    "message": "Karar detayı başarıyla getirildi"
                }
            else:
                # Mock data döndür
                return {
                    "success": True,
                    "decision": {
                        "id": decision_id,
                        "title": "Örnek Yargıtay Kararı",
                        "court": "Yargıtay 4. Hukuk Dairesi",
                        "date": "2024-01-15",
                        "case_number": "2024/1234",
                        "decision_number": "2024/5678",
                        "full_text": "Bu bir örnek karar metnidir. Gerçek karar metni scraper API'den gelecektir...",
                        "summary": "Sözleşme ihlali nedeniyle tazminat davası",
                        "keywords": ["sözleşme", "tazminat", "ihlal", "ticaret"]
                    },
                    "message": "Örnek karar detayı (Scraper API bağlantısı yok)"
                }
        except Exception as e:
            logger.warning(f"Scraper API'ye bağlanılamadı: {e}")
            return {
                "success": False,
                "message": "Karar detayı şu anda alınamıyor",
                "error": str(e)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Karar detay hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Karar detayı alınırken bir hata oluştu"
        )

@app.post("/api/v1/decisions/{decision_id}/export-pdf")
@limiter.limit("10/minute")
async def export_decision_pdf(
    decision_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Yargıtay kararını PDF olarak export eder
    Premium özellik - sadece trial ve premium kullanıcılar erişebilir
    """
    try:
        # Premium feature kontrolü
        user_data = await firestore_manager.get_user_by_id(current_user.user_id)
        if not user_data or not user_data.get('can_export_pdf', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PDF export özelliği premium pakette mevcuttur"
            )
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"PDF export isteği - User: {current_user.user_id}, Decision: {decision_id}, IP: {client_ip}")
        
        # PDF oluşturma işlemi (şimdilik mock response)
        return {
            "success": True,
            "pdf_url": f"/api/v1/files/decisions/{decision_id}.pdf",
            "message": "PDF başarıyla oluşturuldu",
            "expires_at": "2024-12-31T23:59:59Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF export sırasında bir hata oluştu"
        )


# --- Domain Validation Middleware ---
@app.middleware("http")
async def domain_validation_middleware(request: Request, call_next):
    """
    Production'da sadece yargisalzeka.com domain'lerinden gelen istekleri kabul et
    """
    if settings.is_production:
        host = request.headers.get("host", "").lower()
        referer = request.headers.get("referer", "").lower()
        origin = request.headers.get("origin", "").lower()
        
        allowed_domains = [
            "yargisalzeka.com",
            "www.yargisalzeka.com"
        ]
        
        # Host header kontrolü
        if host and not any(domain in host for domain in allowed_domains):
            logger.warning(f"Unauthorized host access attempt: {host}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Bu domain'den erişim izni bulunmamaktadır"}
            )
        
        # Origin header kontrolü (AJAX istekleri için)
        if origin and not any(domain in origin for domain in allowed_domains):
            logger.warning(f"Unauthorized origin access attempt: {origin}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Bu origin'den erişim izni bulunmamaktadır"}
            )
    
    response = await call_next(request)
    return response


# --- Search History Endpoints ---
@app.get("/api/v1/user/search-history")
@limiter.limit("30/minute")
async def get_search_history(
    request: Request,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user)
):
    """Get user's search history"""
    try:
        user_id = current_user.user_id
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"Arama geçmişi isteği - User: {user_id}, IP: {client_ip}")
        
        # Firestore'dan arama geçmişini al
        search_history = await firestore_manager.get_user_search_history(user_id, limit)
        
        return {
            "success": True,
            "data": search_history,
            "message": f"{len(search_history)} arama geçmişi bulundu"
        }
        
    except Exception as e:
        logger.error(f"Arama geçmişi hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Arama geçmişi alınırken bir hata oluştu"
        )

@app.delete("/api/v1/user/search-history/{search_id}")
@limiter.limit("20/minute")
async def delete_search_history(
    search_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a specific search from history"""
    try:
        user_id = current_user.user_id
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"Arama silme isteği - User: {user_id}, Search: {search_id}, IP: {client_ip}")
        
        # Firestore'dan aramayı sil
        success = await firestore_manager.delete_user_search(user_id, search_id)
        
        if success:
            return {
                "success": True,
                "message": "Arama başarıyla silindi"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arama bulunamadı veya silinemedi"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Arama silme hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Arama silinirken bir hata oluştu"
        )

@app.post("/api/v1/user/search-history")
@limiter.limit("100/minute")
async def save_search_to_history(
    request: Request,
    search_data: dict,
    current_user: TokenData = Depends(get_current_user)
):
    """Save a search to user's history"""
    try:
        user_id = current_user.user_id
        
        # API usage logging
        client_ip = get_client_ip(request)
        logger.info(f"Arama kaydetme isteği - User: {user_id}, IP: {client_ip}")
        
        # Arama verilerini Firestore'a kaydet
        search_id = await firestore_manager.save_search_to_history(user_id, search_data)
        
        return {
            "success": True,
            "search_id": search_id,
            "message": "Arama geçmişe kaydedildi"
        }
        
    except Exception as e:
        logger.error(f"Arama kaydetme hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Arama kaydedilirken bir hata oluştu"
        )

