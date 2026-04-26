import { useMemo } from "react";

export default function MetricChart({ history, metricKey, title, emptyText, color, formatTick }) {
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
