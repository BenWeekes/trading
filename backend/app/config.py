from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Weekes AATF"
    app_mode: str = "paper"
    event_mode: str = "mock"
    demo_mode: bool = True
    backend_port: int = 8000
    frontend_port: int = 3000
    database_url: str = Field(default=f"sqlite:///{DATA_DIR / 'aatf.db'}")

    fmp_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5.2"
    agora_enabled: bool = True
    agora_backend_url: str = "http://localhost:8082"
    agora_avatar_client_url: str = "http://localhost:8084"
    agora_profile: str = "VIDEO"

    min_surprise_pct: float = 5.0
    min_market_cap: int = 1_000_000_000
    risk_per_trade: float = 0.02
    stop_loss_pct: float = 0.05
    reward_risk_ratio: float = 2.0
    max_gap_pct: float = 0.08

    daily_cost_alert_usd: float = 10.0
    per_role_cost_alert_usd: float = 5.0

    cors_origins: str = "http://localhost:3000"

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url[len(prefix) :])
        return DATA_DIR / "aatf.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings
