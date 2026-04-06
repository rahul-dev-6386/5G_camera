import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const SESSION_KEY = "smart-campus-session";
const APP_VIEWS = [
  { id: "overview", label: "Overview" },
  { id: "monitor", label: "Live Monitor" },
  { id: "analytics", label: "Analytics" },
];
const CAPTURE_SOURCES = [
  { id: "webcam", label: "Webcam" },
  { id: "stream", label: "Stream URL" },
];

function createStreamCamera(index) {
  return {
    camera_id: `cam_${index}`,
    stream_url: "",
    stream_username: "",
    stream_password: "",
    connection_type: "standard",
    sim_provider: "",
    sim_number: "",
    sim_number_masked: "",
    sim_apn: "",
    plmn: "",
    router_wan_ip: "",
    router_lan_ip: "",
    camera_host: "",
    camera_port: "",
    stream_path: "",
    stream_protocol: "rtsp",
    prefer_router_wan_host: false,
  };
}

function buildProfileStreamUrl(camera) {
  if ((camera.stream_url || "").trim()) {
    return (camera.stream_url || "").trim();
  }

  const protocol = (camera.stream_protocol || "rtsp").trim().toLowerCase();
  const host = camera.prefer_router_wan_host ? (camera.router_wan_ip || "").trim() : (camera.camera_host || "").trim();
  if (!host) {
    return "";
  }

  const defaultPort = protocol === "https" ? "443" : protocol === "http" ? "80" : "554";
  const port = String(camera.camera_port || defaultPort).trim();
  const pathInput = (camera.stream_path || "").trim() || "/avstream/channel=1/stream=1.sdp";
  const path = pathInput.startsWith("/") ? pathInput : `/${pathInput}`;
  return `${protocol}://${host}:${port}${path}`;
}

function StatCard({ label, value, tone = "default", detail }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong>{value}</strong>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}

