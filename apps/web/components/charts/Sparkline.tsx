/**
 * Server-rendered SVG sparkline — no client JS needed.
 * Renders a simple line chart suitable for inline display.
 */

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillColor?: string;
  strokeWidth?: number;
  className?: string;
}

export function Sparkline({
  data,
  width = 120,
  height = 36,
  color = "#2E7D32",
  fillColor,
  strokeWidth = 1.5,
  className,
}: SparklineProps) {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const padding = 2;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1)) * chartWidth;
    const y = padding + chartHeight - ((val - min) / range) * chartHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M${points.join("L")}`;

  // Fill area path (close to bottom)
  const fill = fillColor
    ? `${pathD}L${(padding + chartWidth).toFixed(1)},${(height - padding).toFixed(1)}L${padding.toFixed(1)},${(height - padding).toFixed(1)}Z`
    : undefined;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="Sparkline chart"
    >
      {fill && (
        <path d={fill} fill={fillColor} opacity={0.15} />
      )}
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* End dot */}
      <circle
        cx={parseFloat(points[points.length - 1].split(",")[0])}
        cy={parseFloat(points[points.length - 1].split(",")[1])}
        r={2}
        fill={color}
      />
    </svg>
  );
}

/**
 * Bar sparkline for conflict/categorical data.
 */
interface BarSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export function BarSparkline({
  data,
  width = 120,
  height = 36,
  color = "#757575",
  className,
}: BarSparklineProps) {
  if (data.length < 1) return null;

  const max = Math.max(...data) || 1;
  const padding = 2;
  const gap = 1;
  const barWidth = Math.max(1, (width - padding * 2 - gap * (data.length - 1)) / data.length);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="Bar sparkline chart"
    >
      {data.map((val, i) => {
        const barHeight = Math.max(1, ((val / max) * (height - padding * 2)));
        const x = padding + i * (barWidth + gap);
        const y = height - padding - barHeight;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barWidth}
            height={barHeight}
            fill={color}
            opacity={0.7}
            rx={0.5}
          />
        );
      })}
    </svg>
  );
}
