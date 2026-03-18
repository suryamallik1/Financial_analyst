from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Keys
    GOOGLE_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    POLYGON_API_KEY: str = ""
    FRED_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    
    # GCP
    GCP_PROJECT_ID: str = ""
    BIGQUERY_DATASET: str = "financial_data"
    
    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
