export function createStreamCamera(index) {
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

export function buildProfileStreamUrl(camera) {
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
