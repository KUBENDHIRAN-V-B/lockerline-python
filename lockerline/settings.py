"""Application settings. Nothing is hard-coded; an env-file can feed it."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Every field here is listed in .env.example. The environment can change it."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    database_url: str = Field("sqlite:///./lockerline.db", min_length=1)
    free_window_hours: int = Field(48, ge=1)
    seed_dir: str = Field("seed", min_length=1)
    host: str = Field("0.0.0.0", min_length=1)
    port: int = Field(8080, ge=1, le=65535)
    code_hash_key: str = Field(
        "development-only-change-this-secret",
        min_length=1,
    )
