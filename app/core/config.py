from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Keys
    GOOGLE_API_KEY: str = ""
    FMP_API_KEY: str = ""
    TIINGO_API_KEY: str = ""
    FRED_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    
    # Database & Cache
    POSTGRES_URL: str = "postgresql://admin:password@localhost:5433/quant_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
