export function NetworkBadge({ mode, count, avgLatency }) {
  return (
    <div className="network-badge">
      <span className="badge-label">{mode.toUpperCase()} Lane</span>
      <strong>{count} detections</strong>
      <p>{avgLatency} average latency</p>
    </div>
  );
}

export function ProcessingBadge({ mode, count, avgLatency }) {
  return (
    <div className="network-badge">
      <span className="badge-label">{mode === "edge" ? "Edge AI" : "Cloud AI"}</span>
      <strong>{count} detections</strong>
      <p>{avgLatency} average latency</p>
    </div>
  );
}
