"""
Extended MongoDB Atlas Database Models for Main API
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


# Additional Enums
class PetitionCategory(str, Enum):
    TRAFIK = "trafik"
    TICARET = "ticaret"
    AILE = "aile"
    CEZA = "ceza"
    MEDENI = "medeni"
    IDARE = "idare"
    VERGI = "vergi"
    EMEK = "emek"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FeedbackType(str, Enum):
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    GENERAL_FEEDBACK = "general_feedback"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"


# Extended Collections
class PetitionTemplate(Document):
    """Dilekçe Şablonları MongoDB Modeli"""
    
    template_id: str = Field(..., description="Şablon ID")
    user_id: str = Field(..., description="Oluşturan kullanıcı ID")
    title: str = Field(..., description="Şablon başlığı")
    category: PetitionCategory = Field(..., description="Şablon kategorisi")
    
    # Template content
    template_content: str = Field(..., description="Şablon içeriği")
    case_text: str = Field(..., description="Kaynak olay metni")
    referenced_decisions: List[str] = Field(default=[], description="Referans karar ID'leri")
    
    # AI generation details
    ai_model: str = Field(default="gemini-pro", description="Kullanılan AI modeli")
    generation_prompt: Optional[str] = Field(None, description="Kullanılan prompt")
    
    # Usage stats
    usage_count: int = Field(default=0, description="Kullanım sayısı")
    rating_sum: int = Field(default=0, description="Toplam puan")
    rating_count: int = Field(default=0, description="Değerlendirme sayısı")
    
    # Status
    is_public: bool = Field(default=False, description="Herkese açık mı")
    is_approved: bool = Field(default=False, description="Onaylanmış mı")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "petition_templates"
        indexes = [
            "template_id",
            "user_id",
            "category",
            "is_public",
            "is_approved",
            "created_at",
            [("title", "text"), ("template_content", "text")]
        ]


class SystemLog(Document):
    """Sistem Logları MongoDB Modeli"""
    
    log_id: str = Field(..., description="Log ID")
    level: LogLevel = Field(..., description="Log seviyesi")
    message: str = Field(..., description="Log mesajı")
    
    # Context
    module: str = Field(..., description="Modül adı")
    function: Optional[str] = Field(None, description="Fonksiyon adı")
    user_id: Optional[str] = Field(None, description="İlgili kullanıcı ID")
    
    # Request context
    request_id: Optional[str] = Field(None, description="İstek ID")
    ip_address: Optional[str] = Field(None, description="IP adresi")
    user_agent: Optional[str] = Field(None, description="User agent")
    
    # Error details
    error_type: Optional[str] = Field(None, description="Hata türü")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    
    # Performance
    execution_time: Optional[float] = Field(None, description="Çalışma süresi (ms)")
    memory_usage: Optional[int] = Field(None, description="Bellek kullanımı (bytes)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "system_logs"
        indexes = [
            "log_id",
            "level",
            "module",
            "user_id",
            "created_at",
            "request_id"
        ]


class Notification(Document):
    """Bildirimler MongoDB Modeli"""
    
    notification_id: str = Field(..., description="Bildirim ID")
    user_id: str = Field(..., description="Hedef kullanıcı ID")
    title: str = Field(..., description="Bildirim başlığı")
    message: str = Field(..., description="Bildirim mesajı")
    
    # Type and priority
    notification_type: str = Field(..., description="Bildirim türü")
    priority: str = Field(default="normal", description="Öncelik (low/normal/high/urgent)")
    
    # Delivery
    channels: List[str] = Field(default=["web"], description="Bildirim kanalları (web/email/sms)")
    is_read: bool = Field(default=False, description="Okundu mu")
    read_at: Optional[datetime] = Field(None, description="Okunma tarihi")
    
    # Scheduling
    scheduled_for: Optional[datetime] = Field(None, description="Zamanlanmış gönderim")
    sent_at: Optional[datetime] = Field(None, description="Gönderilme tarihi")
    
    # Action
    action_url: Optional[str] = Field(None, description="Aksiyon URL'i")
    action_text: Optional[str] = Field(None, description="Aksiyon metni")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Son geçerlilik tarihi")
    
    class Settings:
        name = "notifications"
        indexes = [
            "notification_id",
            "user_id",
            "notification_type",
            "is_read",
            "scheduled_for",
            "created_at"
        ]


class Feedback(Document):
    """Kullanıcı Geri Bildirimleri MongoDB Modeli"""
    
    feedback_id: str = Field(..., description="Geri bildirim ID")
    user_id: Optional[str] = Field(None, description="Kullanıcı ID (anonim olabilir)")
    feedback_type: FeedbackType = Field(..., description="Geri bildirim türü")
    
    # Content
    title: str = Field(..., description="Başlık")
    description: str = Field(..., description="Açıklama")
    rating: Optional[int] = Field(None, description="Puan (1-5)")
    
    # Context
    page_url: Optional[str] = Field(None, description="Sayfa URL'i")
    feature_name: Optional[str] = Field(None, description="Özellik adı")
    search_query_id: Optional[str] = Field(None, description="İlgili arama sorgusu ID")
    
    # Status
    status: str = Field(default="open", description="Durum (open/in_progress/resolved/closed)")
    priority: str = Field(default="normal", description="Öncelik")
    assigned_to: Optional[str] = Field(None, description="Atanan kişi")
    
    # Response
    admin_response: Optional[str] = Field(None, description="Admin yanıtı")
    response_date: Optional[datetime] = Field(None, description="Yanıt tarihi")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None, description="IP adresi")
    user_agent: Optional[str] = Field(None, description="User agent")
    
    class Settings:
        name = "feedback"
        indexes = [
            "feedback_id",
            "user_id",
            "feedback_type",
            "status",
            "created_at",
            "rating"
        ]


class AdminUser(Document):
    """Admin Kullanıcıları MongoDB Modeli"""
    
    admin_id: str = Field(..., description="Admin ID")
    email: EmailStr = Field(..., description="Email adresi")
    password_hash: str = Field(..., description="Şifrelenmiş şifre")
    first_name: str = Field(..., description="Ad")
    last_name: str = Field(..., description="Soyad")
    
    # Permissions
    role: str = Field(..., description="Rol (super_admin/admin/moderator)")
    permissions: List[str] = Field(default=[], description="İzinler")
    
    # Status
    is_active: bool = Field(default=True, description="Aktif mi")
    is_super_admin: bool = Field(default=False, description="Süper admin mi")
    
    # Security
    last_login: Optional[datetime] = Field(None, description="Son giriş")
    failed_login_attempts: int = Field(default=0, description="Başarısız giriş denemeleri")
    locked_until: Optional[datetime] = Field(None, description="Kilitlenme bitiş tarihi")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="Oluşturan admin ID")
    
    class Settings:
        name = "admin_users"
        indexes = [
            "admin_id",
            "email",
            "role",
            "is_active",
            "created_at"
        ]


class SystemSetting(Document):
    """Sistem Ayarları MongoDB Modeli"""
    
    setting_id: str = Field(..., description="Ayar ID")
    key: str = Field(..., description="Ayar anahtarı")
    value: Any = Field(..., description="Ayar değeri")
    
    # Metadata
    category: str = Field(..., description="Kategori")
    description: Optional[str] = Field(None, description="Açıklama")
    data_type: str = Field(..., description="Veri türü (string/int/float/bool/json)")
    
    # Validation
    is_required: bool = Field(default=False, description="Zorunlu mu")
    default_value: Optional[Any] = Field(None, description="Varsayılan değer")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Doğrulama kuralları")
    
    # Access control
    is_public: bool = Field(default=False, description="Herkese açık mı")
    requires_restart: bool = Field(default=False, description="Restart gerektirir mi")
    
    # Versioning
    version: int = Field(default=1, description="Versiyon")
    previous_value: Optional[Any] = Field(None, description="Önceki değer")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(None, description="Güncelleyen admin ID")
    
    class Settings:
        name = "system_settings"
        indexes = [
            "setting_id",
            "key",
            "category",
            "is_public",
            "updated_at"
        ]


# Extended Database Manager
class ExtendedDatabaseManager:
    """Extended MongoDB Atlas Database Manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        
    async def connect(self, connection_string: str, database_name: str = "yargisalzeka"):
        """MongoDB Atlas'a bağlan"""
        try:
            self.client = AsyncIOMotorClient(connection_string)
            self.database = self.client[database_name]
            
            # Import existing models
            from .database import (
                User, Subscription, Payment, KeywordsCache, SearchCache, 
                AIAnalysisCache, YargitayDecision, SearchQuery, UserActivity,
                AnalysisResult, UserSession, APIUsage
            )
            
            # Beanie'yi başlat - tüm modeller
            await init_beanie(
                database=self.database,
                document_models=[
                    # Existing core models
                    User, Subscription, Payment,
                    # Existing cache models
                    KeywordsCache, SearchCache, AIAnalysisCache,
                    # Existing data models
                    YargitayDecision, SearchQuery, UserActivity,
                    AnalysisResult, UserSession, APIUsage,
                    # New extended models
                    PetitionTemplate, SystemLog, Notification,
                    Feedback, AdminUser, SystemSetting
                ]
            )
            
            logger.info(f"Extended MongoDB Atlas'a başarıyla bağlanıldı: {database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Extended MongoDB Atlas bağlantı hatası: {e}")
            return False
    
    async def get_extended_stats(self) -> Dict[str, Any]:
        """Genişletilmiş database istatistikleri"""
        try:
            stats = {}
            
            # Core collections
            stats["users_count"] = await User.count()
            stats["subscriptions_count"] = await Subscription.count()
            stats["payments_count"] = await Payment.count()
            
            # Cache collections
            stats["keywords_cache_count"] = await KeywordsCache.count()
            stats["search_cache_count"] = await SearchCache.count()
            stats["ai_analysis_cache_count"] = await AIAnalysisCache.count()
            
            # Data collections
            stats["decisions_count"] = await YargitayDecision.count()
            stats["queries_count"] = await SearchQuery.count()
            stats["activities_count"] = await UserActivity.count()
            
            # Extended collections
            stats["petition_templates_count"] = await PetitionTemplate.count()
            stats["system_logs_count"] = await SystemLog.count()
            stats["notifications_count"] = await Notification.count()
            stats["feedback_count"] = await Feedback.count()
            stats["admin_users_count"] = await AdminUser.count()
            stats["system_settings_count"] = await SystemSetting.count()
            
            # Recent activity (last 7 days)
            from datetime import timedelta
            recent_date = datetime.utcnow() - timedelta(days=7)
            stats["recent_users"] = await User.find(User.created_at >= recent_date).count()
            stats["recent_searches"] = await SearchQuery.find(SearchQuery.created_at >= recent_date).count()
            stats["recent_feedback"] = await Feedback.find(Feedback.created_at >= recent_date).count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Extended database istatistikleri alınamadı: {e}")
            return {}


