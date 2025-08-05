# /yargitay-scraper-api/app/models.py

import uuid
from datetime import datetime
from beanie import Document
from pydantic import Field

class User(Document):
    # Beanie, _id alanını otomatik olarak yönetir.
    email: str
    hashed_password: str
    api_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    search_count: int = 0
    subscription_status: str = "inactive"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "Users" # MongoDB'deki koleksiyonun adı