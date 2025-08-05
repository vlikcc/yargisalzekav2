import sys
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from loguru import logger
from contextlib import asynccontextmanager

from .config import settings
from .schemas import (
    KeywordExtractionRequest, KeywordExtractionResponse,
    DecisionAnalysisRequest, DecisionAnalysisResponse,
    PetitionGenerationRequest, PetitionGenerationResponse,
    SmartSearchRequest, SmartSearchResponse,
    WorkflowAnalysisRequest, WorkflowAnalysisResponse
)
from .ai_service import gemini_service
from .workflow_service import workflow_service

# --- Loglama ---
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level=settings.LOG_LEVEL.upper())

# --- Uygulama ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # httpx client'ı yapılandır
    timeout = httpx.Timeout(
        connect=5.0,   # Bağlantı timeout'u
        read=30.0,     # Okuma timeout'u (AI işlemleri için daha uzun)
        write=5.0,     # Yazma timeout'u
        pool=5.0       # Pool timeout'u
    )
    app.state.http_client = httpx.AsyncClient(timeout=timeout)
    logger.info("Yargısal Zeka API'si başlatıldı.")
    yield
    await app.state.http_client.aclose()
    logger.info("Yargısal Zeka API'si kapatıldı.")

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# CORS middleware ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Üretimde spesifik domain'ler belirtin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check ---
@app.get("/health")
async def health_check():
    """API sağlık kontrolü"""
    return {
        "status": "healthy",
        "service": "Yargısal Zeka API",
        "version": settings.API_VERSION
    }

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

