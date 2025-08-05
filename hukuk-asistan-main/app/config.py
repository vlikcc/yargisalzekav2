from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    
    # n8n ile iletişim için ayarlar
    N8N_WEBHOOK_URL: str
    N8N_AUTH_SECRET: str
    
    # Google Gemini AI ayarları
    GEMINI_API_KEY: str
    
    LOG_LEVEL: str = "INFO"

settings = Settings()