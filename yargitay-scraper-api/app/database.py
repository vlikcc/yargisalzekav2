"""
MongoDB Atlas Database Configuration and Models
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie
from pydantic import BaseModel, Field, EmailStr
from loguru import logger
from dotenv import load_dotenv
from enum import Enum

load_dotenv()


# Enums
class SubscriptionPlan(str, Enum):
    TEMEL = "temel"
    STANDART = "standart"
    PREMIUM = "premium"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


# Core Collections
class User(Document):
    """Kullanıcı Hesapları MongoDB Modeli"""
    
    user_id: str = Field(..., description="Kullanıcı ID")
    email: EmailStr = Field(..., description="Email adresi")
    password_hash: str = Field(..., description="Şifrelenmiş şifre")
    first_name: str = Field(..., description="Ad")
    last_name: str = Field(..., description="Soyad")
    
    # Subscription info
    subscription_plan: SubscriptionPlan = Field(default=SubscriptionPlan.TEMEL, description="Abonelik planı")
    subscription_start: Optional[datetime] = Field(None, description="Abonelik başlangıç tarihi")
    subscription_end: Optional[datetime] = Field(None, description="Abonelik bitiş tarihi")
    is_active: bool = Field(default=True, description="Hesap aktif mi")
    
    # Usage limits
    monthly_search_limit: int = Field(default=50, description="Aylık arama limiti")
    monthly_searches_used: int = Field(default=0, description="Bu ay kullanılan arama sayısı")
    last_search_reset: datetime = Field(default_factory=datetime.utcnow, description="Son arama sayacı sıfırlama")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(None, description="Son giriş tarihi")
    
    class Settings:
        name = "users"
        indexes = [
            "user_id",
            "email",
            "subscription_plan",
            "created_at"
        ]


class Subscription(Document):
    """Abonelik Yönetimi MongoDB Modeli"""
    
    subscription_id: str = Field(..., description="Abonelik ID")
    user_id: str = Field(..., description="Kullanıcı ID")
    plan: SubscriptionPlan = Field(..., description="Abonelik planı")
    
    # Pricing
    monthly_price: float = Field(..., description="Aylık ücret")
    currency: str = Field(default="TRY", description="Para birimi")
    
    # Limits and features
    search_limit: int = Field(..., description="Aylık arama limiti")
    petition_limit: Optional[int] = Field(None, description="Aylık dilekçe limiti")
    api_access: bool = Field(default=False, description="API erişimi")
    priority_support: bool = Field(default=False, description="Öncelikli destek")
    
    # Status
    is_active: bool = Field(default=True, description="Abonelik aktif mi")
    auto_renewal: bool = Field(default=True, description="Otomatik yenileme")
    
    # Dates
    start_date: datetime = Field(..., description="Başlangıç tarihi")
    end_date: datetime = Field(..., description="Bitiş tarihi")
    next_billing_date: Optional[datetime] = Field(None, description="Sonraki fatura tarihi")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "subscriptions"
        indexes = [
            "subscription_id",
            "user_id",
            "plan",
            "is_active",
            "end_date"
        ]


class Payment(Document):
    """Ödeme Geçmişi MongoDB Modeli"""
    
    payment_id: str = Field(..., description="Ödeme ID")
    user_id: str = Field(..., description="Kullanıcı ID")
    subscription_id: str = Field(..., description="Abonelik ID")
    
    # Payment details
    amount: float = Field(..., description="Ödeme tutarı")
    currency: str = Field(default="TRY", description="Para birimi")
    payment_method: str = Field(..., description="Ödeme yöntemi")
    
    # Status
    status: PaymentStatus = Field(..., description="Ödeme durumu")
    transaction_id: Optional[str] = Field(None, description="İşlem ID")
    
    # Billing
    billing_period_start: datetime = Field(..., description="Fatura dönemi başlangıç")
    billing_period_end: datetime = Field(..., description="Fatura dönemi bitiş")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(None, description="İşlenme tarihi")
    
    class Settings:
        name = "payments"
        indexes = [
            "payment_id",
            "user_id",
            "subscription_id",
            "status",
            "created_at"
        ]


# Cache Collections
class KeywordsCache(Document):
    """Anahtar Kelime Önbelleği MongoDB Modeli"""
    
    cache_id: str = Field(..., description="Cache ID")
    case_text_hash: str = Field(..., description="Olay metni hash'i")
    case_text: str = Field(..., description="Olay metni")
    extracted_keywords: List[str] = Field(..., description="Çıkarılan anahtar kelimeler")
    
    # AI details
    ai_model: str = Field(default="gemini-pro", description="Kullanılan AI modeli")
    confidence_score: Optional[float] = Field(None, description="Güven skoru")
    
    # Usage stats
    hit_count: int = Field(default=1, description="Kullanım sayısı")
    last_used: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    
    class Settings:
        name = "keywords_cache"
        indexes = [
            "cache_id",
            "case_text_hash",
            "expires_at",
            "last_used"
        ]


class SearchCache(Document):
    """Arama Sonuçları Önbelleği MongoDB Modeli"""
    
    cache_id: str = Field(..., description="Cache ID")
    keywords_hash: str = Field(..., description="Anahtar kelimeler hash'i")
    keywords: List[str] = Field(..., description="Arama anahtar kelimeleri")
    search_results: List[Dict[str, Any]] = Field(..., description="Arama sonuçları")
    
    # Search metadata
    total_results: int = Field(..., description="Toplam sonuç sayısı")
    search_duration: float = Field(..., description="Arama süresi (saniye)")
    
    # Usage stats
    hit_count: int = Field(default=1, description="Kullanım sayısı")
    last_used: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    
    class Settings:
        name = "search_cache"
        indexes = [
            "cache_id",
            "keywords_hash",
            "expires_at",
            "last_used"
        ]


class AIAnalysisCache(Document):
    """AI Analiz Önbelleği MongoDB Modeli"""
    
    cache_id: str = Field(..., description="Cache ID")
    analysis_hash: str = Field(..., description="Analiz hash'i")
    case_text: str = Field(..., description="Olay metni")
    decision_text: str = Field(..., description="Karar metni")
    
    # Analysis results
    ai_score: int = Field(..., description="AI puanı (0-100)")
    explanation: str = Field(..., description="Açıklama")
    similarity: str = Field(..., description="Benzerlik")
    
    # AI details
    ai_model: str = Field(default="gemini-pro", description="Kullanılan AI modeli")
    
    # Usage stats
    hit_count: int = Field(default=1, description="Kullanım sayısı")
    last_used: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    
    class Settings:
        name = "ai_analysis_cache"
        indexes = [
            "cache_id",
            "analysis_hash",
            "expires_at",
            "last_used"
        ]


# Existing Collections (Updated)
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
                    # Core models
                    User,
                    Subscription,
                    Payment,
                    # Cache models
                    KeywordsCache,
                    SearchCache,
                    AIAnalysisCache,
                    # Existing models
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
            stats["users_count"] = await User.count()
            stats["subscriptions_count"] = await Subscription.count()
            stats["payments_count"] = await Payment.count()
            stats["decisions_count"] = await YargitayDecision.count()
            stats["queries_count"] = await SearchQuery.count()
            stats["activities_count"] = await UserActivity.count()
            
            # Cache stats
            stats["keywords_cache_count"] = await KeywordsCache.count()
            stats["search_cache_count"] = await SearchCache.count()
            stats["ai_analysis_cache_count"] = await AIAnalysisCache.count()
            
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