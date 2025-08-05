from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    
    # Google Gemini AI ayarları
    GEMINI_API_KEY: str
    
    # Yargıtay Scraper API ayarları
    SCRAPER_API_URL: str = "http://localhost:8001"
    
    # Genel ayarlar
    LOG_LEVEL: str = "INFO"
    
    # API ayarları
    API_TITLE: str = "Yargısal Zeka API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Yapay Zeka Destekli Yargıtay Kararı Arama Platformu"

settings = Settings()