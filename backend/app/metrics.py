"""Prometheus metrics collection for the application."""

from prometheus_client import Counter, Gauge, Histogram, Info, CollectorRegistry, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from fastapi import Response
from typing import Optional

from .logger import get_logger


class MetricsManager:
    """Manages Prometheus metrics for the application."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.registry = CollectorRegistry()
        
        # Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Detection metrics
        self.detections_total = Counter(
            'detections_total',
            'Total person detections',
            ['classroom', 'course_code'],
            registry=self.registry
        )
        
        self.detection_duration_seconds = Histogram(
            'detection_duration_seconds',
            'Detection duration in seconds',
            ['processing_mode'],
            registry=self.registry
        )
        
        self.people_count = Gauge(
            'people_count',
            'Current number of people detected',
            ['classroom', 'course_code'],
            registry=self.registry
        )
        
        # Camera metrics
        self.camera_connections = Gauge(
            'camera_connections',
            'Number of active camera connections',
            ['user_id'],
            registry=self.registry
        )
        
        self.camera_frame_errors = Counter(
            'camera_frame_errors',
            'Total camera frame read errors',
            ['camera_id'],
            registry=self.registry
        )
        
        self.camera_health_status = Gauge(
            'camera_health_status',
            'Camera health status (1=healthy, 0.5=degraded, 0=unhealthy)',
            ['camera_id'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_operations_total = Counter(
            'database_operations_total',
            'Total database operations',
            ['operation', 'collection'],
            registry=self.registry
        )
        
        self.database_operation_duration_seconds = Histogram(
            'database_operation_duration_seconds',
            'Database operation duration in seconds',
            ['operation', 'collection'],
            registry=self.registry
        )
        
        # Auth metrics
        self.auth_attempts_total = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['type', 'status'],
            registry=self.registry
        )
        
        # Alert metrics
        self.alerts_total = Counter(
            'alerts_total',
            'Total alerts triggered',
            ['severity', 'alert_type'],
            registry=self.registry
        )
        
        # System info
        self.app_info = Info(
            'app_info',
            'Application information',
            registry=self.registry
        )
        self.app_info.info({
            'version': '2.0.0',
            'name': 'smart-campus-occupancy'
        })
        
        self.logger.info("Prometheus metrics initialized")
    
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """Record an HTTP request."""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        self.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_detection(self, classroom: str, course_code: str, count: int, duration: float, processing_mode: str) -> None:
        """Record a detection event."""
        self.detections_total.labels(classroom=classroom, course_code=course_code).inc()
        self.detection_duration_seconds.labels(processing_mode=processing_mode).observe(duration)
        self.people_count.labels(classroom=classroom, course_code=course_code).set(count)
    
    def record_camera_connection(self, user_id: str, count: int) -> None:
        """Record camera connection count."""
        self.camera_connections.labels(user_id=user_id).set(count)
    
    def record_camera_error(self, camera_id: str) -> None:
        """Record a camera frame error."""
        self.camera_frame_errors.labels(camera_id=camera_id).inc()
    
    def record_camera_health(self, camera_id: str, status: str) -> None:
        """Record camera health status."""
        status_value = 1.0 if status == "healthy" else 0.5 if status == "degraded" else 0.0
        self.camera_health_status.labels(camera_id=camera_id).set(status_value)
    
    def record_database_operation(self, operation: str, collection: str, duration: float) -> None:
        """Record a database operation."""
        self.database_operations_total.labels(operation=operation, collection=collection).inc()
        self.database_operation_duration_seconds.labels(operation=operation, collection=collection).observe(duration)
    
    def record_auth_attempt(self, auth_type: str, status: str) -> None:
        """Record an authentication attempt."""
        self.auth_attempts_total.labels(type=auth_type, status=status).inc()
    
    def record_alert(self, severity: str, alert_type: str) -> None:
        """Record an alert."""
        self.alerts_total.labels(severity=severity, alert_type=alert_type).inc()
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)


# Global metrics manager instance
metrics_manager = MetricsManager()


def get_metrics_response() -> Response:
    """Get metrics response for Prometheus endpoint."""
    return Response(
        content=metrics_manager.get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )
