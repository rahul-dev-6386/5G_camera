"""Tests for configuration validation."""

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


class TestSettingsValidation:
    """Test settings validation."""
    
    def test_jwt_secret_validation_default_fails(self):
        """Test that default JWT secret fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(jwt_secret_key="change-me-in-env")
        assert "JWT_SECRET_KEY" in str(exc_info.value)
    
    def test_jwt_secret_validation_short_fails(self):
        """Test that short JWT secret fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(jwt_secret_key="short")
        assert "at least 32 characters" in str(exc_info.value)
    
    def test_jwt_secret_validation_valid_passes(self):
        """Test that valid JWT secret passes validation."""
        settings = Settings(jwt_secret_key="a" * 32)
        assert settings.jwt_secret_key == "a" * 32
    
    def test_yolo_confidence_validation(self):
        """Test YOLO confidence validation."""
        # Valid values
        Settings(yolo_confidence=0.5)
        Settings(yolo_confidence=0.0)
        Settings(yolo_confidence=1.0)
        
        # Invalid values
        with pytest.raises(ValidationError):
            Settings(yolo_confidence=1.5)
        with pytest.raises(ValidationError):
            Settings(yolo_confidence=-0.1)
    
    def test_yolo_iou_validation(self):
        """Test YOLO IOU validation."""
        # Valid values
        Settings(yolo_iou=0.5)
        Settings(yolo_iou=0.0)
        Settings(yolo_iou=1.0)
        
        # Invalid values
        with pytest.raises(ValidationError):
            Settings(yolo_iou=1.5)
        with pytest.raises(ValidationError):
            Settings(yolo_iou=-0.1)
    
    def test_api_port_validation(self):
        """Test API port validation."""
        # Valid values
        Settings(api_port=8000)
        Settings(api_port=1)
        Settings(api_port=65535)
        
        # Invalid values
        with pytest.raises(ValidationError):
            Settings(api_port=0)
        with pytest.raises(ValidationError):
            Settings(api_port=70000)
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid values
        Settings(log_level="DEBUG")
        Settings(log_level="INFO")
        Settings(log_level="WARNING")
        Settings(log_level="ERROR")
        Settings(log_level="CRITICAL")
        
        # Invalid value
        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")
    
    def test_log_format_validation(self):
        """Test log format validation."""
        # Valid values
        Settings(log_format="text")
        Settings(log_format="json")
        
        # Invalid value
        with pytest.raises(ValidationError):
            Settings(log_format="xml")
    
    def test_get_settings_caching(self):
        """Test that get_settings uses caching."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
