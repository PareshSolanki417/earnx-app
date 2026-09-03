import os
import urllib.parse
from decimal import Decimal
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def sanitize_database_url(url: Optional[str]) -> str:
    """
    Sanitizes and normalizes the database URL.
    - Handles postgres:// -> postgresql:// for SQLAlchemy compatibility
    - Properly URL-encodes passwords with special characters (e.g. #, @, %, etc.)
    - Falls back to local SQLite if URL is missing
    """
    if not url or not url.strip():
        return "sqlite:///./earnx.db"

    url = url.strip()

    # Convert postgres:// to postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Parse and encode credentials if postgresql URL
    try:
        if url.startswith("postgresql://") or url.startswith("postgresql+psycopg2://"):
            parsed = urllib.parse.urlparse(url)
            # Reconstruct with encoded username and password
            username = parsed.username
            password = parsed.password
            hostname = parsed.hostname
            port = parsed.port
            path = parsed.path

            if username and password is not None:
                encoded_user = urllib.parse.quote_plus(username)
                encoded_pass = urllib.parse.quote_plus(password)
                netloc = f"{encoded_user}:{encoded_pass}@{hostname}"
                if port:
                    netloc += f":{port}"
                
                # Check for query parameters like sslmode
                scheme = parsed.scheme
                query = parsed.query
                clean_url = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, query, parsed.fragment))
                return clean_url
    except Exception:
        pass

    return url


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "EarnX"
    APP_DEBUG: bool = True
    API_V1_STR: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    WEBAPP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000,https://web.telegram.org"

    DATABASE_URL: Optional[str] = None

    BOT_TOKEN: str = "mock_bot_token"
    BOT_USERNAME: str = "EarnXBot"

    MONETAG_ZONE_ID: str = "mock_zone_id"
    MONETAG_API_KEY: str = "mock_api_key"
    MONETAG_POSTBACK_SECRET: str = "mock_secret_key"

    SECRET_KEY: str = "super_secret_jwt_key_earnx_dev_32_chars_min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@earnx.app"
    ADMIN_PASSWORD: str = "AdminEarnX2026!"

    COINS_PER_RUPEE: Decimal = Decimal("100.0")
    MIN_WITHDRAWAL_RUPEES: Decimal = Decimal("50.0")
    REFERRAL_BONUS_COINS: Decimal = Decimal("50.0")
    REFERRAL_QUALIFYING_ACTIONS: int = 3
    DAILY_MAX_REWARD_COINS: Decimal = Decimal("1000.0")
    DAILY_MAX_WITHDRAWAL_RUPEES: Decimal = Decimal("500.0")

    MAX_ADS_PER_HOUR: int = 30
    MIN_SECONDS_BETWEEN_ADS: int = 60
    MAX_FAILED_ATTEMPTS: int = 5

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        return sanitize_database_url(self.DATABASE_URL)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
