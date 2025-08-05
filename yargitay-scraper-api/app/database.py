import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
from . import models

load_dotenv()

async def init_db():
    """
    Uygulama başladığında veritabanı bağlantısını ve Beanie'yi başlatır.
    """
    db_url = os.getenv("DATABASE_URL")
    db_name = os.getenv("MONGO_DATABASE")

    client = AsyncIOMotorClient(db_url)
    
    await init_beanie(
        database=client[db_name], 
        document_models=[models.User] # Beanie'ye User modelini tanıt
    )