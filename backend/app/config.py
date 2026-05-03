from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = "sqlite:///" + (BASE_DIR / "data" / "portfolio.db").as_posix().lstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = _DEFAULT_DB
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Pauza między tickerami przy odświeżaniu (Yahoo 429 przy zbyt wielu zapytaniach)
    yahoo_request_delay_seconds: float = 0.55
    # Kopie portfela po każdej zmianie — ile ostatnich pełnych wersji trzymać.
    portfolio_backup_versions: int = 3
    # Dzienny przyrostowy backup historii cen — retencja (dni).
    price_backup_keep_days: int = 120
    # Dokumentacja OpenAPI (/docs) — domyślnie wyłączona (bezpieczniejszy self-host). Dev: ENABLE_OPENAPI=1
    enable_openapi: bool = False
    # Ograniczenie nagłówka Host (np. za reverse proxy). Puste = wyłączone. Przykład: TRUSTED_HOSTS=localhost,127.0.0.1,app.example.com
    trusted_hosts: str = ""


settings = Settings()
