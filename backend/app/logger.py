import logging
import sys
from pathlib import Path
from typing import Any

from .config import get_settings


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data
        
        import json
        return json.dumps(log_entry)


def setup_logging() -> None:
    """Configure application logging with structured output."""
    settings = get_settings()
    
    log_level = getattr(logging, (getattr(settings, "log_level", "INFO") or "INFO").upper(), logging.INFO)
    log_format = getattr(settings, "log_format", "text") or "text"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    log_dir = Path(getattr(settings, "log_dir", "logs"))
    if log_dir != Path("logs"):
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "app.log")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("ultralytics").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def log_extra(self, **kwargs: Any) -> None:
        """Add extra context to the next log message."""
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **factory_kwargs):
            record = old_factory(*args, **factory_kwargs)
            record.extra_data = kwargs
            return record
        
        logging.setLogRecordFactory(record_factory)
