import sys
import uuid
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.templating import Jinja2Templates

from loguru import logger
from contextlib import asynccontextmanager

from .config import settings
from .schemas import (
    AnalysisRequest, AnalysisResponse, N8NResultRequest,
    KeywordExtractionRequest, KeywordExtractionResponse,
    DecisionAnalysisRequest, DecisionAnalysisResponse,
    PetitionGenerationRequest, PetitionGenerationResponse,
    SmartSearchRequest, SmartSearchResponse
)
from .ai_service import gemini_service

# --- Loglama ---
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level=settings.LOG_LEVEL.upper())

# --- Uygulama ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # httpx client'ı kısa timeout'larla yapılandır
    timeout = httpx.Timeout(
        connect=5.0,   # Bağlantı timeout'u
        read=15.0,     # Okuma timeout'u (immediate response için yeterli)
        write=5.0,     # Yazma timeout'u
        pool=5.0       # Pool timeout'u
    )
    app.state.http_client = httpx.AsyncClient(timeout=timeout)
    logger.info("Ana Ürün API'si başlatıldı.")
    yield
    await app.state.http_client.aclose()
    logger.info("Ana Ürün API'si kapatıldı.")

# --- Şablon Motorunu Yapılandır ---
templates = Jinja2Templates(directory="app/templates")
app = FastAPI(
    title="Hukuki Analiz Asistanı - Ana API",
    version="1.0.0",
    lifespan=lifespan
)

# Geçici olarak sonuçları bellekte saklayalım (normalde veritabanı olur)
analysis_results_db = {}

# --- Favicon endpoint'i (404 hatasını önler) ---
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)  # No Content

# --- Kök Dizine Gelen İstekleri Karşılar ---
@app.get("/")
async def read_root(request: Request):
    """
    Ana HTML sayfasını kullanıcıya sunar.
    """
    return templates.TemplateResponse("index.html", {"request": request})

# --- Test Endpoints ---
@app.get("/api/v1/test/n8n")
async def test_n8n_connection(request: Request):
    """
    N8n bağlantısını test eder
    """
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        
        # Test payload
        test_payload = {
            "userCase": "test case",
            "transactionId": "test-123"
        }
        test_headers = {
            "X-N8N-Auth-Secret": settings.N8N_AUTH_SECRET,
            "Content-Type": "application/json"
        }
        
        response = await client.post(
            settings.N8N_WEBHOOK_URL,
            json=test_payload,
            headers=test_headers
        )
        
        return {
            "status": "success",
            "n8n_status_code": response.status_code,
            "n8n_response": response.text[:500],
            "url": settings.N8N_WEBHOOK_URL
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "url": settings.N8N_WEBHOOK_URL
        }

# --- API Endpoints ---
@app.post("/api/v1/analysis", response_model=AnalysisResponse)
async def start_analysis(request: Request, analysis_req: AnalysisRequest):
    """
    Kullanıcıdan gelen isteği alır, n8n iş akışını tetikler.
    Fire and Forget yaklaşımı - n8n'i tetikler ve hemen yanıt döner.
    """
    transaction_id = uuid.uuid4()
    logger.info(f"Yeni analiz isteği alındı. Transaction ID: {transaction_id}")

    # Sonucu belleğe "bekleniyor" olarak kaydet (n8n çağrısından önce)
    analysis_results_db[transaction_id] = {"status": "pending", "result": None}

    # n8n Webhook'unu tetiklemek için hazırlan
    n8n_payload = {
        "userCase": analysis_req.user_case_description,
        "transactionId": str(transaction_id)
    }
    n8n_headers = {
        "X-N8N-Auth-Secret": settings.N8N_AUTH_SECRET,
        "Content-Type": "application/json"
    }

    try:
        client: httpx.AsyncClient = request.app.state.http_client
        
        # Asenkron olarak n8n'i tetikle - yanıtını bekleme (background task)
        import asyncio
        
        async def trigger_n8n():
            try:
                response = await client.post(
                    settings.N8N_WEBHOOK_URL,
                    json=n8n_payload,
                    headers=n8n_headers
                )
                logger.info(f"n8n tetiklendi. Status: {response.status_code}, Transaction ID: {transaction_id}")
            except Exception as e:
                logger.error(f"n8n tetikleme hatası: {e}, Transaction ID: {transaction_id}")
                analysis_results_db[transaction_id] = {
                    "status": "failed", 
                    "result": None,
                    "error": f"N8n tetikleme hatası: {str(e)}"
                }
        
        # Background task olarak başlat
        asyncio.create_task(trigger_n8n())
        
        # Hemen yanıt döndür
        logger.info(f"n8n tetikleme işlemi background'da başlatıldı. Transaction ID: {transaction_id}")
            
    except Exception as e:
        logger.error(f"Genel hata: {e} - Transaction ID: {transaction_id}")
        analysis_results_db[transaction_id] = {
            "status": "failed", 
            "result": None,
            "error": str(e)
        }
        # Bu durumda bile işlemi devam ettir - background task çalışabilir
        logger.warning(f"Hata olmasına rağmen transaction kaydedildi: {transaction_id}")

    return AnalysisResponse(
        message="Analiz başarıyla başlatıldı. Sonuçlar hazır olduğunda bu transaction ID ile sorgulayabilirsiniz.",
        transaction_id=transaction_id
    )


