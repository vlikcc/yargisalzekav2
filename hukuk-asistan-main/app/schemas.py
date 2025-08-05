from pydantic import BaseModel
import uuid

class AnalysisRequest(BaseModel):
    user_case_description: str

class AnalysisResponse(BaseModel):
    message: str
    transaction_id: uuid.UUID

class N8NResultRequest(BaseModel):
    transaction_id: uuid.UUID
    analysis_result: str