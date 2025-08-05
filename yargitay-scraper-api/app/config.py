from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # .env dosyasından ayarları okumak için yapılandırma
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # scraper-api tarafından kullanılan tüm ayarlar
    LOG_LEVEL: str = "INFO"
    USER_RATE_LIMIT: str = "10/minute"
    MAX_PAGES_TO_SEARCH: int = 5
    TARGET_RESULTS_PER_KEYWORD: int = 3
    SELENIUM_GRID_URL: str = "http://selenium-hub:4444/wd/hub"

# Ayarları import edilebilir bir nesne olarak oluştur
settings = Settings()