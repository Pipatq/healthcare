from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    # Pre-shared API key used by the FHIR Gateway to authenticate requests.
    API_KEY: str = "changeme-his-b-key"
    ENV: str = "dev"

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
