"""Ortam bazlı uygulama ayarları (.env dosyasından okunur)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./kahvecell.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # JWT
    jwt_secret_key: str = "dev-only-secret-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # SMS OTP simülasyonu (case: sabit kod 1234)
    otp_simulated_code: str = "1234"
    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5

    # Rate limiting
    rate_limit_enabled: bool = True
    auth_rate_limit: str = "10/minute"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()
