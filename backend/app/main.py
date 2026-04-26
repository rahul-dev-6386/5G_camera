import base64
import json
import time
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

# Suppress common warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*float.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*invalid value.*")
warnings.filterwarnings("ignore", message=".*FP16.*")
warnings.filterwarnings("ignore", message=".*half precision.*")
warnings.filterwarnings("ignore", message=".*UserWarning.*")
warnings.filterwarnings("ignore", message=".*torch.*")

from fastapi import FastAPI, File, Header, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import get_database
from .exceptions import RateLimitError
from .logger import get_logger, setup_logging
from .middleware import ErrorResponseMiddleware, RequestLoggingMiddleware, RequestTimeoutMiddleware
from .metrics import get_metrics_response, metrics_manager
from .rate_limiter import check_rate_limit
from .schemas import (
    AuthResponse,
    ContextListResponse,
    ContextOption,
    DetectionResponse,
    LoginRequest,
    MultiStreamConnectRequest,
    MultiStreamStatusResponse,
    NetworkSimulationResponse,
    OccupancyRecord,
    ProcessingSimulationResponse,
    RefreshTokenRequest,
    SignupRequest,
    StatsResponse,
    StreamConnectRequest,
    StreamStatusResponse,
)
from .security import TokenError, create_jwt_token, decode_jwt_token, hash_password, validate_password_strength, verify_password
from .services.alerts import alert_manager
from .services.detector import detector, get_available_models
from .services.ingest_manager import IngestSessionError, ingest_manager
from .services.multi_camera import fuse_camera_detections
from .services.network import NETWORK_DELAYS_MS, PROCESSING_DELAYS_MS, simulate_network, simulate_processing
from .services.stream_manager import StreamSessionError, stream_manager


# Initialize logging
setup_logging()
logger = get_logger(__name__)

settings = get_settings()
app = FastAPI(
    title="Smart Campus Occupancy & Attendance System",
    description="""
Real-time person detection with YOLOv8, occupancy analytics, and attendance logging through a FastAPI backend and React dashboard.

## Features
- Real-time YOLOv8 person-only detection
- Occupancy counting with annotated frames
- JWT-based authentication (signup, login, refresh, logout)
- Multiple stream modes: browser webcam, direct camera URL, multi-camera pull, and socket ingest
- Multi-camera fusion to reduce duplicate counts across overlapping feeds
- Capacity threshold alerts
- Real-time analytics and time-series aggregation
- Prometheus metrics for monitoring
""",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and session management endpoints"
        },
        {
            "name": "Detection",
            "description": "Person detection and occupancy counting endpoints"
        },
        {
            "name": "Streaming",
            "description": "Camera stream management endpoints"
        },
        {
            "name": "Analytics",
            "description": "Occupancy analytics and statistics endpoints"
        },
        {
            "name": "System",
            "description": "Health checks and system monitoring endpoints"
        }
    ]
)

# Add middleware
app.add_middleware(ErrorResponseMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestTimeoutMiddleware, timeout=settings.request_timeout)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_DIST = PROJECT_ROOT / "apps" / "web" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


def normalize_username(username: str) -> str:
    return username.strip().lower()


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token required.")
    return authorization.split(" ", 1)[1].strip()


def build_auth_response(user: dict) -> AuthResponse:
    access_token = create_jwt_token(
        subject=user["username"],
        secret_key=settings.jwt_secret_key,
        expires_delta=timedelta(minutes=settings.jwt_access_exp_minutes),
        token_type="access",
    )
    refresh_token = create_jwt_token(
        subject=user["username"],
        secret_key=settings.jwt_secret_key,
        expires_delta=timedelta(days=settings.jwt_refresh_exp_days),
        token_type="refresh",
    )
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        username=user["username"],
        full_name=user["full_name"],
    )


