from typing import Literal

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    full_name: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class StreamConnectRequest(BaseModel):
    stream_url: str | None = Field(default=None, max_length=1000)
    stream_username: str | None = Field(default=None, max_length=150)
    stream_password: str | None = Field(default=None, max_length=300)
    connection_type: Literal["standard", "sim_5g"] = "standard"
    sim_provider: str | None = Field(default=None, max_length=80)
    sim_number: str | None = Field(default=None, max_length=40)
    sim_apn: str | None = Field(default=None, max_length=120)
    plmn: str | None = Field(default=None, max_length=20)
    router_wan_ip: str | None = Field(default=None, max_length=100)
    router_lan_ip: str | None = Field(default=None, max_length=100)
    camera_host: str | None = Field(default=None, max_length=255)
    camera_port: int | None = Field(default=None, ge=1, le=65535)
    stream_path: str | None = Field(default=None, max_length=400)
    stream_protocol: Literal["rtsp", "http", "https"] | None = None
    prefer_router_wan_host: bool = False


class StreamStatusResponse(BaseModel):
    connected: bool
    stream_url: str | None = None
    connected_at: str | None = None
    connection_type: Literal["standard", "sim_5g"] | None = None
    sim_provider: str | None = None
    sim_number_masked: str | None = None
    sim_apn: str | None = None
    plmn: str | None = None
    router_wan_ip: str | None = None
    router_lan_ip: str | None = None
    camera_host: str | None = None
    camera_port: int | None = None
    stream_path: str | None = None
    stream_protocol: Literal["rtsp", "http", "https"] | None = None
    prefer_router_wan_host: bool = False


class CameraStreamConfig(BaseModel):
    camera_id: str | None = Field(default=None, max_length=50)
    stream_url: str | None = Field(default=None, max_length=1000)
    stream_username: str | None = Field(default=None, max_length=150)
    stream_password: str | None = Field(default=None, max_length=300)
    connection_type: Literal["standard", "sim_5g"] = "standard"
    sim_provider: str | None = Field(default=None, max_length=80)
    sim_number: str | None = Field(default=None, max_length=40)
    sim_apn: str | None = Field(default=None, max_length=120)
    plmn: str | None = Field(default=None, max_length=20)
    router_wan_ip: str | None = Field(default=None, max_length=100)
    router_lan_ip: str | None = Field(default=None, max_length=100)
    camera_host: str | None = Field(default=None, max_length=255)
    camera_port: int | None = Field(default=None, ge=1, le=65535)
    stream_path: str | None = Field(default=None, max_length=400)
    stream_protocol: Literal["rtsp", "http", "https"] | None = None
    prefer_router_wan_host: bool = False


class MultiStreamConnectRequest(BaseModel):
    cameras: list[CameraStreamConfig] = Field(min_length=1, max_length=8)


class CameraStreamStatus(BaseModel):
    camera_id: str
    stream_url: str
    connected_at: str
    connection_type: Literal["standard", "sim_5g"] = "standard"
    sim_provider: str | None = None
    sim_number_masked: str | None = None
    sim_apn: str | None = None
    plmn: str | None = None
    router_wan_ip: str | None = None
    router_lan_ip: str | None = None
    camera_host: str | None = None
    camera_port: int | None = None
    stream_path: str | None = None
    stream_protocol: Literal["rtsp", "http", "https"] | None = None
    prefer_router_wan_host: bool = False


class MultiStreamStatusResponse(BaseModel):
    connected: bool
    camera_count: int = 0
    cameras: list[CameraStreamStatus] = Field(default_factory=list)


class ContextOption(BaseModel):
    classroom: str
    course_code: str


class ContextListResponse(BaseModel):
    items: list[ContextOption]


class DetectionResponse(BaseModel):
    count: int
    timestamp: str
    latency_ms: float
    network_mode: Literal["5g"]
    processing_mode: Literal["edge", "cloud"] = "edge"
    network_delay_ms: float = 0.0
    processing_delay_ms: float = 0.0
    source: str = "camera"
    classroom: str
    course_code: str
    image_base64: str
    camera_count: int = 1
    camera_counts: dict[str, int] = Field(default_factory=dict)


class OccupancyRecord(BaseModel):
    timestamp: str
    count: int
    network_mode: Literal["5g"] = "5g"
    processing_mode: Literal["edge", "cloud"] = "edge"
    latency_ms: float = 0.0
    network_delay_ms: float = 0.0
    processing_delay_ms: float = 0.0
    source: str = "camera"
    classroom: str = "General"
    course_code: str = "GEN-101"
    camera_count: int = 1
    camera_counts: dict[str, int] = Field(default_factory=dict)


class StatsResponse(BaseModel):
    history: list[OccupancyRecord]
    latest: OccupancyRecord | None


class NetworkSimulationResponse(BaseModel):
    mode: Literal["5g"]
    simulated_delay_ms: int
    measured_response_ms: float
    message: str


class ProcessingSimulationResponse(BaseModel):
    mode: Literal["edge", "cloud"]
    simulated_delay_ms: int
    measured_response_ms: float
    message: str
