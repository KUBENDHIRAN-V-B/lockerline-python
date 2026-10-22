"""Application settings."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    database_url: str = Field("sqlite:///./lockerline.db", min_length=1)
    free_window_hours: int = Field(48, ge=1)
    seed_dir: str = Field("seed", min_length=1)
    host: str = Field("0.0.0.0", min_length=1)
    port: int = Field(8080, ge=1, le=65535)
    # Local-development default only; set LOCKERLINE_CODE_SECRET in deployment.
    code_secret: str = Field(
        "development-only-change-this-secret",
        min_length=16,
        validation_alias="LOCKERLINE_CODE_SECRET",
    )
