from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    default_language: str = "pt"
    default_country: str = "BR"

    cache_ttl: int = 3600          # segundos de validade do cache
    db_path: str = "./cache.db"

    trends_sleep: int = 60         # segundos entre chamadas ao Google Trends

    max_articles: int = 100

    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
