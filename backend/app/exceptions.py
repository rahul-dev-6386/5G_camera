"""Custom exception types for the application."""


class ApplicationException(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(ApplicationException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(ApplicationException):
    """Raised when authorization fails (user doesn't have permission)."""
    pass


class ValidationError(ApplicationException):
    """Raised when input validation fails."""
    pass


class NotFoundError(ApplicationException):
    """Raised when a requested resource is not found."""
    pass


class ConflictError(ApplicationException):
    """Raised when a resource already exists or conflicts with existing data."""
    pass


class RateLimitError(ApplicationException):
    """Raised when rate limit is exceeded."""
    pass


class CameraError(ApplicationException):
    """Raised when camera operations fail."""
    pass


class DetectionError(ApplicationException):
    """Raised when detection operations fail."""
    pass


class DatabaseError(ApplicationException):
    """Raised when database operations fail."""
    pass


class ConfigurationError(ApplicationException):
    """Raised when configuration is invalid."""
    pass


class NetworkError(ApplicationException):
    """Raised when network operations fail."""
    pass
