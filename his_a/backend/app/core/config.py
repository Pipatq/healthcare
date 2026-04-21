from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    # Gateway connection
    GATEWAY_BASE_URL: str = "http://gateway:8000"
    GATEWAY_API_KEY: str = "changeme-gateway-key"
    PROXY_TIMEOUT: float = 30.0
    # JWT
    JWT_SECRET_KEY: str = "changeme-jwt-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80"
    ENV: str = "dev"

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
