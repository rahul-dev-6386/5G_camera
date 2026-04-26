"""Alert system for capacity thresholds and occupancy monitoring."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

from ..config import get_settings
from ..logger import get_logger


class AlertSeverity(Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert event."""
    severity: AlertSeverity
    message: str
    classroom: str
    course_code: str
    current_count: int
    threshold: int
    timestamp: str
    alert_type: str


class AlertManager:
    """Manages capacity threshold alerts."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.alerts: list[Alert] = []
        self.alert_callbacks: list[Callable[[Alert], None]] = []
        self.thresholds: dict[str, int] = {}  # classroom -> threshold
        self.default_threshold = 40
    
    def set_threshold(self, classroom: str, threshold: int) -> None:
        """Set capacity threshold for a specific classroom."""
        self.thresholds[classroom] = threshold
        self.logger.info(f"Set threshold for {classroom} to {threshold}")
    
    def get_threshold(self, classroom: str) -> int:
        """Get capacity threshold for a classroom."""
        return self.thresholds.get(classroom, self.default_threshold)
    
    def check_occupancy(
        self,
        classroom: str,
        course_code: str,
        current_count: int
    ) -> Optional[Alert]:
        """Check if occupancy exceeds threshold and generate alert if needed."""
        threshold = self.get_threshold(classroom)
        
        if current_count >= threshold:
            severity = AlertSeverity.CRITICAL if current_count >= threshold * 1.1 else AlertSeverity.WARNING
            alert = Alert(
                severity=severity,
                message=f"Occupancy {current_count} exceeds capacity threshold {threshold}",
                classroom=classroom,
                course_code=course_code,
                current_count=current_count,
                threshold=threshold,
                timestamp=datetime.now(timezone.utc).isoformat(),
                alert_type="capacity_exceeded"
            )
            self.alerts.append(alert)
            self.logger.warning(
                f"Capacity alert: {classroom} - {current_count}/{threshold} students"
            )
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
            
            return alert
        
        return None
    
    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback function to be called when alerts are triggered."""
        self.alert_callbacks.append(callback)
        self.logger.info(f"Registered alert callback: {callback.__name__}")
    
    def get_recent_alerts(self, limit: int = 50) -> list[Alert]:
        """Get recent alerts."""
        return self.alerts[-limit:]
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        self.logger.info("Cleared all alerts")
    
    def get_alert_summary(self) -> dict:
        """Get summary of alerts by severity."""
        summary = {
            "total": len(self.alerts),
            "critical": 0,
            "warning": 0,
            "info": 0
        }
        
        for alert in self.alerts:
            if alert.severity == AlertSeverity.CRITICAL:
                summary["critical"] += 1
            elif alert.severity == AlertSeverity.WARNING:
                summary["warning"] += 1
            else:
                summary["info"] += 1
        
        return summary


# Global alert manager instance
alert_manager = AlertManager()
