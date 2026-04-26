import { useEffect, useMemo, useRef, useState } from "react";
import {
  LayoutDashboard, Monitor, BarChart3, Sun, Moon, LogOut,
  Copy, Cpu, Wifi, Radio, User, Settings, Eye, Camera
} from "lucide-react";
import AuthView from "./components/auth/AuthView";
import { NetworkBadge, ProcessingBadge } from "./components/common/Badges";
import MetricChart from "./components/common/MetricChart";
import PageHeader from "./components/common/PageHeader";
import StatCard from "./components/common/StatCard";
import { API_BASE_URL, APP_VIEWS, CAPTURE_SOURCES, SESSION_KEY, THEME_KEY } from "./constants/ui";
import { buildProfileStreamUrl, createStreamCamera } from "./utils/streamProfiles";
import { validateAuthForm } from "./utils/validation";

export default function App() {
  const initialTheme = (() => {
    const savedTheme = window.localStorage.getItem(THEME_KEY);
    if (savedTheme === "light" || savedTheme === "dark") {
      return savedTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  })();

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);
  const streamRef = useRef(null);
  const streamFrameUrlsRef = useRef({});
  const processingModeRef = useRef("edge");
  const captureSourceRef = useRef("webcam");
  const classroomRef = useRef("Room 101");
  const courseCodeRef = useRef("CSE101");
  const isDetectingRef = useRef(false);
  const tokenRefreshTimerRef = useRef(null);

  const [session, setSession] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ fullName: "", username: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [validationErrors, setValidationErrors] = useState({});
  const [dbStatus, setDbStatus] = useState(null);
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
  const [socketConnected, setSocketConnected] = useState(false);
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
  const [tokenCopied, setTokenCopied] = useState(false);
  const [theme, setTheme] = useState(initialTheme);
  const [availableModels, setAvailableModels] = useState(null);
  const [selectedModel, setSelectedModel] = useState("auto");
  const [hardwareInfo, setHardwareInfo] = useState(null);
  const [availableReidEmbedders, setAvailableReidEmbedders] = useState(null);
  const [selectedReidEmbedder, setSelectedReidEmbedder] = useState("mobilenet");
  const [trackingEnabled, setTrackingEnabled] = useState(true);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    async function fetchDbStatus() {
      try {
        const response = await fetch(`${API_BASE_URL}/status`);
        const data = await response.json();
        setDbStatus(data.database);
      } catch {
        setDbStatus({ type: "unknown", error: "Failed to fetch status" });
      }
    }
    fetchDbStatus();
  }, []);

  useEffect(() => {
    if (!session?.accessToken) {
      clearTokenRefreshTimer();
      return undefined;
    }

    updateNetworkStatus();
    updateProcessingStatus(processingMode);
    void fetchStats(classroom, courseCode);
    void fetchContexts();
    void fetchStreamStatus();
    void fetchAvailableModels();

    return () => {
      void stopCamera();
    };
  }, [session]);

  useEffect(() => {
    if (session?.accessToken) {
      updateProcessingStatus(processingMode);
    }
  }, [processingMode, session]);

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
    const isStreamMode = captureSource === "stream";
    const isIngestMode = captureSource === "socket_ingest";
    if (!cameraRunning || (!isStreamMode && !isIngestMode) || (isStreamMode && !streamConnected) || (isIngestMode && !socketConnected)) {
      return undefined;
    }

    if (isStreamMode) {
      void refreshStreamPreview();
    } else {
      void refreshIngestPreview();
    }

    const previewInterval = window.setInterval(() => {
      if (isStreamMode) {
        void refreshStreamPreview();
      } else {
        void refreshIngestPreview();
      }
    }, 1500);

    return () => {
      clearInterval(previewInterval);
    };
  }, [cameraRunning, captureSource, streamConnected, socketConnected, streamCameraIds, activeCameraCount]);

  useEffect(() => {
    return () => {
      clearStreamFrames();
      clearTokenRefreshTimer();
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
    setSession(nextSession);
    scheduleTokenRefresh(nextSession);
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
    setValidationErrors({});

    const payload =
      authMode === "login"
        ? { username: authForm.username, password: authForm.password }
        : { username: authForm.username, password: authForm.password, full_name: authForm.fullName };

    console.log("Auth payload:", payload);

    const validation = validateAuthForm(authMode, authForm);
    console.log("Validation result:", validation);
    if (!validation.valid) {
      setValidationErrors(validation.errors);
      return;
    }

    const endpoint = authMode === "login" ? "/auth/login" : "/auth/signup";
    console.log("Submitting to:", endpoint);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      console.log("Response status:", response.status);
      const data = await response.json();
      console.log("Response data:", data);
      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      const nextSession = {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        username: data.username,
        fullName: data.full_name,
      };
      setSession(nextSession);
      scheduleTokenRefresh(nextSession);
      setAuthForm({ fullName: "", username: "", password: "" });
    } catch (requestError) {
      console.error("Auth error:", requestError);
      setAuthError(requestError.message || "Authentication failed.");
    }
  }

  function handleAuthModeChange(mode) {
    setAuthMode(mode);
    setAuthError("");
    setValidationErrors({});
  }

  function clearTokenRefreshTimer() {
    if (tokenRefreshTimerRef.current) {
      clearTimeout(tokenRefreshTimerRef.current);
      tokenRefreshTimerRef.current = null;
    }
  }

  function scheduleTokenRefresh(currentSession) {
    clearTokenRefreshTimer();
    // Refresh token 2 minutes before it expires (13 minutes = 780000 ms)
    // Access token expires in 15 minutes, so refresh at 13 minutes
    tokenRefreshTimerRef.current = window.setTimeout(() => {
      // Use the session from state at timeout time, not stale closure
      const latestSession = session;
      if (latestSession?.refreshToken) {
        void refreshAccessToken(latestSession);
      }
    }, 780000);
  }

  async function logout(skipRequest = false) {
    clearTokenRefreshTimer();
    
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

  async function fetchIngestStatus() {
    try {
      const response = await apiFetch("/ingest/status");
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to load ingest status.");
      }

      const ids = deriveCameraIds(data.cameras || [], data.camera_count || 0);
      setSocketConnected(Boolean(data.connected));
      setActiveCameraCount(data.camera_count || 0);
      setStreamCameraIds(ids);
      setError("");
      return { connected: Boolean(data.connected), cameraIds: ids };
    } catch (statusError) {
      setError(statusError.message || "Unable to load socket ingest status.");
      return { connected: false, cameraIds: [] };
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
    const cameraIds = candidateCameraIds;
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

  async function refreshIngestPreview(force = false, preferredCameraIds = []) {
    if (!force && !socketConnected) {
      return;
    }

    const fallbackCameraIds = Array.from({ length: activeCameraCount }, (_, index) => `cam_${index + 1}`);
    const candidateCameraIds = preferredCameraIds.length ? preferredCameraIds : streamCameraIds.length ? streamCameraIds : fallbackCameraIds;
    const cameraIds = candidateCameraIds;
    if (!cameraIds.length) {
      return;
    }

    const errors = [];
    await Promise.all(
      cameraIds.map(async (cameraId) => {
        try {
          const response = await apiFetch(`/ingest/frame/${encodeURIComponent(cameraId)}`, {}, false);
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Unable to load the ingested frame for ${cameraId}.`);
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
    if (streamCameraIds.length) {
      return streamCameraIds;
    }
    if (activeCameraCount > 0) {
      return Array.from({ length: activeCameraCount }, (_, index) => `cam_${index + 1}`);
    }
    return ["cam_1"];
  }, [streamCameraIds, activeCameraCount]);

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
      } else if (captureSourceRef.current === "socket_ingest") {
        const status = await fetchIngestStatus();
        if (!status.connected) {
          throw new Error("No active socket-ingest cameras. Start camera_socket_client.py from your local network first.");
        }
        await refreshIngestPreview(true, status.cameraIds);
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

    if (captureSourceRef.current === "socket_ingest") {
      setSocketConnected(false);
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
    setSocketConnected(false);
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

    const currentNetworkMode = "5g";
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
      } else if (currentSource === "socket_ingest") {
        response = await apiFetch(`/ingest/detect?${params.toString()}`, {
          method: "POST",
        });
        await refreshIngestPreview();
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
        throw new Error(data.detail || "Unable to load contexts.");
      }

      setContexts(data.items || []);
    } catch (contextsError) {
      setError(contextsError.message || "Unable to load contexts.");
    }
  }

  async function fetchAvailableModels() {
    try {
      const response = await apiFetch("/models");
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to load available models.");
      }

      setAvailableModels(data.available_models || {});
      setHardwareInfo(data.hardware || null);
      setSelectedModel(data.current_model || "auto");
      setAvailableReidEmbedders(data.available_reid_embedders || {});
      setSelectedReidEmbedder(data.current_reid_embedder || "mobilenet");
      setTrackingEnabled(data.tracking_enabled ?? true);
    } catch (modelsError) {
      console.error("Unable to load models:", modelsError);
    }
  }

  async function updateNetworkStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/simulate-network`);
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

    if (nextSource !== "socket_ingest") {
      setSocketConnected(false);
    }

    setCaptureSource(nextSource);
    setError("");
  }

  async function copyAccessToken() {
    if (!session?.accessToken) {
      return;
    }

    try {
      await navigator.clipboard.writeText(session.accessToken);
      setTokenCopied(true);
      window.setTimeout(() => setTokenCopied(false), 2000);
    } catch {
      setError("Unable to copy token. Copy it manually from the browser storage.");
    }
  }

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  const attendanceItems = [...history].reverse();
  const analytics = useMemo(() => {
    const totalDetections = history.length;
    const maxOccupancy = totalDetections ? Math.max(...history.map((item) => item.count)) : 0;
    const avgLatencyValue = totalDetections ? history.reduce((sum, item) => sum + item.latency_ms, 0) / totalDetections : 0;
    const avgNetworkDelayValue = totalDetections ? history.reduce((sum, item) => sum + (item.network_delay_ms || 0), 0) / totalDetections : 0;
    const avgProcessingDelayValue = totalDetections ? history.reduce((sum, item) => sum + (item.processing_delay_ms || 0), 0) / totalDetections : 0;
    const modeStats = ["5g"].map((mode) => {
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
        setAuthMode={handleAuthModeChange}
        authForm={authForm}
        setAuthForm={setAuthForm}
        authError={authError}
        validationErrors={validationErrors}
        onSubmit={handleAuthSubmit}
        theme={theme}
        onToggleTheme={toggleTheme}
        dbStatus={dbStatus}
      />
    );
  }

  return (
    <div className="app-shell">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="sidebar-brand">
          <h1>Smart Campus</h1>
          <p>Occupancy Platform</p>
        </div>

        <div className="sidebar-nav">
          <span className="sidebar-section-label">Dashboard</span>
          <button type="button" className={activeView === "overview" ? "sidebar-item active" : "sidebar-item"} onClick={() => setActiveView("overview")}>
            <LayoutDashboard /> Overview
          </button>
          <button type="button" className={activeView === "monitor" ? "sidebar-item active" : "sidebar-item"} onClick={() => setActiveView("monitor")}>
            <Monitor /> Live Monitor
          </button>
          <button type="button" className={activeView === "analytics" ? "sidebar-item active" : "sidebar-item"} onClick={() => setActiveView("analytics")}>
            <BarChart3 /> Analytics
          </button>

          <span className="sidebar-section-label">System</span>
          <button type="button" className="sidebar-item" onClick={() => void copyAccessToken()}>
            <Copy /> {tokenCopied ? "Token Copied" : "Copy Token"}
          </button>
          <button type="button" className="sidebar-item" onClick={() => void logout()}>
            <LogOut /> Logout
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">
              {(session.fullName || session.username || "?")[0].toUpperCase()}
            </div>
            <div className="sidebar-user-info">
              <strong>{session.fullName || session.username}</strong>
              <small>@{session.username}</small>
            </div>
          </div>
        </div>
      </nav>

      {/* Top Header Bar */}
      <header className="topbar">
        <div className="topbar-left">
          <h2>
            {activeView === "overview" ? "Dashboard Overview" : activeView === "monitor" ? "Live Monitor" : "Analytics"}
          </h2>
          {hardwareInfo && (
            <span className={`topbar-badge ${hardwareInfo.has_gpu ? "gpu" : "cpu"}`}>
              <Cpu /> {hardwareInfo.has_gpu ? hardwareInfo.gpu_name : "CPU Mode"}
            </span>
          )}
          {trackingEnabled && (
            <span className="topbar-badge tracking">
              <Eye /> Tracking ON
            </span>
          )}
        </div>
        <div className="topbar-right">
          <button type="button" className="icon-btn" onClick={toggleTheme}>
            {theme === "dark" ? <Sun /> : <Moon />}
          </button>
          <div className="segmented-control">
            {["edge", "cloud"].map((mode) => (
              <button key={mode} type="button" className={processingMode === mode ? "segment active" : "segment"} onClick={() => setProcessingMode(mode)}>
                {mode === "edge" ? "Edge" : "Cloud"}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {isOverCapacity ? <div className="alert-banner">Occupancy has crossed the room capacity limit. Please regulate entry for this classroom immediately.</div> : null}
        {error ? <div className="error-banner">{error}</div> : null}

      {activeView === "overview" ? (
        <div className="page-grid">
          <section className="hero-panel">
            <div className="hero-main">
              <p className="section-eyebrow">Executive Overview</p>
              <h2>Monitor occupancy risk and response performance from one professional workspace.</h2>
              <p className="hero-text">
                Review live room status, enforce classroom capacity, and monitor low-latency 5G camera operations without digging through crowded UI blocks.
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
                  eyebrow="Network Profile"
                  title="5G performance snapshot"
                  description="Track consistency of detections on the configured low-latency 5G path."
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
                ) : captureSource === "socket_ingest" ? (
                  <>
                    <div className={socketConnected ? "status-tile" : "status-tile danger"}>
                      <span>Socket Ingest Status</span>
                      <strong>{socketConnected ? `${activeCameraCount} camera${activeCameraCount === 1 ? "" : "s"} streaming` : "Not connected"}</strong>
                      <p>
                        Start local push clients with `tools/camera_socket_client.py` and then click Refresh Ingest Cameras.
                      </p>
                    </div>
                    <button type="button" className="secondary-btn" onClick={() => void fetchIngestStatus()}>
                      Refresh Ingest Cameras
                    </button>
                    <div className="generated-url">
                      WebSocket URL example: <code>{`ws://localhost:8000/ws/ingest/cam_1?token=<ACCESS_TOKEN>`}</code>
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
                <label className="field">
                  <span>Detection Model</span>
                  <select value={selectedModel} onChange={(event) => {
                    const model = event.target.value;
                    setSelectedModel(model);
                    if (model !== "auto" && session?.accessToken) {
                      apiFetch(`/models/select?model_name=${encodeURIComponent(model)}`, { method: "POST" }).catch(() => {});
                    }
                  }}>
                    <option value="auto">Auto (Recommended)</option>
                    {availableModels && Object.entries(availableModels).map(([modelId, modelInfo]) => (
                      <option key={modelId} value={modelId}>
                        {modelInfo.name} - {modelInfo.speed} / {modelInfo.accuracy}
                        {modelInfo.requires_gpu && !hardwareInfo?.has_gpu ? " (GPU Required)" : ""}
                      </option>
                    ))}
                  </select>
                  {hardwareInfo && (
                    <small className="field-hint">
                      {hardwareInfo.has_gpu 
                        ? `GPU: ${hardwareInfo.gpu_name} (${hardwareInfo.gpu_memory_gb.toFixed(1)} GB)` 
                        : "CPU Mode - GPU models unavailable"}
                    </small>
                  )}
                </label>
                <label className="field">
                  <span>Duplicate ID Model (Re-ID)</span>
                  <select value={selectedReidEmbedder} onChange={(event) => {
                    const embedder = event.target.value;
                    setSelectedReidEmbedder(embedder);
                    if (session?.accessToken) {
                      apiFetch(`/models/reid?embedder_name=${encodeURIComponent(embedder)}`, { method: "POST" }).catch(() => {});
                    }
                  }}>
                    {availableReidEmbedders && Object.entries(availableReidEmbedders).map(([embedderId, embedderInfo]) => (
                      <option key={embedderId} value={embedderId}>
                        {embedderInfo.name} - {embedderInfo.speed} / {embedderInfo.accuracy}
                        {embedderInfo.requires_gpu && !hardwareInfo?.has_gpu ? " (GPU Required)" : ""}
                      </option>
                    ))}
                  </select>
                  <small className="field-hint">
                    Re-identification model for tracking &amp; preventing duplicate person counts
                  </small>
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
                  {cameraRunning
                    ? `Restart ${captureSource === "stream" ? "Stream" : captureSource === "socket_ingest" ? "Ingest" : "Camera"}`
                    : captureSource === "stream"
                      ? "Connect Stream"
                      : captureSource === "socket_ingest"
                        ? "Start Ingest Monitor"
                        : "Start Live Camera"}
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
                  detail={
                    captureSource === "stream"
                      ? "Status of the remote stream session"
                      : captureSource === "socket_ingest"
                        ? "Status of pushed camera sessions"
                        : "Status of the webcam session"
                  }
                />
                <StatCard
                  label="Input Source"
                  value={captureSource === "stream" ? "Stream" : captureSource === "socket_ingest" ? "Socket Ingest" : "Webcam"}
                  detail="Selected source for live monitoring"
                />
                <StatCard label="Active Cameras" value={`${activeCameraCount}`} detail="Connected room views in fused occupancy mode" />
                <StatCard label="5G SIM Cameras" value={`${simCameraCount}`} detail="Connected cameras running in SIM-based 5G mode" />
                <StatCard label="Measured Latency" value={latency} detail={`Most recent 5G + ${processingMode} response`} />
              </div>
            </article>

            <article className="panel media-panel">
              <PageHeader
                eyebrow="Live Monitoring"
                title="Camera feed and AI overlay"
                description="Use a full camera wall and the fused annotated evidence frame for operational review."
              />
              <div className="media-grid">
                {captureSource !== "webcam" ? (
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
            <StatCard label="Network Mode" value="5G" detail="Low-latency path" />
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
      </main>
    </div>
  );
}
