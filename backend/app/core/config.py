from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    travel_data_mode: Literal["demo", "live"] = "demo"
    places_provider: Literal["demo", "google"] = "demo"
    routes_provider: Literal["demo", "google"] = "demo"
    weather_provider: Literal["demo", "weatherapi"] = "demo"
    routes_travel_mode: str = "DRIVE"
    routes_routing_preference: str = "TRAFFIC_UNAWARE"
    allowed_origins: str = "http://localhost:8080,http://localhost:3000"
    openrouter_api_key: str | None = None
    trip_agent_model: str = "openai/gpt-4.1-mini"
    database_url: str | None = None
    google_maps_api_key: str | None = None
    weather_api_key: str | None = None
    request_timeout_seconds: float = Field(default=12, ge=1, le=60)
    provider_max_retries: int = Field(default=2, ge=0, le=2)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
