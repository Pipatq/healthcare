from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Internal URL of the HIS B Facade (Docker service name)
    HIS_B_BASE_URL: str = "http://his_b:8000"
    # API Key shared with HIS B
    HIS_B_API_KEY: str = "changeme-his-b-key"
    # API Key that HIS A must present to call the Gateway
    GATEWAY_API_KEY: str = "changeme-gateway-key"
    # Request timeout (seconds) when forwarding to HIS B
    PROXY_TIMEOUT: float = 30.0
    ENV: str = "dev"

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