function MetricChart({ history, metricKey, title, emptyText, color, formatTick }) {
  const width = 860;
  const height = 280;
  const padding = 36;

  const { points, labels, maxValue } = useMemo(() => {
    if (!history.length) {
      return { points: "", labels: [], maxValue: 1 };
    }

    const highest = Math.max(...history.map((item) => item[metricKey] || 0), 1);
    const mappedPoints = history
      .map((item, index) => {
        const x = padding + (index * (width - padding * 2)) / Math.max(history.length - 1, 1);
        const y = height - padding - ((item[metricKey] || 0) / highest) * (height - padding * 2);
        return `${x},${y}`;
      })
      .join(" ");

    const mappedLabels = history.map((item, index) => ({
      x: padding + (index * (width - padding * 2)) / Math.max(history.length - 1, 1),
      label: new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }));

    return { points: mappedPoints, labels: mappedLabels, maxValue: highest };
  }, [history, metricKey]);

  if (!history.length) {
    return (
      <div className="empty-state">
        <p>{emptyText}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="chart-title-row">
        <p className="chart-subtitle">{title}</p>
      </div>
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <rect x="0" y="0" width={width} height={height} rx="24" fill="rgba(15, 23, 42, 0.02)" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(71, 85, 105, 0.22)" />
        {[0, 1, 2, 3, 4].map((tick) => {
          const y = padding + ((height - padding * 2) * tick) / 4;
          const value = Math.round(maxValue - (maxValue * tick) / 4);
          return (
            <g key={tick}>
              <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="rgba(148, 163, 184, 0.12)" />
              <text x="10" y={y + 4} fill="rgba(71, 85, 105, 0.85)" fontSize="12">
                {formatTick(value)}
              </text>
            </g>
          );
        })}
        <polyline points={points} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        {history.map((item, index) => {
          const x = padding + (index * (width - padding * 2)) / Math.max(history.length - 1, 1);
          const y = height - padding - ((item[metricKey] || 0) / maxValue) * (height - padding * 2);
          return <circle key={`${metricKey}-${item.timestamp}-${index}`} cx={x} cy={y} r="4.5" fill={color} />;
        })}
        {labels.map((entry, index) => (
          <text key={`${entry.label}-${index}`} x={entry.x} y={height - 10} textAnchor="middle" fill="rgba(100, 116, 139, 0.9)" fontSize="11">
            {entry.label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function NetworkBadge({ mode, count, avgLatency }) {
  return (
    <div className="network-badge">
      <span className="badge-label">{mode.toUpperCase()} Lane</span>
      <strong>{count} detections</strong>
      <p>{avgLatency} average latency</p>
    </div>
  );
}

function ProcessingBadge({ mode, count, avgLatency }) {
  return (
    <div className="network-badge">
      <span className="badge-label">{mode === "edge" ? "Edge AI" : "Cloud AI"}</span>
      <strong>{count} detections</strong>
      <p>{avgLatency} average latency</p>
    </div>
  );
}

function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="section-header">
      <div>
        <p className="section-eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="section-copy">{description}</p>
      </div>
      {action || null}
    </div>
  );
}

function AuthView({ authMode, setAuthMode, authForm, setAuthForm, authError, onSubmit }) {
  return (
    <div className="auth-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="auth-grid">
        <div className="auth-intro">
          <p className="section-eyebrow">Smart Campus Control</p>
          <h1>Enterprise monitoring for occupancy, attendance, and network performance.</h1>
          <p className="hero-text">
            Secure classroom operations in one interface, switch between 4G and 5G simulation, and review occupancy evidence with a cleaner operator workflow.
          </p>
          <div className="feature-list">
            <div className="feature-item">
              <strong>Operational clarity</strong>
              <span>Separate live monitoring, analytics, and review workflows.</span>
            </div>
            <div className="feature-item">
              <strong>Context-based tracking</strong>
              <span>Manage attendance by room and course without mixing sessions.</span>
            </div>
            <div className="feature-item">
              <strong>Audit-ready history</strong>
              <span>Inspect latency and occupancy trends with stored evidence logs.</span>
            </div>
          </div>
        </div>

        <div className="auth-card">
          <p className="section-eyebrow">Secure Access</p>
          <h2 className="auth-heading">Operator sign-in</h2>
          <p className="section-copy">Use your dashboard credentials to continue, or create an operator account for your lab team.</p>
          <div className="segmented-control auth-toggle">
            {["login", "signup"].map((mode) => (
              <button
                key={mode}
                type="button"
                className={authMode === mode ? "segment active" : "segment"}
                onClick={() => setAuthMode(mode)}
              >
                {mode === "login" ? "Login" : "Create account"}
              </button>
            ))}
          </div>
          <form className="auth-form" onSubmit={onSubmit}>
            {authMode === "signup" ? (
              <label className="field">
                <span>Full Name</span>
                <input
                  type="text"
                  value={authForm.fullName}
                  onChange={(event) => setAuthForm((current) => ({ ...current, fullName: event.target.value }))}
                  required
                />
              </label>
            ) : null}
            <label className="field">
              <span>Username</span>
              <input
                type="text"
                value={authForm.username}
                onChange={(event) => setAuthForm((current) => ({ ...current, username: event.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={authForm.password}
                onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))}
                required
              />
            </label>
            {authError ? <div className="error-banner">{authError}</div> : null}
            <button type="submit" className="primary-btn wide-btn">
              {authMode === "login" ? "Open Dashboard" : "Create Operator Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const savedSession = (() => {
    try {
      return JSON.parse(window.localStorage.getItem(SESSION_KEY) || "null");
    } catch {
      return null;
    }
  })();

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);
  const streamRef = useRef(null);
  const streamFrameUrlsRef = useRef({});
  const networkModeRef = useRef("5g");
  const processingModeRef = useRef("edge");
  const captureSourceRef = useRef("webcam");
  const classroomRef = useRef("Room 101");
  const courseCodeRef = useRef("CSE101");
  const isDetectingRef = useRef(false);

  const [session, setSession] = useState(savedSession);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ fullName: "", username: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [networkMode, setNetworkMode] = useState("5g");
  const [processingMode, setProcessingMode] = useState("edge");
  const [networkStatus, setNetworkStatus] = useState("Low latency mode (5G)");
  const [processingStatus, setProcessingStatus] = useState("Edge inference path");
  const [occupancy, setOccupancy] = useState(0);
  const [lastTimestamp, setLastTimestamp] = useState("Waiting for first detection");
  const [latency, setLatency] = useState("0 ms");
  const [annotatedImage, setAnnotatedImage] = useState("");
  const [history, setHistory] = useState([]);
  const [contexts, setContexts] = useState([]);
  const [cameraRunning, setCameraRunning] = useState(false);
  const [captureSource, setCaptureSource] = useState("webcam");
  const [streamCameras, setStreamCameras] = useState([createStreamCamera(1)]);
  const [streamConnected, setStreamConnected] = useState(false);
  const [streamCameraIds, setStreamCameraIds] = useState([]);
  const [streamCameraFrames, setStreamCameraFrames] = useState({});
  const [activeCameraCount, setActiveCameraCount] = useState(0);
  const [simCameraCount, setSimCameraCount] = useState(0);
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState("");
  const [maxCapacity, setMaxCapacity] = useState(40);
  const [captureInterval, setCaptureInterval] = useState(3);
  const [classroom, setClassroom] = useState("Room 101");
  const [courseCode, setCourseCode] = useState("CSE101");
  const [selectedContext, setSelectedContext] = useState("");
  const [activeView, setActiveView] = useState("overview");

  useEffect(() => {
    if (!session?.accessToken) {
      return undefined;
    }

    updateNetworkStatus(networkMode);
    updateProcessingStatus(processingMode);
    void fetchStats(classroom, courseCode);
    void fetchContexts();
    void fetchStreamStatus();

    return () => {
      void stopCamera();
    };
  }, [session]);

  useEffect(() => {
    if (session?.accessToken) {
      updateNetworkStatus(networkMode);
    }
  }, [networkMode, session]);

  useEffect(() => {
    if (session?.accessToken) {
      updateProcessingStatus(processingMode);
    }
  }, [processingMode, session]);

  useEffect(() => {
    networkModeRef.current = networkMode;
  }, [networkMode]);

  useEffect(() => {
    processingModeRef.current = processingMode;
  }, [processingMode]);

  useEffect(() => {
    captureSourceRef.current = captureSource;
  }, [captureSource]);

  useEffect(() => {
    classroomRef.current = classroom;
  }, [classroom]);

  useEffect(() => {
    courseCodeRef.current = courseCode;
  }, [courseCode]);

  useEffect(() => {
    if (!cameraRunning) {
      return;
    }

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    intervalRef.current = window.setInterval(() => {
      void detectFrame();
    }, Math.max(Number(captureInterval), 1) * 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [cameraRunning, captureInterval]);

  useEffect(() => {
    if (!cameraRunning || captureSource !== "stream" || !streamConnected) {
      return undefined;
    }

    void refreshStreamPreview();
    const previewInterval = window.setInterval(() => {
      void refreshStreamPreview();
    }, 1500);

    return () => {
      clearInterval(previewInterval);
    };
  }, [cameraRunning, captureSource, streamConnected, streamCameraIds, activeCameraCount]);

  useEffect(() => {
    return () => {
      clearStreamFrames();
    };
  }, []);

  async function refreshAccessToken(currentSession = session) {
    if (!currentSession?.refreshToken) {
      throw new Error("Refresh token missing.");
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: currentSession.refreshToken }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Session refresh failed.");
    }

    const nextSession = {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      username: data.username,
      fullName: data.full_name,
    };
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
    return nextSession;
  }

  async function apiFetch(path, options = {}, allowRefresh = true) {
    const currentSession = session;
    const headers = new Headers(options.headers || {});
    if (currentSession?.accessToken) {
      headers.set("Authorization", `Bearer ${currentSession.accessToken}`);
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401 && allowRefresh && currentSession?.refreshToken) {
      try {
        const nextSession = await refreshAccessToken(currentSession);
        const retryHeaders = new Headers(options.headers || {});
        retryHeaders.set("Authorization", `Bearer ${nextSession.accessToken}`);
        return await fetch(`${API_BASE_URL}${path}`, {
          ...options,
          headers: retryHeaders,
        });
      } catch {
        logout(true);
      }
    }

    return response;
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError("");

    const endpoint = authMode === "login" ? "/auth/login" : "/auth/signup";
    const payload =
      authMode === "login"
        ? { username: authForm.username, password: authForm.password }
        : { username: authForm.username, password: authForm.password, full_name: authForm.fullName };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      const nextSession = {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        username: data.username,
        fullName: data.full_name,
      };
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
      setSession(nextSession);
      setAuthForm({ fullName: "", username: "", password: "" });
    } catch (requestError) {
      setAuthError(requestError.message || "Authentication failed.");
    }
  }

  async function logout(skipRequest = false) {
    if (!skipRequest && session?.refreshToken) {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: session.refreshToken }),
        });
      } catch {
        // Ignore logout transport errors and clear local session anyway.
      }
    }

    await stopCamera();
    setSession(null);
    setHistory([]);
    setContexts([]);
    setError("");
    setActiveView("overview");
    window.localStorage.removeItem(SESSION_KEY);
  }

  async function fetchStreamStatus() {
    try {
      const response = await apiFetch("/multi-stream/status");
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to load stream status.");
      }

      const cameras = (data.cameras || []).map((item, index) => ({
        camera_id: item.camera_id || `cam_${index + 1}`,
        stream_url: item.stream_url || "",
        stream_username: "",
        stream_password: "",
        connection_type: item.connection_type || "standard",
        sim_provider: item.sim_provider || "",
        sim_number: "",
        sim_number_masked: item.sim_number_masked || "",
        sim_apn: item.sim_apn || "",
        plmn: item.plmn || "",
        router_wan_ip: item.router_wan_ip || "",
        router_lan_ip: item.router_lan_ip || "",
        camera_host: item.camera_host || "",
        camera_port: item.camera_port ? String(item.camera_port) : "",
        stream_path: item.stream_path || "",
        stream_protocol: item.stream_protocol || "rtsp",
        prefer_router_wan_host: Boolean(item.prefer_router_wan_host),
      }));

      setStreamConnected(Boolean(data.connected));
      setActiveCameraCount(data.camera_count || 0);
      setSimCameraCount(cameras.filter((item) => item.connection_type === "sim_5g").length);
      setStreamCameraIds(cameras.map((item) => item.camera_id).sort());
      setStreamCameras(cameras.length ? cameras : [createStreamCamera(1)]);
    } catch (streamStatusError) {
      setError(streamStatusError.message || "Unable to load stream status.");
    }
  }

  function updateStreamFrame(cameraId, nextUrl) {
    const previousUrl = streamFrameUrlsRef.current[cameraId];
    if (previousUrl) {
      URL.revokeObjectURL(previousUrl);
    }

    streamFrameUrlsRef.current[cameraId] = nextUrl;
    setStreamCameraFrames((current) => ({ ...current, [cameraId]: nextUrl }));
  }

  function clearStreamFrames() {
    Object.values(streamFrameUrlsRef.current).forEach((url) => {
      if (url) {
        URL.revokeObjectURL(url);
      }
    });
    streamFrameUrlsRef.current = {};
    setStreamCameraFrames({});
  }

  async function refreshStreamPreview(force = false, preferredCameraIds = []) {
    if (!force && !streamConnected) {
      return;
    }

    const fallbackCameraIds = Array.from({ length: activeCameraCount }, (_, index) => `cam_${index + 1}`);
    const candidateCameraIds = preferredCameraIds.length ? preferredCameraIds : streamCameraIds.length ? streamCameraIds : fallbackCameraIds;
    const cameraIds = candidateCameraIds.slice(0, 2);
    if (!cameraIds.length) {
      return;
    }

    const errors = [];
    await Promise.all(
      cameraIds.map(async (cameraId) => {
        try {
          const response = await apiFetch(`/multi-stream/frame/${encodeURIComponent(cameraId)}`, {}, false);
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Unable to load the frame for ${cameraId}.`);
          }
          const blob = await response.blob();
          updateStreamFrame(cameraId, URL.createObjectURL(blob));
        } catch (cameraError) {
          errors.push(cameraError.message || `Unable to refresh ${cameraId}.`);
        }
      }),
    );

    if (errors.length) {
      setError(errors[0]);
    } else {
      setError("");
    }
  }

  function deriveCameraIds(cameras, fallbackCount = 0) {
    const knownIds = (cameras || [])
      .map((item) => item.camera_id)
      .filter(Boolean)
      .sort();
    if (knownIds.length) {
      return knownIds;
    }

    return Array.from({ length: fallbackCount }, (_, index) => `cam_${index + 1}`);
  }

  function updateStreamCamera(index, field, value) {
    setStreamCameras((current) =>
      current.map((camera, cameraIndex) => {
        if (cameraIndex !== index) {
          return camera;
        }

        const nextCamera = { ...camera, [field]: value };
        if (field === "connection_type" && value === "standard") {
          return { ...nextCamera, sim_provider: "", sim_number: "", sim_apn: "" };
        }
        return nextCamera;
      }),
    );
  }

  function addStreamCamera() {
    setStreamCameras((current) => {
      const maxCameras = 8;
      if (current.length >= maxCameras) {
        return current;
      }
      return [...current, createStreamCamera(current.length + 1)];
    });
  }

  function removeStreamCamera(index) {
    setStreamCameras((current) => {
      if (current.length <= 1) {
        return current;
      }

      const trimmed = current.filter((_, cameraIndex) => cameraIndex !== index);
      return trimmed.map((camera, cameraIndex) => ({ ...camera, camera_id: `cam_${cameraIndex + 1}` }));
    });
  }

  function apply5GTemplate(index) {
    setStreamCameras((current) =>
      current.map((camera, cameraIndex) => {
        if (cameraIndex !== index) {
          return camera;
        }

        return {
          ...camera,
          connection_type: "sim_5g",
          stream_username: camera.stream_username || "admin",
          stream_password: camera.stream_password || "",
          camera_host: camera.camera_host || "10.101.0.6",
          camera_port: camera.camera_port || "554",
          stream_path: camera.stream_path || "/avstream/channel=1/stream=1.sdp",
          stream_protocol: camera.stream_protocol || "rtsp",
          router_wan_ip: camera.router_wan_ip || "10.101.0.2",
          router_lan_ip: camera.router_lan_ip || "192.168.128.1",
          plmn: camera.plmn || "00101",
        };
      }),
    );
  }

  const displayedCameraIds = useMemo(() => {
    if (streamCameraIds.length >= 2) {
      return streamCameraIds.slice(0, 2);
    }

    if (streamCameraIds.length === 1) {
      return [streamCameraIds[0], "cam_2"];
    }

    return ["cam_1", "cam_2"];
  }, [streamCameraIds]);

  async function connectStream() {
    const normalizedCameras = streamCameras
      .map((camera, index) => ({
        camera_id: `cam_${index + 1}`,
        stream_url: (camera.stream_url || "").trim(),
        stream_username: (camera.stream_username || "").trim(),
        stream_password: camera.stream_password || "",
        connection_type: camera.connection_type || "standard",
        sim_provider: (camera.sim_provider || "").trim(),
        sim_number: (camera.sim_number || "").trim(),
        sim_number_masked: camera.sim_number_masked || "",
        sim_apn: (camera.sim_apn || "").trim(),
        plmn: (camera.plmn || "").trim(),
        router_wan_ip: (camera.router_wan_ip || "").trim(),
        router_lan_ip: (camera.router_lan_ip || "").trim(),
        camera_host: (camera.camera_host || "").trim(),
        camera_port: Number(camera.camera_port) || undefined,
        stream_path: (camera.stream_path || "").trim(),
        stream_protocol: (camera.stream_protocol || "rtsp").trim().toLowerCase(),
        prefer_router_wan_host: Boolean(camera.prefer_router_wan_host),
      }))
      .map((camera) => ({ ...camera, stream_url: camera.stream_url || buildProfileStreamUrl(camera) }))
      .filter((camera) => camera.stream_url);

    if (!normalizedCameras.length) {
      throw new Error("Enter at least one valid stream URL before connecting.");
    }

    const invalidAuthCamera = normalizedCameras.find((camera) => camera.stream_password && !camera.stream_username);
    if (invalidAuthCamera) {
      throw new Error(`Camera ${invalidAuthCamera.camera_id.toUpperCase()} needs a username when password is set.`);
    }

    const invalidSimCamera = normalizedCameras.find(
      (camera) => camera.connection_type === "sim_5g" && !camera.camera_host && !camera.router_wan_ip && !camera.stream_url,
    );
    if (invalidSimCamera) {
      throw new Error(`Camera ${invalidSimCamera.camera_id.toUpperCase()} needs a camera host, router WAN host, or direct stream URL.`);
    }

    const response = await apiFetch("/multi-stream/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cameras: normalizedCameras.map((camera) => ({
          camera_id: camera.camera_id,
          stream_url: camera.stream_url,
          stream_username: camera.stream_username || undefined,
          stream_password: camera.stream_password || undefined,
          connection_type: camera.connection_type,
          sim_provider: camera.connection_type === "sim_5g" ? camera.sim_provider || undefined : undefined,
          sim_number: camera.connection_type === "sim_5g" ? camera.sim_number || undefined : undefined,
          sim_apn: camera.connection_type === "sim_5g" ? camera.sim_apn || undefined : undefined,
          plmn: camera.connection_type === "sim_5g" ? camera.plmn || undefined : undefined,
          router_wan_ip: camera.connection_type === "sim_5g" ? camera.router_wan_ip || undefined : undefined,
          router_lan_ip: camera.connection_type === "sim_5g" ? camera.router_lan_ip || undefined : undefined,
          camera_host: camera.camera_host || undefined,
          camera_port: camera.camera_port || undefined,
          stream_path: camera.stream_path || undefined,
          stream_protocol: camera.stream_protocol || undefined,
          prefer_router_wan_host: camera.connection_type === "sim_5g" ? camera.prefer_router_wan_host : undefined,
        })),
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Unable to connect to the camera streams.");
    }

    const resolvedCameraIds = deriveCameraIds(data.cameras || [], normalizedCameras.length);
    setStreamConnected(true);
    setActiveCameraCount(data.camera_count || normalizedCameras.length);
    setStreamCameraIds(resolvedCameraIds);
    setSimCameraCount((data.cameras || []).filter((item) => item.connection_type === "sim_5g").length);
    setStreamCameras(
      normalizedCameras.map((camera, index) => ({
        ...camera,
        camera_id: `cam_${index + 1}`,
        sim_number_masked: camera.sim_number ? "" : camera.sim_number_masked,
      })),
    );
    setError("");
    await refreshStreamPreview(true, resolvedCameraIds);
  }

  async function disconnectStream() {
    try {
      const response = await apiFetch("/multi-stream/disconnect", { method: "POST" }, false);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Unable to disconnect the stream.");
      }
    } catch (disconnectError) {
      setError(disconnectError.message || "Unable to disconnect the stream.");
    } finally {
      setStreamConnected(false);
      setActiveCameraCount(0);
      setSimCameraCount(0);
      setStreamCameraIds([]);
      clearStreamFrames();
    }
  }

  async function startCamera() {
    try {
      if (!classroom.trim() || !courseCode.trim()) {
        throw new Error("Enter classroom and course code before starting capture.");
      }

      if (cameraRunning) {
        await stopCamera();
      }

      if (captureSourceRef.current === "stream") {
        await connectStream();
      } else {
        if (streamConnected) {
          await disconnectStream();
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }

      setCameraRunning(true);
      setError("");
      setActiveView("monitor");

      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    } catch (cameraError) {
      setError(cameraError.message || "Camera access was blocked or unavailable. Allow camera permission and try again.");
    }
  }

  async function stopCamera(skipRemoteDisconnect = false) {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    if (!skipRemoteDisconnect && streamConnected) {
      await disconnectStream();
    } else if (skipRemoteDisconnect) {
      clearStreamFrames();
    }

    setCameraRunning(false);
    setIsDetecting(false);
    isDetectingRef.current = false;
  }

  async function resetSession() {
    await stopCamera();
    setOccupancy(0);
    setLastTimestamp("Waiting for first detection");
    setLatency("0 ms");
    setAnnotatedImage("");
    setActiveCameraCount(0);
    setSimCameraCount(0);
    setStreamCameraIds([]);
    setStreamCameras([createStreamCamera(1)]);
    clearStreamFrames();
    setHistory([]);
    setError("");
  }

  async function detectFrame() {
    const currentSource = captureSourceRef.current;
    const requiresWebcamFrame = currentSource === "webcam";
    if (
      isDetectingRef.current ||
      (requiresWebcamFrame && (!videoRef.current || !canvasRef.current || videoRef.current.readyState < 2)) ||
      (!requiresWebcamFrame && !streamConnected)
    ) {
      return;
    }

    const currentNetworkMode = networkModeRef.current;
    const currentProcessingMode = processingModeRef.current;
    const currentClassroom = classroomRef.current.trim();
    const currentCourseCode = courseCodeRef.current.trim().toUpperCase();

    setIsDetecting(true);
    isDetectingRef.current = true;
    try {
      const params = new URLSearchParams({
        mode: currentNetworkMode,
        processing_mode: currentProcessingMode,
        classroom: currentClassroom,
        course_code: currentCourseCode,
      });

      let response;
      if (currentSource === "stream") {
        response = await apiFetch(`/multi-stream/detect?${params.toString()}`, {
          method: "POST",
        });
        await refreshStreamPreview();
      } else {
        const blob = await captureFrame();
        if (!blob) {
          throw new Error("Unable to capture a frame from the camera.");
        }

        const formData = new FormData();
        formData.append("file", blob, "frame.jpg");

        response = await apiFetch(`/detect?${params.toString()}`, {
          method: "POST",
          body: formData,
        });
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Detection failed");
      }

      setOccupancy(data.count);
      setLastTimestamp(new Date(data.timestamp).toLocaleString());
      setLatency(`${data.latency_ms} ms`);
      setAnnotatedImage(`data:image/jpeg;base64,${data.image_base64}`);
      setActiveCameraCount(data.camera_count || 0);
      setError("");
      setSelectedContext(`${data.classroom}|||${data.course_code}`);
      await fetchStats(data.classroom, data.course_code);
      await fetchContexts();
    } catch (requestError) {
      setError(requestError.message || "Unable to contact backend.");
    } finally {
      setIsDetecting(false);
      isDetectingRef.current = false;
    }
  }

  function captureFrame() {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.92);
    });
  }

  async function fetchStats(targetClassroom = classroom, targetCourseCode = courseCode) {
    try {
      const params = new URLSearchParams({
        limit: "18",
        classroom: targetClassroom.trim(),
        course_code: targetCourseCode.trim().toUpperCase(),
      });
      const response = await apiFetch(`/stats?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to load stats");
      }
      setHistory(data.history);
    } catch (statsError) {
      setError(statsError.message || "Unable to load occupancy history.");
    }
  }

  async function fetchContexts() {
    try {
      const response = await apiFetch("/contexts");
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to load classroom contexts");
      }
      setContexts(data.items || []);
    } catch (contextError) {
      setError(contextError.message || "Unable to load classroom and course contexts.");
    }
  }

  async function updateNetworkStatus(mode) {
    try {
      const response = await fetch(`${API_BASE_URL}/simulate-network?mode=${mode}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to simulate network");
      }
      setNetworkStatus(`${data.message} | ${data.measured_response_ms} ms`);
      setLatency(`${data.measured_response_ms} ms`);
    } catch (networkError) {
      setError(networkError.message || "Unable to reach backend network simulation endpoint.");
    }
  }

  async function updateProcessingStatus(mode) {
    try {
      const response = await fetch(`${API_BASE_URL}/simulate-processing?mode=${mode}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to simulate processing path");
      }
      setProcessingStatus(`${data.message} | ${data.measured_response_ms} ms`);
    } catch (processingError) {
      setError(processingError.message || "Unable to reach backend processing simulation endpoint.");
    }
  }

  function exportCsv() {
    if (!history.length) {
      setError("No logs available to export yet.");
      return;
    }

    const rows = [
      ["timestamp", "student_count", "network_mode", "processing_mode", "latency_ms", "network_delay_ms", "processing_delay_ms", "classroom", "course_code"],
      ...history.map((item) => [
        item.timestamp,
        String(item.count),
        item.network_mode || "5g",
        item.processing_mode || "edge",
        String(item.latency_ms || 0),
        String(item.network_delay_ms || 0),
        String(item.processing_delay_ms || 0),
        item.classroom || "",
        item.course_code || "",
      ]),
    ];
    const csvContent = rows.map((row) => row.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${classroom}-${courseCode}-occupancy.csv`.replace(/\s+/g, "-");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function applyContextFilter(value) {
    setSelectedContext(value);
    if (!value) {
      return;
    }

    const [nextClassroom, nextCourseCode] = value.split("|||");
    setClassroom(nextClassroom);
    setCourseCode(nextCourseCode);
    void fetchStats(nextClassroom, nextCourseCode);
  }

  async function handleCaptureSourceChange(nextSource) {
    if (cameraRunning) {
      await stopCamera();
    }

    if (nextSource === "webcam" && streamConnected) {
      await disconnectStream();
    }

    setCaptureSource(nextSource);
    setError("");
  }

  const attendanceItems = [...history].reverse();
  const analytics = useMemo(() => {
    const totalDetections = history.length;
    const maxOccupancy = totalDetections ? Math.max(...history.map((item) => item.count)) : 0;
    const avgLatencyValue = totalDetections ? history.reduce((sum, item) => sum + item.latency_ms, 0) / totalDetections : 0;
    const avgNetworkDelayValue = totalDetections ? history.reduce((sum, item) => sum + (item.network_delay_ms || 0), 0) / totalDetections : 0;
    const avgProcessingDelayValue = totalDetections ? history.reduce((sum, item) => sum + (item.processing_delay_ms || 0), 0) / totalDetections : 0;
    const modeStats = ["5g", "4g"].map((mode) => {
      const items = history.filter((item) => item.network_mode === mode);
      const avg = items.length ? `${(items.reduce((sum, item) => sum + item.latency_ms, 0) / items.length).toFixed(1)} ms` : "0 ms";
      return { mode, count: items.length, avgLatency: avg };
    });
    const processingStats = ["edge", "cloud"].map((mode) => {
      const items = history.filter((item) => item.processing_mode === mode);
      const avg = items.length ? `${(items.reduce((sum, item) => sum + item.latency_ms, 0) / items.length).toFixed(1)} ms` : "0 ms";
      return { mode, count: items.length, avgLatency: avg };
    });
    return {
      totalDetections,
      maxOccupancy,
      avgLatency: `${avgLatencyValue.toFixed(1)} ms`,
      avgNetworkDelay: `${avgNetworkDelayValue.toFixed(1)} ms`,
      avgProcessingDelay: `${avgProcessingDelayValue.toFixed(1)} ms`,
      modeStats,
      processingStats,
    };
  }, [history]);

  const isOverCapacity = occupancy > Number(maxCapacity);
  const capacityUsage = Number(maxCapacity) > 0 ? Math.min(100, Math.round((occupancy / Number(maxCapacity)) * 100)) : 0;

  if (!session?.accessToken) {
    return (
      <AuthView
        authMode={authMode}
        setAuthMode={setAuthMode}
        authForm={authForm}
        setAuthForm={setAuthForm}
        authError={authError}
        onSubmit={handleAuthSubmit}
      />
    );
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="topbar">
        <div className="brand-block">
          <p className="section-eyebrow">Operations Console</p>
          <h1>Smart Campus Occupancy Platform</h1>
          <p className="topbar-copy">A cleaner operator workspace for classroom monitoring, attendance review, and network benchmarking.</p>
        </div>

        <div className="topbar-side">
          <div className="session-chip">
            <span className="session-chip-label">Signed in as</span>
            <strong>{session.fullName || session.username}</strong>
            <small>@{session.username}</small>
          </div>
          <div className="mode-control-stack">
            <div className="mode-control-block">
              <span className="mode-control-label">Network</span>
              <div className="segmented-control">
                {["5g", "4g"].map((mode) => (
                  <button key={mode} type="button" className={networkMode === mode ? "segment active" : "segment"} onClick={() => setNetworkMode(mode)}>
                    {mode.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <div className="mode-control-block">
              <span className="mode-control-label">AI Path</span>
              <div className="segmented-control">
                {["edge", "cloud"].map((mode) => (
                  <button key={mode} type="button" className={processingMode === mode ? "segment active" : "segment"} onClick={() => setProcessingMode(mode)}>
                    {mode === "edge" ? "Edge" : "Cloud"}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </header>

      <nav className="view-tabs" aria-label="Dashboard Views">
        {APP_VIEWS.map((view) => (
          <button
            key={view.id}
            type="button"
            className={activeView === view.id ? "view-tab active" : "view-tab"}
            onClick={() => setActiveView(view.id)}
          >
            {view.label}
          </button>
        ))}
      </nav>

      {isOverCapacity ? <div className="alert-banner">Occupancy has crossed the room capacity limit. Please regulate entry for this classroom immediately.</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      {activeView === "overview" ? (
        <div className="page-grid">
          <section className="hero-panel">
            <div className="hero-main">
              <p className="section-eyebrow">Executive Overview</p>
              <h2>Monitor occupancy risk and response performance from one professional workspace.</h2>
              <p className="hero-text">
                Review live room status, enforce classroom capacity, and compare the practical impact of 4G versus 5G response time without digging through crowded UI blocks.
              </p>
              <div className="hero-actions">
                <button type="button" className="primary-btn" onClick={() => void startCamera()}>
                  {cameraRunning ? "Restart Capture" : `Start ${captureSource === "stream" ? "Stream" : "Webcam"} Monitoring`}
                </button>
                <button type="button" className="secondary-btn" onClick={() => setActiveView("analytics")}>
                  Open Analytics
                </button>
              </div>
            </div>
            <div className="hero-side">
              <div className="signal-card">
                <span className="signal-label">Current network status</span>
                <strong>{networkStatus}</strong>
                <p>{cameraRunning ? `Live capture is active with ${processingMode} inference.` : "Capture is idle. Start the camera to resume evidence collection."}</p>
              </div>
              <div className="signal-card">
                <span className="signal-label">Current AI path</span>
                <strong>{processingStatus}</strong>
                <p>{processingMode === "edge" ? "Inference is simulated near the classroom for faster response." : "Inference is simulated through the cloud path with extra transit overhead."}</p>
              </div>
              <div className="capacity-meter-card">
                <div className="meter-copy">
                  <span className="signal-label">Capacity utilization</span>
                  <strong>{capacityUsage}%</strong>
                  <p>
                    {occupancy} of {maxCapacity} seats currently occupied in {classroom}.
                  </p>
                </div>
                <div className="meter-track" aria-hidden="true">
                  <div className={isOverCapacity ? "meter-fill danger" : "meter-fill"} style={{ width: `${capacityUsage}%` }} />
                </div>
              </div>
            </div>
          </section>

          <section className="summary-grid">
            <StatCard label="Current Occupancy" value={`${occupancy}`} tone="accent" detail={`${classroom} | ${courseCode}`} />
            <StatCard label="Average Latency" value={analytics.avgLatency} detail="Across the active room-course history" />
            <StatCard label="Avg Network Delay" value={analytics.avgNetworkDelay} detail="Transport contribution across detections" />
            <StatCard label="Avg AI Delay" value={analytics.avgProcessingDelay} detail="Processing path contribution across detections" />
            <StatCard label="Last Detection" value={lastTimestamp} detail={cameraRunning ? "Live stream active" : "Waiting for next capture"} />
            <StatCard label="Max Occupancy" value={`${analytics.maxOccupancy}`} detail="Peak count in loaded logs" />
          </section>

          <section className="overview-lower">
            <article className="panel">
              <PageHeader
                eyebrow="Operational Context"
                title="Room configuration"
                description="Keep monitoring scoped to the correct classroom and course before starting or reviewing a session."
                action={
                  <button type="button" className="secondary-btn" onClick={() => void fetchStats()}>
                    Refresh Context
                  </button>
                }
              />
              <div className="control-grid">
                <label className="field">
                  <span>Classroom</span>
                  <input type="text" value={classroom} onChange={(event) => setClassroom(event.target.value)} />
                </label>
                <label className="field">
                  <span>Course Code</span>
                  <input type="text" value={courseCode} onChange={(event) => setCourseCode(event.target.value.toUpperCase())} />
                </label>
                <label className="field">
                  <span>Saved Contexts</span>
                  <select value={selectedContext} onChange={(event) => applyContextFilter(event.target.value)}>
                    <option value="">Select classroom and course</option>
                    {contexts.map((item) => {
                      const value = `${item.classroom}|||${item.course_code}`;
                      return (
                        <option key={value} value={value}>
                          {item.classroom} | {item.course_code}
                        </option>
                      );
                    })}
                  </select>
                </label>
                <label className="field">
                  <span>Capture Interval (Seconds)</span>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={captureInterval}
                    onChange={(event) => setCaptureInterval(Math.max(1, Number(event.target.value) || 1))}
                  />
                </label>
                <label className="field">
                  <span>Room Capacity</span>
                  <input type="number" min="1" value={maxCapacity} onChange={(event) => setMaxCapacity(event.target.value)} />
                </label>
                <div className={isOverCapacity ? "status-tile danger" : "status-tile"}>
                  <span>Capacity Status</span>
                  <strong>{isOverCapacity ? "Over limit" : "Within limit"}</strong>
                  <p>{isOverCapacity ? "Entry should be regulated." : "Current occupancy remains within the configured threshold."}</p>
                </div>
              </div>
            </article>

            <div className="overview-side-stack">
              <article className="panel compact-panel">
                <PageHeader
                  eyebrow="Network Comparison"
                  title="Mode performance snapshot"
                  description="Benchmark the detection history across both simulated access conditions."
                />
                <div className="network-badges">
                  {analytics.modeStats.map((item) => (
                    <NetworkBadge key={item.mode} mode={item.mode} count={item.count} avgLatency={item.avgLatency} />
                  ))}
                </div>
              </article>

              <article className="panel compact-panel">
                <PageHeader
                  eyebrow="Processing Comparison"
                  title="Edge versus cloud"
                  description="Compare the impact of the selected AI deployment path on end-to-end detection time."
                />
                <div className="network-badges">
                  {analytics.processingStats.map((item) => (
                    <ProcessingBadge key={item.mode} mode={item.mode} count={item.count} avgLatency={item.avgLatency} />
                  ))}
                </div>
              </article>
            </div>
          </section>
        </div>
      ) : null}

      <div className="page-grid" hidden={activeView !== "monitor"}>
          <section className="monitor-layout">
            <article className="panel control-panel">
              <PageHeader
                eyebrow="Session Control"
                title="Live capture operations"
                description="Drive the stream, apply context filters, and control when evidence is captured."
              />
              <div className="control-grid single-column">
                <label className="field">
                  <span>Capture Source</span>
                  <select value={captureSource} onChange={(event) => void handleCaptureSourceChange(event.target.value)}>
                    {CAPTURE_SOURCES.map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>AI Processing Path</span>
                  <select value={processingMode} onChange={(event) => setProcessingMode(event.target.value)}>
                    <option value="edge">Edge Inference</option>
                    <option value="cloud">Cloud Inference</option>
                  </select>
                </label>
                {captureSource === "stream" ? (
                  <>
                    <div className="stream-config-head">
                      <span className="stream-config-title">Camera Profiles</span>
                      <button type="button" className="secondary-btn compact-btn" onClick={addStreamCamera} disabled={streamCameras.length >= 8}>
                        Add Camera
                      </button>
                    </div>
                    <div className="stream-camera-list">
                      {streamCameras.map((camera, index) => (
                        <div className="stream-camera-card" key={camera.camera_id}>
                          <div className="stream-camera-card-header">
                            <strong>{`Camera ${index + 1}`}</strong>
                            {camera.connection_type === "sim_5g" ? <span className="sim-tag">5G SIM</span> : null}
                            <button type="button" className="secondary-btn compact-btn" onClick={() => apply5GTemplate(index)}>
                              Use 5G Template
                            </button>
                            <button
                              type="button"
                              className="secondary-btn compact-btn"
                              onClick={() => removeStreamCamera(index)}
                              disabled={streamCameras.length <= 1}
                            >
                              Remove
                            </button>
                          </div>

                          <label className="field">
                            <span>Connection Type</span>
                            <select value={camera.connection_type} onChange={(event) => updateStreamCamera(index, "connection_type", event.target.value)}>
                              <option value="standard">Standard IP Camera</option>
                              <option value="sim_5g">5G SIM Camera</option>
                            </select>
                          </label>

                          <label className="field">
                            <span>Stream URL</span>
                            <input
                              type="text"
                              value={camera.stream_url}
                              onChange={(event) => updateStreamCamera(index, "stream_url", event.target.value)}
                              placeholder="http://10.0.4.166:8081/video"
                            />
                          </label>

                          <div className="stream-auth-grid">
                            <label className="field">
                              <span>Username (Optional)</span>
                              <input
                                type="text"
                                autoComplete="username"
                                value={camera.stream_username}
                                onChange={(event) => updateStreamCamera(index, "stream_username", event.target.value)}
                                placeholder="camera_user"
                              />
                            </label>
                            <label className="field">
                              <span>Password (Optional)</span>
                              <input
                                type="password"
                                autoComplete="current-password"
                                value={camera.stream_password}
                                onChange={(event) => updateStreamCamera(index, "stream_password", event.target.value)}
                                placeholder="camera_password"
                              />
                            </label>
                          </div>

                          {camera.connection_type === "sim_5g" ? (
                            <div className="stream-auth-grid">
                              <label className="field">
                                <span>SIM Provider</span>
                                <input
                                  type="text"
                                  value={camera.sim_provider}
                                  onChange={(event) => updateStreamCamera(index, "sim_provider", event.target.value)}
                                  placeholder="Jio / Airtel / Vodafone"
                                />
                              </label>
                              <label className="field">
                                <span>SIM Number / ICCID</span>
                                <input
                                  type="text"
                                  value={camera.sim_number}
                                  onChange={(event) => updateStreamCamera(index, "sim_number", event.target.value)}
                                  placeholder="8991XXXXXXXXXXXX"
                                />
                                {camera.sim_number_masked ? <small className="field-note">Connected SIM: {camera.sim_number_masked}</small> : null}
                              </label>
                              <label className="field">
                                <span>PLMN</span>
                                <input type="text" value={camera.plmn} onChange={(event) => updateStreamCamera(index, "plmn", event.target.value)} placeholder="00101" />
                              </label>
                              <label className="field">
                                <span>Camera Host (Private)</span>
                                <input
                                  type="text"
                                  value={camera.camera_host}
                                  onChange={(event) => updateStreamCamera(index, "camera_host", event.target.value)}
                                  placeholder="10.101.0.6"
                                />
                              </label>
                              <label className="field">
                                <span>Router WAN IPv4</span>
                                <input
                                  type="text"
                                  value={camera.router_wan_ip}
                                  onChange={(event) => updateStreamCamera(index, "router_wan_ip", event.target.value)}
                                  placeholder="10.101.0.2"
                                />
                              </label>
                              <label className="field">
                                <span>Router LAN IP</span>
                                <input
                                  type="text"
                                  value={camera.router_lan_ip}
                                  onChange={(event) => updateStreamCamera(index, "router_lan_ip", event.target.value)}
                                  placeholder="192.168.128.1"
                                />
                              </label>
                              <label className="field">
                                <span>Protocol</span>
                                <select value={camera.stream_protocol} onChange={(event) => updateStreamCamera(index, "stream_protocol", event.target.value)}>
                                  <option value="rtsp">RTSP</option>
                                  <option value="http">HTTP</option>
                                  <option value="https">HTTPS</option>
                                </select>
                              </label>
                              <label className="field">
                                <span>Port</span>
                                <input
                                  type="number"
                                  min="1"
                                  max="65535"
                                  value={camera.camera_port}
                                  onChange={(event) => updateStreamCamera(index, "camera_port", event.target.value)}
                                  placeholder="554"
                                />
                              </label>
                              <label className="field stream-full-width">
                                <span>Stream Path</span>
                                <input
                                  type="text"
                                  value={camera.stream_path}
                                  onChange={(event) => updateStreamCamera(index, "stream_path", event.target.value)}
                                  placeholder="/avstream/channel=1/stream=1.sdp"
                                />
                              </label>
                              <label className="field stream-full-width">
                                <span>SIM APN (Optional)</span>
                                <input
                                  type="text"
                                  value={camera.sim_apn}
                                  onChange={(event) => updateStreamCamera(index, "sim_apn", event.target.value)}
                                  placeholder="iot.5g.operator"
                                />
                              </label>
                              <label className="field stream-full-width checkbox-field">
                                <span>Use Router WAN Host</span>
                                <input
                                  type="checkbox"
                                  checked={Boolean(camera.prefer_router_wan_host)}
                                  onChange={(event) => updateStreamCamera(index, "prefer_router_wan_host", event.target.checked)}
                                />
                              </label>
                              <div className="generated-url">Resolved URL: {buildProfileStreamUrl(camera) || "waiting for host/stream URL"}</div>
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </>
                ) : null}
                <label className="field">
                  <span>Classroom</span>
                  <input type="text" value={classroom} onChange={(event) => setClassroom(event.target.value)} />
                </label>
                <label className="field">
                  <span>Course Code</span>
                  <input type="text" value={courseCode} onChange={(event) => setCourseCode(event.target.value.toUpperCase())} />
                </label>
                <label className="field">
                  <span>Capture Interval (Seconds)</span>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={captureInterval}
                    onChange={(event) => setCaptureInterval(Math.max(1, Number(event.target.value) || 1))}
                  />
                </label>
                <label className="field">
                  <span>Saved Contexts</span>
                  <select value={selectedContext} onChange={(event) => applyContextFilter(event.target.value)}>
                    <option value="">Select classroom and course</option>
                    {contexts.map((item) => {
                      const value = `${item.classroom}|||${item.course_code}`;
                      return (
                        <option key={value} value={value}>
                          {item.classroom} | {item.course_code}
                        </option>
                      );
                    })}
                  </select>
                </label>
              </div>
              {captureSource === "stream" ? (
                <div className={streamConnected ? "status-tile" : "status-tile danger"}>
                  <span>Stream Status</span>
                  <strong>{streamConnected ? `${activeCameraCount} camera${activeCameraCount === 1 ? "" : "s"} connected` : "Not connected"}</strong>
                  <p>
                    {streamConnected
                      ? "The room is running in fused multi-camera mode and overlapping detections are merged into one occupancy estimate."
                      : "Add one or more camera profiles. Use 5G SIM mode for real SIM-enabled cameras and standard mode for regular IP streams."}
                  </p>
                </div>
              ) : null}
              <div className="stack-actions">
                <button type="button" className="primary-btn" onClick={() => void startCamera()}>
                  {cameraRunning ? `Restart ${captureSource === "stream" ? "Stream" : "Camera"}` : captureSource === "stream" ? "Connect Stream" : "Start Live Camera"}
                </button>
                <button type="button" className="secondary-btn" onClick={() => void detectFrame()} disabled={!cameraRunning || isDetecting}>
                  {isDetecting ? "Detecting..." : "Detect Now"}
                </button>
                <button type="button" className="secondary-btn" onClick={() => void stopCamera()} disabled={!cameraRunning}>
                  Stop Capture
                </button>
                <button type="button" className="secondary-btn" onClick={() => void resetSession()}>
                  Reset Session
                </button>
              </div>
              <div className="mini-stats">
                <StatCard
                  label="Capture State"
                  value={cameraRunning ? "Streaming" : "Idle"}
                  detail={captureSource === "stream" ? "Status of the remote stream session" : "Status of the webcam session"}
                />
                <StatCard label="Input Source" value={captureSource === "stream" ? "Stream" : "Webcam"} detail="Selected source for live monitoring" />
                <StatCard label="Active Cameras" value={`${activeCameraCount}`} detail="Connected room views in fused occupancy mode" />
                <StatCard label="5G SIM Cameras" value={`${simCameraCount}`} detail="Connected cameras running in SIM-based 5G mode" />
                <StatCard label="Measured Latency" value={latency} detail={`Most recent ${networkMode.toUpperCase()} + ${processingMode} response`} />
              </div>
            </article>

            <article className="panel media-panel">
              <PageHeader
                eyebrow="Live Monitoring"
                title="Camera feed and AI overlay"
                description="Use the raw feed and annotated evidence side by side for operational review."
              />
              <div className="media-grid">
                {captureSource === "stream" ? (
                  <>
                    {displayedCameraIds.map((cameraId, index) => (
                      <div className="video-frame" key={cameraId}>
                        <span className="frame-label">{`Camera ${index + 1} (${cameraId.toUpperCase()})`}</span>
                        {streamCameraFrames[cameraId] ? (
                          <img src={streamCameraFrames[cameraId]} alt={`Live feed from ${cameraId}`} />
                        ) : (
                          <div className="placeholder-card">{`Connect ${cameraId.toUpperCase()} to view this live frame.`}</div>
                        )}
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="video-frame">
                    <span className="frame-label">Camera Feed</span>
                    <video ref={videoRef} autoPlay playsInline muted />
                  </div>
                )}
                <div className={captureSource === "stream" ? "video-frame stream-annotated-frame" : "video-frame"}>
                  <span className="frame-label">Annotated Detection</span>
                  {annotatedImage ? (
                    <img src={annotatedImage} alt="Detected people with bounding boxes" />
                  ) : (
                    <div className="placeholder-card">Annotated evidence appears here after the first successful detection cycle.</div>
                  )}
                </div>
              </div>
            </article>
          </section>
      </div>

      {activeView === "analytics" ? (
        <div className="page-grid">
          <section className="summary-grid analytics-summary">
            <StatCard label="Total Detections" value={`${analytics.totalDetections}`} detail="Loaded from the selected context" />
            <StatCard label="Capture Interval" value={`${captureInterval}s`} detail="Automatic sampling cadence" />
            <StatCard label="Active Context" value={`${classroom} | ${courseCode}`} detail="Current analytics filter" />
            <StatCard label="Network Mode" value={networkMode.toUpperCase()} detail="Current simulation profile" />
            <StatCard label="AI Path" value={processingMode === "edge" ? "Edge" : "Cloud"} detail="Current inference deployment" />
            <StatCard label="Avg Network Delay" value={analytics.avgNetworkDelay} detail="Simulated transport overhead" />
            <StatCard label="Avg AI Delay" value={analytics.avgProcessingDelay} detail="Simulated processing overhead" />
          </section>

          <section className="analytics-layout">
            <article className="panel chart-panel">
              <PageHeader
                eyebrow="Occupancy Analytics"
                title="Occupancy trend over time"
                description="Identify crowd buildup and compare the latest room load against expected capacity."
              />
              <MetricChart
                history={history}
                metricKey="count"
                title="Occupancy Timeline"
                emptyText="No occupancy data yet for this classroom and course."
                color="#0f766e"
                formatTick={(value) => value}
              />
            </article>

            <article className="panel chart-panel">
              <PageHeader
                eyebrow="Latency Analytics"
                title="Response time trend"
                description="Inspect how the backend responded across successive detections."
              />
              <MetricChart
                history={history}
                metricKey="latency_ms"
                title="Latency Timeline"
                emptyText="Latency readings will appear after detections are logged."
                color="#b45309"
                formatTick={(value) => `${value} ms`}
              />
            </article>

            <article className="panel attendance-panel">
              <PageHeader
                eyebrow="Evidence Log"
                title="Detection history"
                description="Review timestamped occupancy records, network mode, AI path, and measured latency."
                action={
                  <div className="inline-actions">
                    <button type="button" className="secondary-btn" onClick={() => void fetchStats()}>
                      Refresh Logs
                    </button>
                    <button type="button" className="secondary-btn" onClick={exportCsv}>
                      Export CSV
                    </button>
                    <button type="button" className="secondary-btn" onClick={() => void logout()}>
                      Logout
                    </button>
                  </div>
                }
              />
              <div className="attendance-list">
                {attendanceItems.length ? (
                  attendanceItems.map((item, index) => (
                    <div className="attendance-row" key={`${item.timestamp}-${index}`}>
                      <div>
                        <strong>{new Date(item.timestamp).toLocaleTimeString()}</strong>
                        <p>{new Date(item.timestamp).toLocaleDateString()}</p>
                      </div>
                      <div className="attendance-meta">
                        <span>{item.count} people</span>
                        <span>{item.network_mode.toUpperCase()}</span>
                        <span>{(item.processing_mode || "edge").toUpperCase()}</span>
                        <span>{item.latency_ms} ms</span>
                        <span>Net {item.network_delay_ms || 0} ms</span>
                        <span>AI {item.processing_delay_ms || 0} ms</span>
                        <span>{item.classroom} | {item.course_code}</span>
                        <span>{item.camera_count || 1} camera views</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="placeholder-card">No logs yet for this classroom and course. Start detection to populate the database.</div>
                )}
              </div>
            </article>
          </section>
        </div>
      ) : null}

      <canvas ref={canvasRef} hidden />
    </div>
  );
}
