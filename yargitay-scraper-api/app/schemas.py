# /yargitay-scraper-api/app/schemas.py (MongoDB'siz)

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Arama Şemaları ---
class ResultItem(BaseModel):
    daire: str
    esas_no: str
    karar_no: str
    karar_tarihi: str
    karar_metni: str
    keyword: str
    case_number: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[str] = None
    court: Optional[str] = None
    url: Optional[str] = None

class SearchRequest(BaseModel):
    keywords: List[str]
    max_results: Optional[int] = 50

class SearchResponse(BaseModel):
    results: List[ResultItem]
    success: bool
    message: str
    search_details: Dict[str, Any]
    processing_time: Optional[float] = None
    total_keywords: Optional[int] = None
    unique_results: Optional[int] = None