@app.post("/api/v1/analysis/result")
async def receive_analysis_result(
    result_req: N8NResultRequest,
    x_n8n_auth_secret: str = Header(...)
):
    """
    N8n iş akışından gelen nihai sonucu kabul eder.
    Sadece n8n'in bildiği gizli anahtar ile erişilebilir.
    """
    if x_n8n_auth_secret != settings.N8N_AUTH_SECRET:
        logger.warning("Yetkisiz bir n8n sonuç isteği denemesi yapıldı.")
        raise HTTPException(status_code=403, detail="Invalid credentials")

    transaction_id = result_req.transaction_id
    logger.info(f"n8n'den sonuç alındı. Transaction ID: {transaction_id}")

    if transaction_id not in analysis_results_db:
        logger.error(f"Bilinmeyen bir transaction ID için sonuç geldi: {transaction_id}")
        raise HTTPException(status_code=404, detail="Transaction ID not found")

    # Sonucu bellekteki kayda işle
    analysis_results_db[transaction_id] = {
        "status": "completed",
        "result": result_req.analysis_result
    }

    logger.info(f"Transaction {transaction_id} başarıyla tamamlandı ve kaydedildi.")
    return Response(status_code=200, content="Result received successfully.")


@app.get("/api/v1/analysis/{transaction_id}")
async def get_analysis_status(transaction_id: uuid.UUID):
    """
    Belirli bir analizin durumunu ve sonucunu sorgular.
    """
    result = analysis_results_db.get(transaction_id)
    if not result:
        raise HTTPException(status_code=404, detail="Transaction ID not found")
    
    logger.info(f"Transaction {transaction_id} durumu sorgulandı: {result['status']}")
    return result

# --- AI Özellikleri Endpoints ---

@app.post("/api/v1/ai/extract-keywords", response_model=KeywordExtractionResponse)
async def extract_keywords(request: KeywordExtractionRequest):
    """
    Olay metninden hukuki anahtar kelimeleri çıkarır
    """
    try:
        keywords = await gemini_service.extract_keywords_from_case(request.case_text)
        return KeywordExtractionResponse(
            keywords=keywords,
            success=True,
            message=f"{len(keywords)} anahtar kelime başarıyla çıkarıldı"
        )
    except Exception as e:
        logger.error(f"Anahtar kelime çıkarma hatası: {e}")
        return KeywordExtractionResponse(
            keywords=[],
            success=False,
            message=f"Hata: {str(e)}"
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
async def generate_petition(request: PetitionGenerationRequest):
    """
    Olay metni ve alakalı kararlardan dilekçe şablonu oluşturur
    """
    try:
        petition = await gemini_service.generate_petition_template(
            request.case_text,
            request.relevant_decisions
        )
        return PetitionGenerationResponse(
            petition_template=petition,
            success=True,
            message="Dilekçe şablonu başarıyla oluşturuldu"
        )
    except Exception as e:
        logger.error(f"Dilekçe oluşturma hatası: {e}")
        return PetitionGenerationResponse(
            petition_template="Dilekçe şablonu oluşturulamadı",
            success=False,
            message=f"Hata: {str(e)}"
        )

@app.post("/api/v1/ai/smart-search", response_model=SmartSearchResponse)
async def smart_search(request: SmartSearchRequest):
    """
    Akıllı arama: Olay metninden anahtar kelime çıkarır, 
    Yargıtay'da arar ve sonuçları puanlar
    """
    try:
        # 1. Anahtar kelimeleri çıkar
        keywords = await gemini_service.extract_keywords_from_case(request.case_text)
        
        # 2. Yargıtay scraper API'sini çağır
        client: httpx.AsyncClient = request.app.state.http_client
        search_payload = {"keywords": keywords}
        
        # Yargıtay scraper API endpoint'i (docker-compose'daki servis adı)
        scraper_url = "http://yargitay-scraper-api:8001/search"
        
        response = await client.post(scraper_url, json=search_payload)
        
        if response.status_code == 200:
            search_data = response.json()
            search_results = search_data.get("results", [])
            
            # 3. Her sonucu AI ile analiz et ve puanla
            analyzed_results = []
            for result in search_results[:request.max_results]:
                analysis = await gemini_service.analyze_decision_relevance(
                    request.case_text,
                    result.get("content", "")
                )
                
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
        else:
            return SmartSearchResponse(
                keywords=keywords,
                search_results=[],
                analyzed_results=[],
                success=False,
                message="Yargıtay arama servisi hatası"
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

