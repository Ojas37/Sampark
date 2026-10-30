from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{ROOT_DIR / 'backend' / 'data' / 'flowwise.db'}"
    jwt_secret: str = "local-demo-secret-change-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    demo_mode: bool = True
    llm_provider: str = "none"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    public_base_url: str = "http://localhost:5173"
    storage_dir: Path = ROOT_DIR / "backend" / "data" / "files"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
