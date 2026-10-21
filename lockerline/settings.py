"""One settings object, read once at start-up. Nothing is hard-coded.

Every field here has a default; the environment can change it. This module imports nothing from FastAPI, so the services that read the
settings stay free of the web framework; the request dependency lives in routers/__init__.py.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field("sqlite:///./lockerline.db", min_length=1)
    free_window_hours: int = Field(48, ge=1)                # how long a pickup code stays valid
    code_hash_key: str = Field("dev-only-change-me", min_length=1)  # keyed SHA-256 for pickup codes
    seed_dir: str = Field("seed", min_length=1)
    host: str = Field("0.0.0.0", min_length=1)              # the address uvicorn binds
    port: int = Field(8080, ge=1, le=65535)