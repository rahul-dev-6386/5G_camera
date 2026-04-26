import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request

from .config import get_settings
from .exceptions import RateLimitError
from .logger import get_logger


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    
    def __init__(self, requests: int, period: int):
        self.requests = requests
        self.period = period
        self.requests_by_ip: dict[str, list[float]] = defaultdict(list)
        self.logger = get_logger(__name__)
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if the identifier is allowed to make a request."""
        now = time.time()
        
        # Clean old requests
        cutoff = now - self.period
        self.requests_by_ip[identifier] = [
            timestamp for timestamp in self.requests_by_ip[identifier]
            if timestamp > cutoff
        ]
        
        # Check if under limit
        if len(self.requests_by_ip[identifier]) >= self.requests:
            self.logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra_data={
                    "identifier": identifier,
                    "requests": len(self.requests_by_ip[identifier]),
                    "limit": self.requests
                }
            )
            return False
        
        # Add current request
        self.requests_by_ip[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for the identifier."""
        now = time.time()
        cutoff = now - self.period
        self.requests_by_ip[identifier] = [
            timestamp for timestamp in self.requests_by_ip[identifier]
            if timestamp > cutoff
        ]
        return max(0, self.requests - len(self.requests_by_ip[identifier]))


# Global rate limiter instance
settings = get_settings()
rate_limiter = RateLimiter(
    requests=settings.rate_limit_requests,
    period=settings.rate_limit_period
)


def check_rate_limit(request: Request, identifier: Optional[str] = None) -> None:
    """Check rate limit for a request and raise exception if exceeded."""
    client_ip = identifier or request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip):
        remaining = rate_limiter.get_remaining(client_ip)
        raise RateLimitError(
            f"Rate limit exceeded. Try again in {settings.rate_limit_period} seconds.",
            details={
                "limit": settings.rate_limit_requests,
                "period": settings.rate_limit_period,
                "remaining": remaining
            }
        )
