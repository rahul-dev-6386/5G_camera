"""Frame buffer queue for handling network jitter and smoothing frame delivery."""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..logger import get_logger


@dataclass
class Frame:
    """Represents a video frame with metadata."""
    bytes: bytes
    timestamp: str
    camera_id: str


class FrameBuffer:
    """Thread-safe frame buffer queue for handling network jitter."""
    
    def __init__(self, max_size: int = 10, camera_id: str = "default"):
        self.max_size = max_size
        self.camera_id = camera_id
        self.buffer: deque[Frame] = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def put(self, frame_bytes: bytes) -> None:
        """Add a frame to the buffer."""
        async with self.lock:
            frame = Frame(
                bytes=frame_bytes,
                timestamp=datetime.now(timezone.utc).isoformat(),
                camera_id=self.camera_id
            )
            self.buffer.append(frame)
            
            if len(self.buffer) == self.max_size:
                self.logger.warning(
                    f"Frame buffer full for camera {self.camera_id}, dropping oldest frame"
                )
    
    async def get(self) -> Optional[bytes]:
        """Get the latest frame from the buffer."""
        async with self.lock:
            if not self.buffer:
                return None
            
            # Return the most recent frame
            return self.buffer[-1].bytes
    
    async def get_all(self) -> list[bytes]:
        """Get all frames from the buffer and clear it."""
        async with self.lock:
            frames = [frame.bytes for frame in self.buffer]
            self.buffer.clear()
            return frames
    
    async def size(self) -> int:
        """Get current buffer size."""
        async with self.lock:
            return len(self.buffer)
    
    async def clear(self) -> None:
        """Clear all frames from the buffer."""
        async with self.lock:
            self.buffer.clear()
            self.logger.info(f"Frame buffer cleared for camera {self.camera_id}")
    
    async def get_latest_timestamp(self) -> Optional[str]:
        """Get the timestamp of the latest frame."""
        async with self.lock:
            if not self.buffer:
                return None
            return self.buffer[-1].timestamp


class FrameBufferManager:
    """Manages frame buffers for multiple cameras."""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.buffers: dict[str, FrameBuffer] = {}
        self.lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def get_buffer(self, camera_id: str) -> FrameBuffer:
        """Get or create a frame buffer for a camera."""
        async with self.lock:
            if camera_id not in self.buffers:
                self.buffers[camera_id] = FrameBuffer(
                    max_size=self.max_size,
                    camera_id=camera_id
                )
                self.logger.info(f"Created frame buffer for camera {camera_id}")
            return self.buffers[camera_id]
    
    async def put_frame(self, camera_id: str, frame_bytes: bytes) -> None:
        """Add a frame to the camera's buffer."""
        buffer = await self.get_buffer(camera_id)
        await buffer.put(frame_bytes)
    
    async def get_frame(self, camera_id: str) -> Optional[bytes]:
        """Get the latest frame from the camera's buffer."""
        buffer = await self.get_buffer(camera_id)
        return await buffer.get()
    
    async def clear_buffer(self, camera_id: str) -> None:
        """Clear the camera's buffer."""
        async with self.lock:
            if camera_id in self.buffers:
                await self.buffers[camera_id].clear()
                del self.buffers[camera_id]
    
    async def clear_all(self) -> None:
        """Clear all camera buffers."""
        async with self.lock:
            for buffer in self.buffers.values():
                await buffer.clear()
            self.buffers.clear()
            self.logger.info("All frame buffers cleared")
    
    async def get_status(self) -> dict[str, int]:
        """Get status of all buffers."""
        async with self.lock:
            return {
                camera_id: await buffer.size()
                for camera_id, buffer in self.buffers.items()
            }


# Global frame buffer manager
frame_buffer_manager = FrameBufferManager(max_size=10)
