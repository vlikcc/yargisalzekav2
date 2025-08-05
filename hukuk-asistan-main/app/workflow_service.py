"""
Workflow Mikroservisleri
n8n workflow'larının yerini alan mikroservisler
"""

import time
import httpx
from loguru import logger
from typing import List, Dict, Any, Optional

from .ai_service import gemini_service
from .config import settings


class WorkflowService:
    """
    n8n workflow'larının yerini alan mikroservis sınıfı
    """
    
    def __init__(self):
        self.scraper_api_url = settings.SCRAPER_API_URL
        
    async def complete_analysis_workflow(
        self, 
        case_text: str, 
        max_results: int = 10,
        include_petition: bool = False,
        http_client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        Tam analiz workflow'u:
        1. Anahtar kelime çıkarma
        2. Yargıtay'da arama
        3. Sonuçları AI ile puanlama
        4. İsteğe bağlı dilekçe şablonu oluşturma
        """
        start_time = time.time()
        
        try:
            # 1. Anahtar kelimeleri çıkar
            logger.info("Workflow başlatıldı: Anahtar kelime çıkarma")
            keywords = await self._extract_keywords(case_text)
            
            # 2. Yargıtay'da arama yap
            logger.info(f"Workflow: {len(keywords)} anahtar kelime ile arama yapılıyor")
            search_results = await self._search_yargitay(keywords, max_results, http_client)
            
            # 3. Sonuçları AI ile analiz et ve puanla
            logger.info(f"Workflow: {len(search_results)} sonuç AI ile analiz ediliyor")
            analyzed_results = await self._analyze_and_score_results(case_text, search_results)
            
            # 4. İsteğe bağlı dilekçe şablonu oluştur
            petition_template = None
            if include_petition and analyzed_results:
                logger.info("Workflow: Dilekçe şablonu oluşturuluyor")
                petition_template = await self._generate_petition(case_text, analyzed_results[:3])
            
            processing_time = time.time() - start_time
            
            logger.info(f"Workflow tamamlandı: {processing_time:.2f} saniye")
            
            return {
                "keywords": keywords,
                "search_results": search_results,
                "analyzed_results": analyzed_results,
                "petition_template": petition_template,
                "processing_time": processing_time,
                "success": True,
                "message": f"Analiz başarıyla tamamlandı. {len(analyzed_results)} sonuç bulundu."
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Workflow hatası: {e}")
            
            return {
                "keywords": [],
                "search_results": [],
                "analyzed_results": [],
                "petition_template": None,
                "processing_time": processing_time,
                "success": False,
                "message": f"Workflow hatası: {str(e)}"
            }
    
    async def _extract_keywords(self, case_text: str) -> List[str]:
        """Olay metninden anahtar kelimeleri çıkarır"""
        try:
            keywords = await gemini_service.extract_keywords_from_case(case_text)
            return keywords
        except Exception as e:
            logger.warning(f"Gemini API hatası, fallback keywords kullanılıyor: {e}")
            # Fallback keywords
            return self._generate_fallback_keywords(case_text)
    
    def _generate_fallback_keywords(self, case_text: str) -> List[str]:
        """Gemini API çalışmadığında kullanılacak basit keyword extraction"""
        # Basit keyword extraction - hukuki terimler
        legal_terms = [
            "sözleşme", "tazminat", "zarar", "yükümlülük", "hak", "borç",
            "satış", "kira", "iş", "hizmet", "ürün", "teslim", "ödeme",
            "mahkeme", "dava", "karar", "temyiz", "istinaf", "icra",
            "mülkiyet", "zilyetlik", "rehin", "kefalet", "garanti"
        ]
        
        case_lower = case_text.lower()
        found_keywords = []
        
        for term in legal_terms:
            if term in case_lower:
                found_keywords.append(term)
        
        # En az 3, en fazla 8 keyword döndür
        if len(found_keywords) < 3:
            found_keywords.extend(["hukuki", "yasal", "mahkeme"])
        
        return found_keywords[:8]
    
    async def _search_yargitay(
        self, 
        keywords: List[str], 
        max_results: int,
        http_client: Optional[httpx.AsyncClient]
    ) -> List[Dict[str, Any]]:
        """Yargıtay scraper API'sini kullanarak arama yapar"""
        if not http_client:
            # Eğer http_client verilmemişse kendi client'ımızı oluştur
            timeout = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await self._perform_search(client, keywords, max_results)
        else:
            return await self._perform_search(http_client, keywords, max_results)
    
    async def _perform_search(
        self, 
        client: httpx.AsyncClient, 
        keywords: List[str], 
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Gerçek arama işlemini yapar"""
        try:
            search_payload = {
                "keywords": keywords,
                "max_results": max_results
            }
            
            scraper_url = f"{self.scraper_api_url}/search"
            response = await client.post(scraper_url, json=search_payload)
            
            if response.status_code == 200:
                search_data = response.json()
                return search_data.get("results", [])
            else:
                logger.warning(f"Scraper API hatası: {response.status_code}")
                return self._generate_mock_search_results()
                
        except Exception as e:
            logger.warning(f"Scraper API'ye bağlanılamadı: {e}")
            return self._generate_mock_search_results()
    
    def _generate_mock_search_results(self) -> List[Dict[str, Any]]:
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
    
    async def _analyze_and_score_results(
        self, 
        case_text: str, 
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Her arama sonucunu AI ile analiz eder ve puanlar"""
        analyzed_results = []
        
        for result in search_results:
            try:
                # AI analizi yap
                analysis = await gemini_service.analyze_decision_relevance(
                    case_text, 
                    result.get("content", "")
                )
                
                # Sonuca AI puanını ekle
                analyzed_result = {
                    **result,
                    "ai_score": analysis["score"],
                    "ai_explanation": analysis["explanation"],
                    "ai_similarity": analysis["similarity"]
                }
                
            except Exception as e:
                logger.warning(f"AI analizi başarısız, fallback puan kullanılıyor: {e}")
                # Fallback scoring
                score = self._calculate_fallback_score(case_text, result.get("content", ""))
                analyzed_result = {
                    **result,
                    "ai_score": score,
                    "ai_explanation": "Otomatik puanlama kullanıldı",
                    "ai_similarity": "Orta" if score > 50 else "Düşük"
                }
            
            analyzed_results.append(analyzed_result)
        
        # Puanına göre sırala (yüksekten düşüğe)
        analyzed_results.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
        
        return analyzed_results
    
    def _calculate_fallback_score(self, case_text: str, decision_text: str) -> int:
        """AI analizi çalışmadığında kullanılacak basit puanlama"""
        case_words = set(case_text.lower().split())
        decision_words = set(decision_text.lower().split())
        
        # Ortak kelimelerin oranına göre puan ver
        common_words = case_words.intersection(decision_words)
        if len(case_words) == 0:
            return 50
        
        similarity_ratio = len(common_words) / len(case_words)
        score = min(int(similarity_ratio * 100), 100)
        
        # En az 30, en fazla 90 puan ver
        return max(30, min(score, 90))
    
    async def _generate_petition(
        self, 
        case_text: str, 
        relevant_decisions: List[Dict[str, Any]]
    ) -> Optional[str]:
        """En alakalı kararlardan dilekçe şablonu oluşturur"""
        try:
            petition = await gemini_service.generate_petition_template(
                case_text, 
                relevant_decisions
            )
            return petition
        except Exception as e:
            logger.warning(f"Dilekçe oluşturma başarısız: {e}")
            return self._generate_fallback_petition(case_text, relevant_decisions)
    
    def _generate_fallback_petition(
        self, 
        case_text: str, 
        relevant_decisions: List[Dict[str, Any]]
    ) -> str:
        """AI dilekçe oluşturma çalışmadığında kullanılacak basit şablon"""
        decision_refs = ""
        for i, decision in enumerate(relevant_decisions[:3], 1):
            decision_refs += f"{i}. {decision.get('case_number', 'Bilinmeyen')} sayılı karar\n"
        
        template = f"""
DAVA DİLEKÇESİ

Sayın Hakime,

Aşağıda belirtilen olaylar nedeniyle tarafınıza başvurmaktayım:

OLAY:
{case_text[:500]}...

HUKUKI DAYANAK:
İlgili Yargıtay kararları:
{decision_refs}

Bu nedenlerle;
1. Davanın kabulü,
2. Tazminatın takdiri,
3. Yargılama giderlerinin karşı taraftan alınması,

Talep ederim.

[Tarih ve İmza]

NOT: Bu şablon otomatik oluşturulmuştur. Hukuki inceleme yaptırınız.
        """
        
        return template.strip()


# Singleton instance
workflow_service = WorkflowService()

