# security.py - Güvenlik modülü
import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, EmailStr
from loguru import logger

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Security Bearer
security = HTTPBearer()

class UserInDB(BaseModel):
    id: str
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    subscription_plan: str = "basic"
    api_calls_remaining: int = 50

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
    subscription_plan: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi doğrula"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Şifreyi hashle"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: Dict[Any, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Access token oluştur"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[Any, Any]) -> str:
    """Refresh token oluştur"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenData]:
    """Token'ı doğrula"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        subscription_plan: str = payload.get("subscription_plan", "basic")
        
        if email is None or user_id is None:
            return None
            
        return TokenData(
            email=email, 
            user_id=user_id, 
            subscription_plan=subscription_plan
        )
    except jwt.PyJWTError as e:
        logger.error(f"JWT doğrulama hatası: {e}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Mevcut kullanıcıyı al"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token doğrulanamadı",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
        
    return token_data

async def get_admin_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Admin kullanıcı kontrolü"""
    # Bu kısım database'den kullanıcı bilgilerini alacak şekilde genişletilecek
    # Şimdilik basit kontrol
    if current_user.subscription_plan != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gerekli"
        )
    return current_user

def check_subscription_limits(user: TokenData, operation: str = "search") -> bool:
    """Abonelik limitleri kontrolü"""
    limits = {
        "basic": {"search": 50, "ai_analysis": 20, "petition": 5},
        "standard": {"search": 500, "ai_analysis": 200, "petition": 50},
        "premium": {"search": -1, "ai_analysis": -1, "petition": -1},  # Unlimited
        "admin": {"search": -1, "ai_analysis": -1, "petition": -1}
    }
    
    user_limits = limits.get(user.subscription_plan, limits["basic"])
    operation_limit = user_limits.get(operation, 0)
    
    # -1 means unlimited
    if operation_limit == -1:
        return True
    
    # Bu kısım database'den kullanıcının kalan hakkını kontrol edecek
    # Şimdilik True dönüyor
    return True

def validate_input(text: str, max_length: int = 10000, min_length: int = 10) -> str:
    """Input validasyonu"""
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metin boş olamaz"
        )
    
    text = text.strip()
    
    if len(text) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metin en az {min_length} karakter olmalıdır"
        )
    
    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metin en fazla {max_length} karakter olabilir"
        )
    
    # XSS ve injection koruması
    dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=', 'DROP TABLE', 'DELETE FROM']
    text_lower = text.lower()
    
    for pattern in dangerous_patterns:
        if pattern.lower() in text_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Güvenlik nedeniyle bu metin kabul edilemez"
            )
    
    return text

def get_client_ip(request: Request) -> str:
    """Gerçek client IP'sini al (proxy arkasında da çalışır)"""
    # Proxy headers'larını kontrol et
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host

def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
    """Güvenli redirect URL kontrolü"""
    if not url:
        return False
    
    if allowed_hosts is None:
        allowed_hosts = ["localhost", "127.0.0.1", "yargisalzeka.com"]
    
    # Relative URL'ler güvenli
    if url.startswith("/") and not url.startswith("//"):
        return True
    
    # Absolute URL'leri kontrol et
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.hostname in allowed_hosts
    except:
        return False

# API Key authentication (alternatif)
class APIKeyAuth:
    def __init__(self):
        self.api_keys = os.getenv("API_KEYS", "").split(",")
        self.api_keys = [key.strip() for key in self.api_keys if key.strip()]
    
    def __call__(self, request: Request) -> bool:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            api_key = request.query_params.get("api_key")
        
        if not api_key or api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz API anahtarı"
            )
        return True

# Rate limiting decorators
def rate_limit_by_user(rate: str = "10/minute"):
    """Kullanıcı bazlı rate limiting"""
    def decorator(func):
        return limiter.limit(rate)(func)
    return decorator

def rate_limit_by_ip(rate: str = "100/hour"):
    """IP bazlı rate limiting"""
    def decorator(func):
        return limiter.limit(rate, key_func=get_remote_address)(func)
    return decorator