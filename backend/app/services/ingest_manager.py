from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


class IngestSessionError(RuntimeError):
    pass


@dataclass
class IngestFrame:
    camera_id: str
    frame_bytes: bytes
    updated_at: str


class IngestManager:
    def __init__(self) -> None:
        self._frames: dict[str, dict[str, IngestFrame]] = {}
        self._lock = Lock()

    def upsert_frame(self, user_id: str, camera_id: str, frame_bytes: bytes) -> None:
        if not frame_bytes:
            raise IngestSessionError("Received empty frame payload.")

        updated_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            user_frames = self._frames.setdefault(user_id, {})
            user_frames[camera_id] = IngestFrame(camera_id=camera_id, frame_bytes=frame_bytes, updated_at=updated_at)

    def get_frame(self, user_id: str, camera_id: str) -> bytes:
        with self._lock:
            user_frames = self._frames.get(user_id, {})
            frame = user_frames.get(camera_id)
        if not frame:
            raise IngestSessionError(f"No ingested frame available for '{camera_id}'.")
        return frame.frame_bytes

    def get_multi_frames(self, user_id: str) -> list[dict]:
        with self._lock:
            user_frames = dict(self._frames.get(user_id, {}))

        if not user_frames:
            raise IngestSessionError("No ingested camera frames are available for this account.")

        return [
            {
                "camera_id": camera_id,
                "stream_url": f"socket://ingest/{camera_id}",
                "updated_at": frame.updated_at,
                "frame_bytes": frame.frame_bytes,
            }
            for camera_id, frame in sorted(user_frames.items())
        ]

    def get_status(self, user_id: str) -> dict:
        with self._lock:
            user_frames = dict(self._frames.get(user_id, {}))

        if not user_frames:
            return {"connected": False, "camera_count": 0, "cameras": []}

        cameras = [
            {
                "camera_id": camera_id,
                "stream_url": f"socket://ingest/{camera_id}",
                "connected_at": frame.updated_at,
                "connection_type": "standard",
            }
            for camera_id, frame in sorted(user_frames.items())
        ]
        return {"connected": True, "camera_count": len(cameras), "cameras": cameras}

    def clear_user(self, user_id: str) -> None:
        with self._lock:
            self._frames.pop(user_id, None)


ingest_manager = IngestManager()
