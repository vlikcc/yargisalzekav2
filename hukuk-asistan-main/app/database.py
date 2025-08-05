"""
MongoDB Atlas Database Configuration for Main API
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class AnalysisResult(Document):
    """AI Analiz Sonuçları MongoDB Modeli"""
    
    analysis_id: str = Field(..., description="Analiz ID")
    user_id: Optional[str] = Field(None, description="Kullanıcı ID")
    case_text: str = Field(..., description="Olay metni")
    extracted_keywords: List[str] = Field(default=[], description="Çıkarılan anahtar kelimeler")
    
    # Search results
    search_results: List[Dict[str, Any]] = Field(default=[], description="Arama sonuçları")
    scored_results: List[Dict[str, Any]] = Field(default=[], description="Puanlanmış sonuçlar")
    
    # AI Analysis
    ai_analysis: Optional[Dict[str, Any]] = Field(None, description="AI analiz detayları")
    petition_template: Optional[str] = Field(None, description="Dilekçe şablonu")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time: Optional[float] = Field(None, description="Toplam çalışma süresi")
    
    class Settings:
        name = "analysis_results"
        indexes = [
            "analysis_id",
            "user_id",
            "created_at",
            [("case_text", "text")]
        ]


class UserSession(Document):
    """Kullanıcı Oturumları MongoDB Modeli"""
    
    session_id: str = Field(..., description="Oturum ID")
    user_id: Optional[str] = Field(None, description="Kullanıcı ID")
    ip_address: str = Field(..., description="IP adresi")
    user_agent: Optional[str] = Field(None, description="User agent")
    
    # Session data
    session_data: Dict[str, Any] = Field(default={}, description="Oturum verisi")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Oturum bitiş zamanı")
    
    class Settings:
        name = "user_sessions"
        indexes = [
            "session_id",
            "user_id",
            "ip_address",
            "created_at",
            "expires_at"
        ]


class APIUsage(Document):
    """API Kullanım İstatistikleri MongoDB Modeli"""
    
    usage_id: str = Field(..., description="Kullanım ID")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    
    # Request data
    user_id: Optional[str] = Field(None, description="Kullanıcı ID")
    ip_address: str = Field(..., description="IP adresi")
    request_size: Optional[int] = Field(None, description="İstek boyutu")
    response_size: Optional[int] = Field(None, description="Yanıt boyutu")
    
    # Performance
    response_time: Optional[float] = Field(None, description="Yanıt süresi (ms)")
    status_code: int = Field(..., description="HTTP status code")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "api_usage"
        indexes = [
            "endpoint",
            "user_id",
            "ip_address",
            "created_at",
            "status_code"
        ]


class DatabaseManager:
    """MongoDB Atlas Database Manager for Main API"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        
    async def connect(self, connection_string: str, database_name: str = "yargisalzeka"):
        """MongoDB Atlas'a bağlan"""
        try:
            self.client = AsyncIOMotorClient(connection_string)
            self.database = self.client[database_name]
            
            # Beanie'yi başlat
            await init_beanie(
                database=self.database,
                document_models=[
                    AnalysisResult,
                    UserSession,
                    APIUsage
                ]
            )
            
            logger.info(f"Main API MongoDB Atlas'a başarıyla bağlandı: {database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Main API MongoDB Atlas bağlantı hatası: {e}")
            return False
    
    async def disconnect(self):
        """MongoDB bağlantısını kapat"""
        if self.client:
            self.client.close()
            logger.info("Main API MongoDB bağlantısı kapatıldı")
    
    async def health_check(self) -> bool:
        """Database sağlık kontrolü"""
        try:
            if not self.client:
                return False
            
            # Ping database
            await self.client.admin.command('ping')
            return True
            
        except Exception as e:
            logger.error(f"Main API Database sağlık kontrolü başarısız: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Database istatistikleri"""
        try:
            stats = {}
            
            # Collection stats
            stats["analysis_count"] = await AnalysisResult.count()
            stats["sessions_count"] = await UserSession.count()
            stats["api_usage_count"] = await APIUsage.count()
            
            # Recent activity
            from datetime import timedelta
            recent_date = datetime.utcnow() - timedelta(days=7)
            stats["recent_analysis"] = await AnalysisResult.find(
                AnalysisResult.created_at >= recent_date
            ).count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Main API Database istatistikleri alınamadı: {e}")
            return {}


# Global database manager instance
db_manager = DatabaseManager()


async def get_database():
    """Database instance'ını al"""
    return db_manager.database


async def init_database():
    """Database'i başlat"""
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    if not connection_string:
        logger.error("MONGODB_CONNECTION_STRING environment variable bulunamadı")
        return False
    
    database_name = os.getenv("MONGODB_DATABASE_NAME", "yargisalzeka")
    return await db_manager.connect(connection_string, database_name)


async def close_database():
    """Database bağlantısını kapat"""
    await db_manager.disconnect()


# Utility functions for saving data
async def save_analysis_result(
    analysis_id: str,
    case_text: str,
    keywords: List[str],
    search_results: List[Dict],
    scored_results: List[Dict],
    ai_analysis: Dict = None,
    petition_template: str = None,
    execution_time: float = None,
    user_id: str = None
) -> bool:
    """Analiz sonucunu MongoDB'ye kaydet"""
    try:
        analysis = AnalysisResult(
            analysis_id=analysis_id,
            user_id=user_id,
            case_text=case_text,
            extracted_keywords=keywords,
            search_results=search_results,
            scored_results=scored_results,
            ai_analysis=ai_analysis,
            petition_template=petition_template,
            execution_time=execution_time
        )
        
        await analysis.save()
        logger.info(f"Analiz sonucu kaydedildi: {analysis_id}")
        return True
        
    except Exception as e:
        logger.error(f"Analiz sonucu kaydedilemedi: {e}")
        return False


async def log_api_usage(
    endpoint: str,
    method: str,
    ip_address: str,
    status_code: int,
    response_time: float = None,
    user_id: str = None,
    request_size: int = None,
    response_size: int = None
) -> bool:
    """API kullanımını MongoDB'ye kaydet"""
    try:
        import uuid
        usage = APIUsage(
            usage_id=str(uuid.uuid4()),
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
            request_size=request_size,
            response_size=response_size
        )
        
        await usage.save()
        return True
        
    except Exception as e:
        logger.error(f"API kullanımı kaydedilemedi: {e}")
        return False