# Global extended database manager instance
extended_db_manager = ExtendedDatabaseManager()


# Utility functions for extended models
async def create_default_system_settings():
    """Varsayılan sistem ayarlarını oluştur"""
    default_settings = [
        {
            "setting_id": "maintenance_mode",
            "key": "maintenance_mode",
            "value": False,
            "category": "system",
            "description": "Bakım modu aktif mi",
            "data_type": "bool",
            "is_required": True,
            "default_value": False,
            "is_public": True,
            "requires_restart": False
        },
        {
            "setting_id": "max_search_results",
            "key": "max_search_results",
            "value": 50,
            "category": "search",
            "description": "Maksimum arama sonucu sayısı",
            "data_type": "int",
            "is_required": True,
            "default_value": 50,
            "is_public": False,
            "requires_restart": False
        },
        {
            "setting_id": "ai_cache_duration",
            "key": "ai_cache_duration",
            "value": 30,
            "category": "ai",
            "description": "AI cache süresi (gün)",
            "data_type": "int",
            "is_required": True,
            "default_value": 30,
            "is_public": False,
            "requires_restart": False
        }
    ]
    
    for setting_data in default_settings:
        existing = await SystemSetting.find_one(SystemSetting.key == setting_data["key"])
        if not existing:
            setting = SystemSetting(**setting_data)
            await setting.save()
            logger.info(f"Varsayılan ayar oluşturuldu: {setting_data['key']}")


async def create_default_admin_user():
    """Varsayılan admin kullanıcısı oluştur"""
    import hashlib
    
    admin_email = "admin@yargisalzeka.com"
    existing_admin = await AdminUser.find_one(AdminUser.email == admin_email)
    
    if not existing_admin:
        # Varsayılan şifre: admin123 (production'da değiştirilmeli)
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        
        admin = AdminUser(
            admin_id="admin_001",
            email=admin_email,
            password_hash=password_hash,
            first_name="System",
            last_name="Administrator",
            role="super_admin",
            permissions=["all"],
            is_active=True,
            is_super_admin=True
        )
        
        await admin.save()
        logger.info(f"Varsayılan admin kullanıcısı oluşturuldu: {admin_email}")


async def init_extended_database():
    """Genişletilmiş database'i başlat"""
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    if not connection_string:
        logger.error("MONGODB_CONNECTION_STRING environment variable bulunamadı")
        return False
    
    database_name = os.getenv("MONGODB_DATABASE_NAME", "yargisalzeka")
    success = await extended_db_manager.connect(connection_string, database_name)
    
    if success:
        # Varsayılan verileri oluştur
        await create_default_system_settings()
        await create_default_admin_user()
    
    return success

