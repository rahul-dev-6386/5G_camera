import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .logger import get_logger


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeout limits."""
    
    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            if process_time > self.timeout:
                self.logger.warning(
                    f"Request to {request.url.path} took {process_time:.2f}s "
                    f"(exceeds timeout of {self.timeout}s)"
                )
            
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            self.logger.error(
                f"Request to {request.url.path} failed after {process_time:.2f}s: {str(e)}",
                exc_info=True
            )
            raise


class ErrorResponseMiddleware(BaseHTTPMiddleware):
    """Middleware to handle errors consistently and return structured responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            self.logger.error(
                f"Unhandled error on {request.method} {request.url.path}: {str(e)}",
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error_type": type(e).__name__,
                    "path": str(request.url.path)
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        self.logger.info(
            f"Incoming request: {request.method} {request.url.path}"
        )
        
        response = await call_next(request)
        process_time = time.time() - start_time
        
        self.logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        return response
