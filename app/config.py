from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str
    storage_dir: str = "./storage"
    database_url: str = "sqlite:///./harf.db"
    free_daily_videos: int = 2
    free_tier_max_minutes: int = 10
    max_upload_mb: int = 50
    allowed_origin: str = "http://localhost:5500"
    google_client_id: str = ""
    jwt_secret: str
    jwt_expires_minutes: int = 60 * 24 * 30
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    frontend_url: str = "http://localhost:5500"
    port: int = 8000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
