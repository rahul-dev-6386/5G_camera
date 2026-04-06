from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[4]
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    storage_dir: str = Field(default=str(ROOT_DIR / "storage"), alias="STORAGE_DIR")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    jwt_secret_key: str = Field(default="change-me-in-env", alias="JWT_SECRET_KEY")
    jwt_access_exp_minutes: int = Field(default=15, alias="JWT_ACCESS_EXP_MINUTES")
    jwt_refresh_exp_days: int = Field(default=7, alias="JWT_REFRESH_EXP_DAYS")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
