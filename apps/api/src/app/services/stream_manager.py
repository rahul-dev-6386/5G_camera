from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import quote, urlsplit, urlunsplit

import cv2


class StreamSessionError(RuntimeError):
    pass


@dataclass
class CameraSession:
    camera_id: str
    stream_url: str
    capture_url: str
    capture: cv2.VideoCapture
    connected_at: str
    connection_type: str
    sim_provider: str | None = None
    sim_number_masked: str | None = None
    sim_apn: str | None = None
    plmn: str | None = None
    router_wan_ip: str | None = None
    router_lan_ip: str | None = None
    camera_host: str | None = None
    camera_port: int | None = None
    stream_path: str | None = None
    stream_protocol: str | None = None
    prefer_router_wan_host: bool = False


class StreamManager:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, CameraSession]] = {}
        self._lock = Lock()

    def _mask_identifier(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        if len(cleaned) <= 4:
            return "*" * len(cleaned)
        return f"{'*' * (len(cleaned) - 4)}{cleaned[-4:]}"

    def _build_stream_url_from_profile(self, config: dict) -> str:
        stream_url = (config.get("stream_url") or "").strip()
        if stream_url:
            return stream_url

        camera_host = (config.get("camera_host") or "").strip()
        router_wan_ip = (config.get("router_wan_ip") or "").strip()
        prefer_router_wan_host = bool(config.get("prefer_router_wan_host", False))
        host = router_wan_ip if (prefer_router_wan_host and router_wan_ip) else camera_host
        if not host:
            return ""

        protocol = (config.get("stream_protocol") or "rtsp").strip().lower()
        if protocol not in {"rtsp", "http", "https"}:
            raise StreamSessionError("Unsupported stream protocol. Use rtsp, http, or https.")

        raw_path = (config.get("stream_path") or "").strip() or "/avstream/channel=1/stream=1.sdp"
        normalized_path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        if protocol == "rtsp":
            port = int(config.get("camera_port") or 554)
        elif protocol == "https":
            port = int(config.get("camera_port") or 443)
        else:
            port = int(config.get("camera_port") or 80)

        return f"{protocol}://{host}:{port}{normalized_path}"

    def _open_capture(self, stream_url: str) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(stream_url)
        if not capture.isOpened():
            capture.release()
            raise StreamSessionError("Unable to open the camera stream. Verify the URL and camera availability.")

        success, _ = capture.read()
        if not success:
            capture.release()
            raise StreamSessionError("Connected to the stream, but no frames were received from the camera.")
        return capture

    def _build_authenticated_stream_url(self, stream_url: str, username: str, password: str) -> str:
        if not username:
            return stream_url

        try:
            parsed = urlsplit(stream_url)
        except ValueError as exc:
            raise StreamSessionError("Invalid stream URL format.") from exc

        if not parsed.scheme or not parsed.netloc:
            return stream_url

        hostname = parsed.hostname or ""
        if not hostname:
            return stream_url
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"

        try:
            parsed_port = parsed.port
        except ValueError as exc:
            raise StreamSessionError("Invalid stream URL format.") from exc
        port = f":{parsed_port}" if parsed_port else ""
        auth_segment = quote(username, safe="")
        if password:
            auth_segment = f"{auth_segment}:{quote(password, safe='')}"
        netloc = f"{auth_segment}@{hostname}{port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    def _sanitize_stream_url(self, stream_url: str) -> str:
        try:
            parsed = urlsplit(stream_url)
        except ValueError:
            return stream_url

        if not parsed.scheme or not parsed.netloc:
            return stream_url

        hostname = parsed.hostname or ""
        if not hostname:
            return stream_url
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"

        try:
            parsed_port = parsed.port
        except ValueError:
            return stream_url
        port = f":{parsed_port}" if parsed_port else ""
        userinfo = ""
        if parsed.username:
            userinfo = "***:***@"
        netloc = f"{userinfo}{hostname}{port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    def connect(
        self,
        user_id: str,
        stream_url: str | None,
        stream_username: str | None = None,
        stream_password: str | None = None,
        connection_type: str = "standard",
        sim_provider: str | None = None,
        sim_number: str | None = None,
        sim_apn: str | None = None,
        plmn: str | None = None,
        router_wan_ip: str | None = None,
        router_lan_ip: str | None = None,
        camera_host: str | None = None,
        camera_port: int | None = None,
        stream_path: str | None = None,
        stream_protocol: str | None = None,
        prefer_router_wan_host: bool = False,
    ) -> CameraSession:
        normalized_url = (stream_url or "").strip()

        normalized_username = (stream_username or "").strip()
        normalized_password = (stream_password or "").strip()
        if normalized_password and not normalized_username:
            raise StreamSessionError("Stream username is required when a stream password is provided.")

        return self.connect_many(
            user_id,
            [
                {
                    "camera_id": "cam_1",
                    "stream_url": normalized_url,
                    "stream_username": normalized_username,
                    "stream_password": normalized_password,
                    "connection_type": connection_type,
                    "sim_provider": sim_provider,
                    "sim_number": sim_number,
                    "sim_apn": sim_apn,
                    "plmn": plmn,
                    "router_wan_ip": router_wan_ip,
                    "router_lan_ip": router_lan_ip,
                    "camera_host": camera_host,
                    "camera_port": camera_port,
                    "stream_path": stream_path,
                    "stream_protocol": stream_protocol,
                    "prefer_router_wan_host": prefer_router_wan_host,
                }
            ],
        )[0]

    def connect_many(self, user_id: str, camera_configs: list[dict]) -> list[CameraSession]:
        if not camera_configs:
            raise StreamSessionError("Provide at least one camera stream.")

        next_sessions: dict[str, CameraSession] = {}
        opened_captures: list[cv2.VideoCapture] = []
        connected_at = datetime.now(timezone.utc).isoformat()

        try:
            for index, item in enumerate(camera_configs):
                camera_id = (item.get("camera_id") or f"cam_{index + 1}").strip()
                stream_url = self._build_stream_url_from_profile(item)
                stream_username = (item.get("stream_username") or "").strip()
                stream_password = (item.get("stream_password") or "").strip()
                connection_type = (item.get("connection_type") or "standard").strip().lower()
                sim_provider = (item.get("sim_provider") or "").strip()
                sim_number = (item.get("sim_number") or "").strip()
                sim_apn = (item.get("sim_apn") or "").strip()
                plmn = (item.get("plmn") or "").strip()
                router_wan_ip = (item.get("router_wan_ip") or "").strip()
                router_lan_ip = (item.get("router_lan_ip") or "").strip()
                camera_host = (item.get("camera_host") or "").strip()
                camera_port = int(item.get("camera_port") or 0) or None
                stream_path = (item.get("stream_path") or "").strip()
                stream_protocol = (item.get("stream_protocol") or "rtsp").strip().lower()
                prefer_router_wan_host = bool(item.get("prefer_router_wan_host", False))
                if not camera_id:
                    raise StreamSessionError("Each camera needs a non-empty camera ID.")
                if not stream_url:
                    raise StreamSessionError(f"Camera '{camera_id}' is missing stream URL or camera host profile data.")
                if stream_password and not stream_username:
                    raise StreamSessionError(f"Camera '{camera_id}' requires a stream username when password is provided.")
                if connection_type not in {"standard", "sim_5g"}:
                    raise StreamSessionError(f"Camera '{camera_id}' has unsupported connection type '{connection_type}'.")
                if connection_type == "sim_5g":
                    if not (camera_host or router_wan_ip or stream_url):
                        raise StreamSessionError(
                            f"Camera '{camera_id}' requires a reachable host or stream URL for 5G SIM mode."
                        )
                if camera_id in next_sessions:
                    raise StreamSessionError(f"Duplicate camera ID '{camera_id}' detected.")

                capture_url = self._build_authenticated_stream_url(stream_url, stream_username, stream_password)
                capture = self._open_capture(capture_url)
                opened_captures.append(capture)
                next_sessions[camera_id] = CameraSession(
                    camera_id=camera_id,
                    stream_url=self._sanitize_stream_url(capture_url),
                    capture_url=capture_url,
                    capture=capture,
                    connected_at=connected_at,
                    connection_type=connection_type,
                    sim_provider=sim_provider or None,
                    sim_number_masked=self._mask_identifier(sim_number) or None,
                    sim_apn=sim_apn or None,
                    plmn=plmn or None,
                    router_wan_ip=router_wan_ip or None,
                    router_lan_ip=router_lan_ip or None,
                    camera_host=camera_host or None,
                    camera_port=camera_port,
                    stream_path=stream_path or None,
                    stream_protocol=stream_protocol or None,
                    prefer_router_wan_host=prefer_router_wan_host,
                )
        except Exception:
            for capture in opened_captures:
                capture.release()
            raise

        with self._lock:
            previous_sessions = self._sessions.pop(user_id, {})
            self._sessions[user_id] = next_sessions

        for session in previous_sessions.values():
            session.capture.release()

        return list(next_sessions.values())

    def disconnect(self, user_id: str) -> bool:
        with self._lock:
            sessions = self._sessions.pop(user_id, {})

        if not sessions:
            return False

        for session in sessions.values():
            session.capture.release()
        return True

    def get_status(self, user_id: str) -> dict:
        with self._lock:
            sessions = dict(self._sessions.get(user_id, {}))

        if not sessions:
            return {"connected": False, "stream_url": None, "connected_at": None}

        first_session = next(iter(sessions.values()))
        return {
            "connected": True,
            "stream_url": first_session.stream_url,
            "connected_at": first_session.connected_at,
            "connection_type": first_session.connection_type,
            "sim_provider": first_session.sim_provider,
            "sim_number_masked": first_session.sim_number_masked,
            "sim_apn": first_session.sim_apn,
            "plmn": first_session.plmn,
            "router_wan_ip": first_session.router_wan_ip,
            "router_lan_ip": first_session.router_lan_ip,
            "camera_host": first_session.camera_host,
            "camera_port": first_session.camera_port,
            "stream_path": first_session.stream_path,
            "stream_protocol": first_session.stream_protocol,
            "prefer_router_wan_host": first_session.prefer_router_wan_host,
        }

    def get_multi_status(self, user_id: str) -> dict:
        with self._lock:
            sessions = dict(self._sessions.get(user_id, {}))

        if not sessions:
            return {"connected": False, "camera_count": 0, "cameras": []}

        cameras = [
            {
                "camera_id": session.camera_id,
                "stream_url": session.stream_url,
                "connected_at": session.connected_at,
                "connection_type": session.connection_type,
                "sim_provider": session.sim_provider,
                "sim_number_masked": session.sim_number_masked,
                "sim_apn": session.sim_apn,
                "plmn": session.plmn,
                "router_wan_ip": session.router_wan_ip,
                "router_lan_ip": session.router_lan_ip,
                "camera_host": session.camera_host,
                "camera_port": session.camera_port,
                "stream_path": session.stream_path,
                "stream_protocol": session.stream_protocol,
                "prefer_router_wan_host": session.prefer_router_wan_host,
            }
            for session in sessions.values()
        ]
        cameras.sort(key=lambda item: item["camera_id"])
        return {"connected": True, "camera_count": len(cameras), "cameras": cameras}

    def _read_frame(self, user_id: str, camera_id: str, session: CameraSession) -> bytes:
        success, frame = session.capture.read()
        if not success:
            session.capture.release()
            replacement = cv2.VideoCapture(session.capture_url)
            if not replacement.isOpened():
                replacement.release()
                with self._lock:
                    current_sessions = self._sessions.get(user_id, {})
                    current = current_sessions.get(camera_id)
                    if current is session:
                        current_sessions.pop(camera_id, None)
                raise StreamSessionError(f"Stream '{camera_id}' was lost and could not be re-established.")

            retry_success, frame = replacement.read()
            if not retry_success:
                replacement.release()
                with self._lock:
                    current_sessions = self._sessions.get(user_id, {})
                    current = current_sessions.get(camera_id)
                    if current is session:
                        current_sessions.pop(camera_id, None)
                raise StreamSessionError(f"Stream '{camera_id}' is open, but no frames are currently available.")

            with self._lock:
                current_sessions = self._sessions.get(user_id, {})
                current = current_sessions.get(camera_id)
                if current is session:
                    current_sessions[camera_id] = CameraSession(
                        camera_id=session.camera_id,
                        stream_url=session.stream_url,
                        capture_url=session.capture_url,
                        capture=replacement,
                        connected_at=session.connected_at,
                        connection_type=session.connection_type,
                        sim_provider=session.sim_provider,
                        sim_number_masked=session.sim_number_masked,
                        sim_apn=session.sim_apn,
                        plmn=session.plmn,
                        router_wan_ip=session.router_wan_ip,
                        router_lan_ip=session.router_lan_ip,
                        camera_host=session.camera_host,
                        camera_port=session.camera_port,
                        stream_path=session.stream_path,
                        stream_protocol=session.stream_protocol,
                        prefer_router_wan_host=session.prefer_router_wan_host,
                    )
                else:
                    replacement.release()
                    raise StreamSessionError(f"The stream session for '{camera_id}' changed while reconnecting.")

        success, encoded = cv2.imencode(".jpg", frame)
        if not success:
            raise StreamSessionError(f"The stream frame for '{camera_id}' could not be encoded for detection.")
        return encoded.tobytes()

    def read_frame_bytes(self, user_id: str) -> bytes:
        with self._lock:
            sessions = dict(self._sessions.get(user_id, {}))

        if not sessions:
            raise StreamSessionError("No camera stream is connected for this account.")

        first_camera_id = sorted(sessions)[0]
        return self._read_frame(user_id, first_camera_id, sessions[first_camera_id])

    def read_multi_frame_bytes(self, user_id: str) -> list[dict]:
        with self._lock:
            sessions = dict(self._sessions.get(user_id, {}))

        if not sessions:
            raise StreamSessionError("No camera streams are connected for this account.")

        frames = []
        for camera_id in sorted(sessions):
            session = sessions[camera_id]
            frames.append(
                {
                    "camera_id": camera_id,
                    "stream_url": session.stream_url,
                    "frame_bytes": self._read_frame(user_id, camera_id, session),
                }
            )
        return frames

    def read_camera_frame_bytes(self, user_id: str, camera_id: str) -> bytes:
        with self._lock:
            sessions = dict(self._sessions.get(user_id, {}))

        if not sessions:
            raise StreamSessionError("No camera streams are connected for this account.")

        normalized_camera_id = camera_id.strip()
        if not normalized_camera_id:
            raise StreamSessionError("Camera ID is required.")

        session = sessions.get(normalized_camera_id)
        if not session:
            raise StreamSessionError(f"Camera '{normalized_camera_id}' is not connected.")

        return self._read_frame(user_id, normalized_camera_id, session)


stream_manager = StreamManager()
