# /yargitay-scraper-api/app/schemas.py

from pydantic import BaseModel, ConfigDict
from typing import List
from beanie import PydanticObjectId # <-- MongoDB'nin ID tipi için özel import

# --- Arama Şemaları ---
class ResultItem(BaseModel):
    daire: str
    esas_no: str
    karar_no: str
    karar_tarihi: str
    karar_metni: str
    keyword: str

class SearchRequest(BaseModel):
    keywords: List[str]

class SearchResponse(BaseModel):
    results: List[ResultItem]
    success: bool
    message: str
    search_details: dict

# --- Kullanıcı Şemaları (NİHAİ VERSİYON) ---
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

# Bu şema, veritabanından gelen User modelini API yanıtına dönüştürür
class User(UserBase):
    id: PydanticObjectId # <-- ID tipini Beanie'nin kendi tipi olarak belirtiyoruz
    api_key: str
    is_active: bool
    search_count: int
    subscription_status: str

    # Pydantic V2 için veritabanı modelinden veri okuma yapılandırması
    model_config = ConfigDict(
        from_attributes=True,       # orm_mode'un yeni ve doğru adı
        arbitrary_types_allowed=True # PydanticObjectId gibi özel tiplere izin verir
    )