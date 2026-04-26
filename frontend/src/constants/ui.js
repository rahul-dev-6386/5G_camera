// Use same-origin '/api' by default so SSH/browser setups work via a single forwarded frontend port.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
export const SESSION_KEY = "smart-campus-session";
export const THEME_KEY = "smart-campus-theme";

export const APP_VIEWS = [
  { id: "overview", label: "Overview" },
  { id: "monitor", label: "Live Monitor" },
  { id: "analytics", label: "Analytics" },
];

export const CAPTURE_SOURCES = [
  { id: "webcam", label: "Webcam" },
  { id: "stream", label: "Stream URL" },
  { id: "socket_ingest", label: "Socket Ingest" },
];
