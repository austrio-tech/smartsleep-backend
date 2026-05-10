from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1-hour sessions

    database_url: Optional[str] = None

    # Supabase
    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str

    # Cloudflare R2
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_endpoint_url: Optional[str] = None
    r2_bucket_name: Optional[str] = None

    # Email (Google Apps Script relay)
    google_script_url: str = ""
    email_token: str = ""
    email_name: str = "Smart Sleep Service"
    frontend_url: str = "https://smartsleep-api.onrender.com"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
