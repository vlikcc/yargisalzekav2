"""
MongoDB Atlas Database Configuration and Models
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


class YargitayDecision(Document):
    """Yargıtay Kararı MongoDB Modeli"""
    
    decision_id: str = Field(..., description="Karar ID")
    court: str = Field(..., description="Mahkeme")
    date: datetime = Field(..., description="Karar tarihi")
    number: str = Field(..., description="Karar numarası")
    title: str = Field(..., description="Karar başlığı")
    content: str = Field(..., description="Karar içeriği")
    keywords: List[str] = Field(default=[], description="Anahtar kelimeler")
    category: Optional[str] = Field(None, description="Kategori")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    source_url: Optional[str] = Field(None, description="Kaynak URL")
    
    # Search ve indexing için
    search_score: Optional[float] = Field(None, description="Arama skoru")
    ai_score: Optional[float] = Field(None, description="AI puanı")
    
    class Settings:
        name = "yargitay_decisions"
        indexes = [
            "decision_id",
            "court",
            "date",
            "keywords",
            "category",
            [("title", "text"), ("content", "text")]  # Text search index
        ]


class SearchQuery(Document):
    """Arama Sorguları MongoDB Modeli"""
    
    query_id: str = Field(..., description="Sorgu ID")
    user_id: Optional[str] = Field(None, description="Kullanıcı ID")
    query_text: str = Field(..., description="Arama metni")
    keywords: List[str] = Field(default=[], description="Çıkarılan anahtar kelimeler")
    results_count: int = Field(default=0, description="Sonuç sayısı")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time: Optional[float] = Field(None, description="Çalışma süresi (saniye)")
    
    # Results
    results: List[Dict[str, Any]] = Field(default=[], description="Arama sonuçları")
    
    class Settings:
        name = "search_queries"
        indexes = [
            "query_id",
            "user_id",
            "created_at",
            [("query_text", "text")]
        ]


class UserActivity(Document):
    """Kullanıcı Aktiviteleri MongoDB Modeli"""
    
    user_id: str = Field(..., description="Kullanıcı ID")
    activity_type: str = Field(..., description="Aktivite türü")
    activity_data: Dict[str, Any] = Field(default={}, description="Aktivite verisi")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    ip_address: Optional[str] = Field(None, description="IP adresi")
    user_agent: Optional[str] = Field(None, description="User agent")
    
    class Settings:
        name = "user_activities"
        indexes = [
            "user_id",
            "activity_type",
            "created_at"
        ]


class DatabaseManager:
    """MongoDB Atlas Database Manager"""
    
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
                    YargitayDecision,
                    SearchQuery,
                    UserActivity
                ]
            )
            
            logger.info(f"MongoDB Atlas'a başarıyla bağlanıldı: {database_name}")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB Atlas bağlantı hatası: {e}")
            return False
    
    async def disconnect(self):
        """MongoDB bağlantısını kapat"""
        if self.client:
            self.client.close()
            logger.info("MongoDB bağlantısı kapatıldı")
    
    async def health_check(self) -> bool:
        """Database sağlık kontrolü"""
        try:
            if not self.client:
                return False
            
            # Ping database
            await self.client.admin.command('ping')
            return True
            
        except Exception as e:
            logger.error(f"Database sağlık kontrolü başarısız: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Database istatistikleri"""
        try:
            stats = {}
            
            # Collection stats
            stats["decisions_count"] = await YargitayDecision.count()
            stats["queries_count"] = await SearchQuery.count()
            stats["activities_count"] = await UserActivity.count()
            
            # Database stats
            db_stats = await self.database.command("dbStats")
            stats["database_size"] = db_stats.get("dataSize", 0)
            stats["storage_size"] = db_stats.get("storageSize", 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Database istatistikleri alınamadı: {e}")
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


# Legacy function for backward compatibility
async def init_db():
    """
    Uygulama başladığında veritabanı bağlantısını ve Beanie'yi başlatır.
    """
    return await init_database()