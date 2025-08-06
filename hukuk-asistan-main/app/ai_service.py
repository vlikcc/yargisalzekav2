"""
Google Gemini AI entegrasyonu için servis modülü
Olay metinlerinden anahtar kelime çıkarma ve karar analizi
"""

import google.generativeai as genai
from typing import List, Dict, Any
from loguru import logger
from .config import settings

class GeminiAIService:
    def __init__(self):
        """Gemini AI servisini başlatır"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    async def extract_keywords_from_case(self, case_text: str) -> List[str]:
        """
        Olay metninden hukuki anahtar kelimeleri çıkarır
        
        Args:
            case_text: Kullanıcının girdiği olay metni
            
        Returns:
            List[str]: Çıkarılan anahtar kelimeler listesi
        """
        try:
            prompt = f"""
            Aşağıdaki hukuki olay metnini analiz et ve Yargıtay kararlarında arama yapmak için 
            en uygun anahtar kelimeleri çıkar. Anahtar kelimeler Türk hukuku terminolojisine uygun olmalı.
            
            Olay metni: {case_text}
            
            Lütfen sadece anahtar kelimeleri virgülle ayırarak listele. Açıklama yapma.
            Örnek format: "tazminat, sözleşme ihlali, maddi zarar, manevi tazminat"
            """
            
            response = self.model.generate_content(prompt)
            keywords_text = response.text.strip()
            
            # Virgülle ayrılmış kelimeleri listeye çevir
            keywords = [keyword.strip() for keyword in keywords_text.split(',')]
            keywords = [k for k in keywords if k]  # Boş stringleri filtrele
            
            logger.info(f"Olay metninden {len(keywords)} anahtar kelime çıkarıldı")
            return keywords
            
        except Exception as e:
            logger.error(f"Anahtar kelime çıkarma hatası: {e}")
            # Hata durumunda basit fallback
            return ["tazminat", "hukuki sorumluluk"]
    
    async def analyze_decision_relevance(self, case_text: str, decision_text: str) -> Dict[str, Any]:
        """
        Bir Yargıtay kararının olay metniyle ilişkisini analiz eder ve puanlar
        
        Args:
            case_text: Kullanıcının olay metni
            decision_text: Yargıtay kararı metni
            
        Returns:
            Dict: Analiz sonucu ve puan
        """
        try:
            prompt = f"""
            Aşağıdaki olay metni ile Yargıtay kararı arasındaki ilişkiyi analiz et:
            
            OLAY METNİ:
            {case_text}
            
            YARGITAY KARARI:
            {decision_text[:2000]}  # İlk 2000 karakter
            
            Lütfen şu formatta yanıt ver:
            PUAN: [0-100 arası sayı]
            AÇIKLAMA: [Kısa açıklama]
            BENZERLIK: [Hangi konularda benzer]
            """
            
            response = self.model.generate_content(prompt)
            analysis_text = response.text.strip()
            
            # Basit parsing
            lines = analysis_text.split('\n')
            score = 50  # Default score
            explanation = "Analiz tamamlandı"
            similarity = "Genel hukuki konular"
            
            for line in lines:
                if line.startswith('PUAN:'):
                    try:
                        score = int(line.split(':')[1].strip())
                    except:
                        pass
                elif line.startswith('AÇIKLAMA:'):
                    explanation = line.split(':', 1)[1].strip()
                elif line.startswith('BENZERLIK:'):
                    similarity = line.split(':', 1)[1].strip()
            
            return {
                "score": max(0, min(100, score)),  # 0-100 arası sınırla
                "explanation": explanation,
                "similarity": similarity
            }
            
        except Exception as e:
            logger.error(f"Karar analizi hatası: {e}")
            return {
                "score": 50,
                "explanation": "Analiz sırasında hata oluştu",
                "similarity": "Belirlenemedi"
            }
    
    async def generate_petition_template(self, case_text: str, relevant_decisions: List[Dict]) -> str:
        """
        Olay metni ve alakalı Yargıtay kararlarından dilekçe şablonu oluşturur
        
        Args:
            case_text: Olay metni
            relevant_decisions: Alakalı Yargıtay kararları listesi
            
        Returns:
            str: Oluşturulan dilekçe şablonu
        """
        try:
            decisions_summary = "\n".join([
                f"- {decision.get('title', 'Başlık yok')}: {decision.get('summary', 'Özet yok')[:200]}"
                for decision in relevant_decisions[:3]  # İlk 3 karar
            ])
            
            prompt = f"""
            Aşağıdaki bilgileri kullanarak hukuki dilekçe şablonu oluştur:
            
            OLAY METNİ:
            {case_text}
            
            ALAKALI YARGITAY KARARLARI:
            {decisions_summary}
            
            Lütfen standart hukuki dilekçe formatında, emsal kararları referans alan 
            bir şablon oluştur. Şablon şu bölümleri içermeli:
            - Başlık
            - Taraflar
            - Olaylar
            - Hukuki Dayanak
            - Emsal Kararlar
            - Talep
            """
            
            response = self.model.generate_content(prompt)
            petition_template = response.text.strip()
            
            logger.info("Dilekçe şablonu başarıyla oluşturuldu")
            return petition_template
            
        except Exception as e:
            logger.error(f"Dilekçe şablonu oluşturma hatası: {e}")
            return """
            DİLEKÇE ŞABLONU
            
            [Bu bölümde dilekçe şablonu yer alacaktır]
            
            Şablon oluşturma sırasında teknik bir hata oluştu.
            Lütfen daha sonra tekrar deneyin.
            """

# Global instance
gemini_service = GeminiAIService()

