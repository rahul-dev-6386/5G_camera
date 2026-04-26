from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    storage_dir: str = Field(default=str(ROOT_DIR / "storage"), alias="STORAGE_DIR")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    jwt_secret_key: str = Field(default="change-me-in-env", alias="JWT_SECRET_KEY")
    jwt_access_exp_minutes: int = Field(default=15, alias="JWT_ACCESS_EXP_MINUTES")
    jwt_refresh_exp_days: int = Field(default=7, alias="JWT_REFRESH_EXP_DAYS")
    yolo_model: str = Field(default="auto", alias="YOLO_MODEL")
    yolo_confidence: float = Field(default=0.35, alias="YOLO_CONFIDENCE")
    yolo_iou: float = Field(default=0.45, alias="YOLO_IOU")
    yolo_imgsz: int = Field(default=960, alias="YOLO_IMGSZ")
    yolo_device: str = Field(default="auto", alias="YOLO_DEVICE")
    enable_tracking: bool = Field(default=True, alias="ENABLE_TRACKING")
    max_age: int = Field(default=30, alias="TRACKING_MAX_AGE")
    
    # New settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")
    max_upload_size: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")
    min_password_length: int = Field(default=8, alias="MIN_PASSWORD_LENGTH")
    enable_mongodb: bool = Field(default=False, alias="ENABLE_MONGODB")
    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="smart_campus", alias="MONGODB_DB_NAME")
    
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if v == "change-me-in-env" or len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure random string of at least 32 characters. "
                "Update your .env file with a strong secret."
            )
        return v
    
    @field_validator("yolo_confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("YOLO_CONFIDENCE must be between 0 and 1")
        return v
    
    @field_validator("yolo_iou")
    @classmethod
    def validate_iou(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("YOLO_IOU must be between 0 and 1")
        return v
    
    @field_validator("api_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("API_PORT must be between 1 and 65535")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        if v.lower() not in {"text", "json"}:
            raise ValueError("LOG_FORMAT must be 'text' or 'json'")
        return v.lower()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
