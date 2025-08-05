from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid

class AnalysisRequest(BaseModel):
    user_case_description: str

class AnalysisResponse(BaseModel):
    message: str
    transaction_id: uuid.UUID

class N8NResultRequest(BaseModel):
    transaction_id: uuid.UUID
    analysis_result: str

# AI Özellikleri için yeni schema'lar
class KeywordExtractionRequest(BaseModel):
    case_text: str

class KeywordExtractionResponse(BaseModel):
    keywords: List[str]
    success: bool
    message: str

class DecisionAnalysisRequest(BaseModel):
    case_text: str
    decision_text: str

class DecisionAnalysisResponse(BaseModel):
    score: int  # 0-100 arası
    explanation: str
    similarity: str
    success: bool

class PetitionGenerationRequest(BaseModel):
    case_text: str
    relevant_decisions: List[Dict[str, Any]]

class PetitionGenerationResponse(BaseModel):
    petition_template: str
    success: bool
    message: str

class SmartSearchRequest(BaseModel):
    case_text: str
    max_results: Optional[int] = 10

class SmartSearchResponse(BaseModel):
    keywords: List[str]
    search_results: List[Dict[str, Any]]
    analyzed_results: List[Dict[str, Any]]  # Puanlanmış sonuçlar
    success: bool
    message: str