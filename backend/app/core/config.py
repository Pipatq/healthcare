from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    # Comma-separated list of allowed CORS origins, e.g. "http://localhost:5173,https://app.example.com"
    ALLOWED_ORIGINS: str = ""
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENV: str = "dev"

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