async def persist_refresh_session(username: str, refresh_token: str) -> None:
    database = await get_database()
    payload = decode_jwt_token(refresh_token, settings.jwt_secret_key, "refresh")
    await database.refresh_sessions.insert_one(
        {
            "username": username,
            "jti": payload["jti"],
            "expires_at": datetime.fromtimestamp(payload["exp"], tz=UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )


async def get_current_user(authorization: str | None) -> dict:
    token = extract_bearer_token(authorization)
    try:
        payload = decode_jwt_token(token, settings.jwt_secret_key, "access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    database = await get_database()
    user = await database.users.find_one(
        {"username": payload["sub"]},
        {"password_hash": 0, "password_salt": 0},
    )
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")
    return user


def build_occupancy_record(item: dict) -> OccupancyRecord:
    return OccupancyRecord(
        timestamp=item["timestamp"],
        count=item["count"],
        network_mode=item.get("network_mode", "5g"),
        processing_mode=item.get("processing_mode", "edge"),
        latency_ms=item.get("latency_ms", 0.0),
        network_delay_ms=item.get("network_delay_ms", 0.0),
        processing_delay_ms=item.get("processing_delay_ms", 0.0),
        source=item.get("source", "camera"),
        classroom=item.get("classroom", "General"),
        course_code=item.get("course_code", "GEN-101"),
        camera_count=item.get("camera_count", 1),
        camera_counts=item.get("camera_counts", {}),
    )


def get_current_user_from_access_token(token: str) -> dict:
    try:
        payload = decode_jwt_token(token, settings.jwt_secret_key, "access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return {"username": payload["sub"]}


async def process_detection(
    image_bytes: bytes | None,
    *,
    user: dict,
    mode: Literal["5g"],
    processing_mode: Literal["edge", "cloud"],
    classroom: str,
    course_code: str,
    source: str,
    detection_result: dict | None = None,
    fused_count: int | None = None,
    camera_count: int = 1,
    camera_counts: dict[str, int] | None = None,
) -> DetectionResponse:
    await simulate_network(mode)
    await simulate_processing(processing_mode)

    if detection_result is None and not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    started = time.perf_counter()
    result = detection_result or detector.detect_people(image_bytes)
    inference_ms = round((time.perf_counter() - started) * 1000, 2)
    resolved_count = fused_count if fused_count is not None else result["count"]
    resolved_camera_counts = camera_counts or {}

    payload = {
        "timestamp": result["timestamp"],
        "count": resolved_count,
        "network_mode": mode,
        "processing_mode": processing_mode,
        "latency_ms": round(inference_ms + NETWORK_DELAYS_MS[mode] + PROCESSING_DELAYS_MS[processing_mode], 2),
        "network_delay_ms": float(NETWORK_DELAYS_MS[mode]),
        "processing_delay_ms": float(PROCESSING_DELAYS_MS[processing_mode]),
        "source": source,
        "classroom": classroom.strip(),
        "course_code": course_code.strip().upper(),
        "user_id": user["username"],
        "username": user["username"],
        "camera_count": camera_count,
        "camera_counts": resolved_camera_counts,
    }

    database = await get_database()
    await database.occupancy_logs.insert_one(payload)
    
    # Check for capacity alerts
    alert = alert_manager.check_occupancy(classroom, course_code, resolved_count)
    if alert:
        logger.warning(
            f"Capacity alert triggered: {classroom} - {resolved_count}/{alert.threshold}"
        )

    return DetectionResponse(
        count=resolved_count,
        timestamp=result["timestamp"],
        latency_ms=payload["latency_ms"],
        network_mode=mode,
        processing_mode=processing_mode,
        network_delay_ms=payload["network_delay_ms"],
        processing_delay_ms=payload["processing_delay_ms"],
        source=payload["source"],
        classroom=payload["classroom"],
        course_code=payload["course_code"],
        image_base64=result["image_base64"],
        camera_count=camera_count,
        camera_counts=resolved_camera_counts,
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    if settings.enable_mongodb:
        try:
            from .mongodb_db import mongodb
            await mongodb.connect()
            logger.info("MongoDB connection established on startup")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    if settings.enable_mongodb:
        try:
            from .mongodb_db import mongodb
            await mongodb.close()
            logger.info("MongoDB connection closed on shutdown")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns basic health status of the application.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0"
    }


@app.get("/status", tags=["System"])
async def system_status():
    """
    System status endpoint.
    
    Returns detailed system status including database connection information.
    """
    from .config import get_settings
    settings = get_settings()
    
    db_info = {
        "type": "local_json" if not settings.enable_mongodb else "mongodb",
        "mongodb_enabled": settings.enable_mongodb,
        "mongodb_uri": settings.mongodb_uri if settings.enable_mongodb else None,
        "mongodb_db_name": settings.mongodb_db_name if settings.enable_mongodb else None,
    }
    
    if settings.enable_mongodb:
        try:
            from .mongodb_db import mongodb
            if mongodb.db:
                db_info["mongodb_connected"] = True
                db_info["mongodb_status"] = "connected"
            else:
                db_info["mongodb_connected"] = False
                db_info["mongodb_status"] = "not_connected"
        except Exception as e:
            db_info["mongodb_connected"] = False
            db_info["mongodb_status"] = f"error: {str(e)}"
    
    return {
        "status": "operational",
        "timestamp": datetime.now(UTC).isoformat(),
        "database": db_info,
        "storage_dir": settings.storage_dir,
    }


@app.get("/metrics", tags=["System"])
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns application metrics in Prometheus format for monitoring and alerting.
    """
    return get_metrics_response()


@app.post("/auth/signup", response_model=AuthResponse, tags=["Authentication"])
async def signup(payload: SignupRequest, request: Request) -> AuthResponse:
    """
    Register a new user account.
    
    Creates a new user with the provided credentials. The password must meet strength requirements:
    - At least 8 characters
    - Contains uppercase and lowercase letters
    - Contains at least one digit
    - Not a common password
    
    **Example Request:**
    ```json
    {
      "username": "johndoe",
      "password": "SecureP@ssw0rd",
      "full_name": "John Doe"
    }
    ```
    
    **Example Response:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "username": "johndoe",
      "full_name": "John Doe"
    }
    ```
    """
    check_rate_limit(request)
    
    # Validate password strength
    is_strong, message = validate_password_strength(payload.password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=message)
    
    database = await get_database()
    username = normalize_username(payload.username)
    existing_user = await database.users.find_one({"username": username})
    if existing_user:
        raise HTTPException(status_code=409, detail="Username already exists.")

    password_salt, password_hash = hash_password(payload.password)
    user_doc = {
        "_id": username,
        "username": username,
        "full_name": payload.full_name.strip(),
        "password_salt": password_salt,
        "password_hash": password_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }
    await database.users.insert_one(user_doc)

    auth_response = build_auth_response(user_doc)
    await persist_refresh_session(user_doc["username"], auth_response.refresh_token)
    logger.info(f"New user registered: {username}")
    return auth_response


@app.post("/auth/login", response_model=AuthResponse, tags=["Authentication"])
async def login(payload: LoginRequest, request: Request) -> AuthResponse:
    """
    Authenticate a user and return access tokens.
    
    Validates user credentials and returns JWT access and refresh tokens.
    The access token is valid for 15 minutes by default.
    
    **Example Request:**
    ```json
    {
      "username": "johndoe",
      "password": "SecureP@ssw0rd"
    }
    ```
    
    **Example Response:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "username": "johndoe",
      "full_name": "John Doe"
    }
    ```
    """
    check_rate_limit(request)
    
    database = await get_database()
    username = normalize_username(payload.username)
    user = await database.users.find_one({"username": username})
    if not user or not verify_password(payload.password, user["password_salt"], user["password_hash"]):
        logger.warning(f"Failed login attempt for username: {username}")
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    auth_response = build_auth_response(user)
    await persist_refresh_session(user["username"], auth_response.refresh_token)
    logger.info(f"User logged in: {username}")
    return auth_response


@app.post("/auth/refresh", response_model=AuthResponse, tags=["Authentication"])
async def refresh_token(payload: RefreshTokenRequest) -> AuthResponse:
    try:
        decoded = decode_jwt_token(payload.refresh_token, settings.jwt_secret_key, "refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    database = await get_database()
    refresh_session = await database.refresh_sessions.find_one({"jti": decoded["jti"], "username": decoded["sub"]})
    if not refresh_session:
        raise HTTPException(status_code=401, detail="Refresh session not found.")

    user = await database.users.find_one({"username": decoded["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")

    await database.refresh_sessions.delete_one({"jti": decoded["jti"], "username": decoded["sub"]})
    auth_response = build_auth_response(user)
    await persist_refresh_session(user["username"], auth_response.refresh_token)
    return auth_response


@app.post("/auth/logout", tags=["Authentication"])
async def logout(payload: RefreshTokenRequest) -> dict:
    try:
        decoded = decode_jwt_token(payload.refresh_token, settings.jwt_secret_key, "refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    database = await get_database()
    await database.refresh_sessions.delete_one({"jti": decoded["jti"], "username": decoded["sub"]})
    return {"status": "logged_out"}


@app.post("/detect", response_model=DetectionResponse, tags=["Detection"])
async def detect_people(
    file: UploadFile = File(...),
    mode: Literal["5g"] = Query(default="5g"),
    processing_mode: Literal["edge", "cloud"] = Query(default="edge"),
    classroom: str = Query(..., min_length=1, max_length=100),
    course_code: str = Query(..., min_length=1, max_length=50),
    authorization: str | None = Header(default=None),
) -> DetectionResponse:
    user = await get_current_user(authorization)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image frame.")

    image_bytes = await file.read()
    return await process_detection(
        image_bytes,
        user=user,
        mode=mode,
        processing_mode=processing_mode,
        classroom=classroom,
        course_code=course_code,
        source="webcam",
    )


@app.get("/stream/status", response_model=StreamStatusResponse, tags=["Streaming"])
async def get_stream_status(authorization: str | None = Header(default=None)) -> StreamStatusResponse:
    user = await get_current_user(authorization)
    return StreamStatusResponse(**stream_manager.get_status(user["username"]))


@app.get("/multi-stream/status", response_model=MultiStreamStatusResponse, tags=["Streaming"])
async def get_multi_stream_status(authorization: str | None = Header(default=None)) -> MultiStreamStatusResponse:
    user = await get_current_user(authorization)
    return MultiStreamStatusResponse(
        **stream_manager.get_multi_status(user["username"]),
    )


@app.post("/stream/connect", response_model=StreamStatusResponse, tags=["Streaming"])
async def connect_stream(
    payload: StreamConnectRequest,
    authorization: str | None = Header(default=None),
) -> StreamStatusResponse:
    user = await get_current_user(authorization)
    try:
        session = stream_manager.connect(
            user["username"],
            payload.stream_url,
            payload.stream_username,
            payload.stream_password,
            payload.connection_type,
            payload.sim_provider,
            payload.sim_number,
            payload.sim_apn,
            payload.plmn,
            payload.router_wan_ip,
            payload.router_lan_ip,
            payload.camera_host,
            payload.camera_port,
            payload.stream_path,
            payload.stream_protocol,
            payload.prefer_router_wan_host,
        )
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamStatusResponse(
        connected=True,
        stream_url=session.stream_url,
        connected_at=session.connected_at,
    )


@app.post("/multi-stream/connect", response_model=MultiStreamStatusResponse, tags=["Streaming"])
async def connect_multi_stream(
    payload: MultiStreamConnectRequest,
    authorization: str | None = Header(default=None),
) -> MultiStreamStatusResponse:
    user = await get_current_user(authorization)
    try:
        stream_manager.connect_many(
            user["username"],
            [
                {
                    "camera_id": item.camera_id or f"cam_{index + 1}",
                    "stream_url": item.stream_url,
                    "stream_username": item.stream_username,
                    "stream_password": item.stream_password,
                    "connection_type": item.connection_type,
                    "sim_provider": item.sim_provider,
                    "sim_number": item.sim_number,
                    "sim_apn": item.sim_apn,
                    "plmn": item.plmn,
                    "router_wan_ip": item.router_wan_ip,
                    "router_lan_ip": item.router_lan_ip,
                    "camera_host": item.camera_host,
                    "camera_port": item.camera_port,
                    "stream_path": item.stream_path,
                    "stream_protocol": item.stream_protocol,
                    "prefer_router_wan_host": item.prefer_router_wan_host,
                }
                for index, item in enumerate(payload.cameras)
            ],
        )
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MultiStreamStatusResponse(**stream_manager.get_multi_status(user["username"]))


@app.post("/stream/disconnect", tags=["Streaming"], response_model=StreamStatusResponse)
async def disconnect_stream(authorization: str | None = Header(default=None)) -> StreamStatusResponse:
    user = await get_current_user(authorization)
    stream_manager.disconnect(user["username"])
    return StreamStatusResponse(connected=False, stream_url=None, connected_at=None)


@app.post("/multi-stream/disconnect", response_model=MultiStreamStatusResponse, tags=["Streaming"])
async def disconnect_multi_stream(authorization: str | None = Header(default=None)) -> MultiStreamStatusResponse:
    user = await get_current_user(authorization)
    stream_manager.disconnect(user["username"])
    return MultiStreamStatusResponse(connected=False, camera_count=0, cameras=[])


@app.get("/ingest/status", response_model=MultiStreamStatusResponse, tags=["Streaming"])
async def get_ingest_status(authorization: str | None = Header(default=None)) -> MultiStreamStatusResponse:
    user = await get_current_user(authorization)
    return MultiStreamStatusResponse(**ingest_manager.get_status(user["username"]))


@app.get("/ingest/frame/{camera_id}", response_model=None, tags=["Streaming"])
async def get_ingest_frame(camera_id: str, authorization: str | None = Header(default=None)) -> Response:
    user = await get_current_user(authorization)
    try:
        frame_bytes = ingest_manager.get_frame(user["username"], camera_id)
    except IngestSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=frame_bytes, media_type="image/jpeg")


@app.post("/ingest/detect", response_model=DetectionResponse, tags=["Detection"])
async def detect_ingest_frame(
    mode: Literal["5g"] = Query(default="5g"),
    processing_mode: Literal["edge", "cloud"] = Query(default="edge"),
    classroom: str = Query(..., min_length=1, max_length=100),
    course_code: str = Query(..., min_length=1, max_length=50),
    authorization: str | None = Header(default=None),
) -> DetectionResponse:
    user = await get_current_user(authorization)
    try:
        frames = ingest_manager.get_multi_frames(user["username"])
    except IngestSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    camera_results = [{"camera_id": item["camera_id"], "result": detector.detect_people(item["frame_bytes"])} for item in frames]
    fused = fuse_camera_detections(camera_results)
    detection_result = {
        "count": fused["count"],
        "timestamp": camera_results[0]["result"]["timestamp"] if camera_results else time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "image_base64": fused["image_base64"],
    }
    return await process_detection(
        None,
        user=user,
        mode=mode,
        processing_mode=processing_mode,
        classroom=classroom,
        course_code=course_code,
        source="socket_ingest",
        detection_result=detection_result,
        fused_count=fused["count"],
        camera_count=fused["camera_count"],
        camera_counts=fused["camera_counts"],
    )


@app.websocket("/ws/ingest/{camera_id}")
async def ingest_camera_stream(websocket: WebSocket, camera_id: str, token: str | None = Query(default=None)) -> None:
    if not token:
        await websocket.close(code=4401)
        return

    try:
        user = get_current_user_from_access_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    username = user["username"]

    try:
        while True:
            message = await websocket.receive()
            frame_bytes = message.get("bytes")
            if frame_bytes is None and message.get("text"):
                text_payload = message["text"]
                try:
                    parsed = json.loads(text_payload)
                    image_b64 = parsed.get("image_base64", "")
                    frame_bytes = base64.b64decode(image_b64) if image_b64 else None
                except Exception:
                    frame_bytes = None

            if not frame_bytes:
                await websocket.send_json({"status": "ignored", "reason": "empty_frame"})
                continue

            ingest_manager.upsert_frame(username, camera_id, frame_bytes)
            await websocket.send_json({"status": "ok", "camera_id": camera_id})
    except WebSocketDisconnect:
        return


@app.get("/stream/frame", response_model=None)
async def get_stream_frame(authorization: str | None = Header(default=None)) -> Response:
    user = await get_current_user(authorization)
    try:
        frame_bytes = stream_manager.read_frame_bytes(user["username"])
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(content=frame_bytes, media_type="image/jpeg")


@app.get("/multi-stream/frame", response_model=None)
async def get_multi_stream_frame(authorization: str | None = Header(default=None)) -> Response:
    user = await get_current_user(authorization)
    try:
        frames = stream_manager.read_multi_frame_bytes(user["username"])
        camera_results = [{"camera_id": item["camera_id"], "result": detector.detect_people(item["frame_bytes"])} for item in frames]
        fused = fuse_camera_detections(camera_results)
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(content=base64.b64decode(fused["image_base64"]), media_type="image/jpeg")


@app.get("/multi-stream/frame/{camera_id}", response_model=None)
async def get_single_multi_stream_frame(camera_id: str, authorization: str | None = Header(default=None)) -> Response:
    user = await get_current_user(authorization)
    try:
        frame_bytes = stream_manager.read_camera_frame_bytes(user["username"], camera_id)
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(content=frame_bytes, media_type="image/jpeg")


@app.post("/stream/detect", response_model=DetectionResponse)
async def detect_stream_frame(
    mode: Literal["5g"] = Query(default="5g"),
    processing_mode: Literal["edge", "cloud"] = Query(default="edge"),
    classroom: str = Query(..., min_length=1, max_length=100),
    course_code: str = Query(..., min_length=1, max_length=50),
    authorization: str | None = Header(default=None),
) -> DetectionResponse:
    user = await get_current_user(authorization)
    try:
        frame_bytes = stream_manager.read_frame_bytes(user["username"])
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await process_detection(
        frame_bytes,
        user=user,
        mode=mode,
        processing_mode=processing_mode,
        classroom=classroom,
        course_code=course_code,
        source="stream",
    )


@app.post("/multi-stream/detect", response_model=DetectionResponse)
async def detect_multi_stream_frame(
    mode: Literal["5g"] = Query(default="5g"),
    processing_mode: Literal["edge", "cloud"] = Query(default="edge"),
    classroom: str = Query(..., min_length=1, max_length=100),
    course_code: str = Query(..., min_length=1, max_length=50),
    authorization: str | None = Header(default=None),
) -> DetectionResponse:
    user = await get_current_user(authorization)
    try:
        frames = stream_manager.read_multi_frame_bytes(user["username"])
    except StreamSessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    camera_results = [{"camera_id": item["camera_id"], "result": detector.detect_people(item["frame_bytes"])} for item in frames]
    fused = fuse_camera_detections(camera_results)
    detection_result = {
        "count": fused["count"],
        "timestamp": camera_results[0]["result"]["timestamp"] if camera_results else time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "image_base64": fused["image_base64"],
    }
    return await process_detection(
        None,
        user=user,
        mode=mode,
        processing_mode=processing_mode,
        classroom=classroom,
        course_code=course_code,
        source="multi_stream",
        detection_result=detection_result,
        fused_count=fused["count"],
        camera_count=fused["camera_count"],
        camera_counts=fused["camera_counts"],
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats(
    limit: int = Query(default=20, ge=1, le=500),
    classroom: str | None = Query(default=None),
    course_code: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> StatsResponse:
    user = await get_current_user(authorization)
    database = await get_database()
    query: dict = {"user_id": user["username"]}
    if classroom:
        query["classroom"] = classroom.strip()
    if course_code:
        query["course_code"] = course_code.strip().upper()

    cursor = (
        database.occupancy_logs.find(
            query,
            {
                "_id": 0,
                "timestamp": 1,
                "count": 1,
                "network_mode": 1,
                "processing_mode": 1,
                "latency_ms": 1,
                "network_delay_ms": 1,
                "processing_delay_ms": 1,
                "source": 1,
                "classroom": 1,
                "course_code": 1,
                "camera_count": 1,
                "camera_counts": 1,
            },
        )
        .sort("timestamp", -1)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)

    history = [build_occupancy_record(item) for item in reversed(items)]
    latest = history[-1] if history else None
    return StatsResponse(history=history, latest=latest)


@app.get("/contexts", response_model=ContextListResponse, tags=["System"])
async def get_contexts(authorization: str | None = Header(default=None)) -> ContextListResponse:
    user = await get_current_user(authorization)
    database = await get_database()
    pipeline = [
        {"$match": {"user_id": user["username"]}},
        {"$group": {"_id": {"classroom": "$classroom", "course_code": "$course_code"}}},
        {"$sort": {"_id.classroom": 1, "_id.course_code": 1}},
    ]
    items = await database.occupancy_logs.aggregate(pipeline).to_list(length=None)
    return ContextListResponse(
        items=[
            ContextOption(
                classroom=item["_id"].get("classroom", "General"),
                course_code=item["_id"].get("course_code", "GEN-101"),
            )
            for item in items
        ]
    )


@app.get("/simulate-network", response_model=NetworkSimulationResponse, tags=["System"])
async def simulate_network_endpoint(mode: Literal["5g"] = Query(default="5g")) -> NetworkSimulationResponse:
    measured_response_ms = await simulate_network(mode)
    message = "Low latency mode (5G)"
    return NetworkSimulationResponse(
        mode=mode,
        simulated_delay_ms=NETWORK_DELAYS_MS[mode],
        measured_response_ms=measured_response_ms,
        message=message,
    )


@app.get("/simulate-processing", response_model=ProcessingSimulationResponse, tags=["System"])
async def simulate_processing_endpoint(mode: Literal["edge", "cloud"] = Query(default="edge")) -> ProcessingSimulationResponse:
    measured_response_ms = await simulate_processing(mode)
    message = "Edge inference path" if mode == "edge" else "Cloud inference path"
    return ProcessingSimulationResponse(
        mode=mode,
        simulated_delay_ms=PROCESSING_DELAYS_MS[mode],
        measured_response_ms=measured_response_ms,
        message=message,
    )


@app.get("/models", tags=["System"])
async def get_models_info() -> dict:
    """Get available models and hardware information."""
    return get_available_models()


@app.post("/models/select", tags=["System"])
async def select_model(model_name: str, authorization: str | None = Header(default=None)) -> dict:
    """Select a model for detection."""
    user = await get_current_user(authorization)
    
    models_info = get_available_models()
    
    if model_name not in models_info["available_models"]:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model_name} is not available or not supported on this hardware"
        )
    
    # Switch the model dynamically
    try:
        success = detector.switch_model(model_name)
        if success:
            return {
                "status": "success",
                "message": f"Model switched to: {model_name}",
                "selected_model": model_name,
                "current_model": detector.get_current_model(),
                "requires_restart": False
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to switch model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/reid", tags=["System"])
async def select_reid_embedder(embedder_name: str, authorization: str | None = Header(default=None)) -> dict:
    """Select a re-identification embedder for duplicate person detection."""
    user = await get_current_user(authorization)
    
    models_info = get_available_models()
    
    if embedder_name not in models_info["available_reid_embedders"]:
        raise HTTPException(
            status_code=400,
            detail=f"Re-ID embedder {embedder_name} is not available or not supported on this hardware"
        )
    
    try:
        success = detector.switch_embedder(embedder_name)
        if success:
            return {
                "status": "success",
                "message": f"Re-ID embedder switched to: {embedder_name}",
                "selected_embedder": embedder_name,
                "current_embedder": detector.get_current_embedder(),
                "tracking_enabled": detector.enable_tracking,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to switch re-ID embedder")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_model=None, tags=["System"])
async def root() -> FileResponse | dict:
    if FRONTEND_DIST.exists():
        return FileResponse(FRONTEND_DIST / "index.html")

    return {
        "message": "Backend is running. Start the React frontend at http://localhost:5173 or build it into apps/web/dist.",
        "frontend_origin": settings.frontend_origin,
    }
