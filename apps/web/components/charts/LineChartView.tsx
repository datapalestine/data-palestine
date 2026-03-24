"use client";

import dynamic from "next/dynamic";
import { ChartLegend } from "./ChartLegend";
import type { TooltipContentProps } from "recharts";

// Lazy-load recharts to avoid SSR issues
const LineChart = dynamic(
  () => import("recharts").then((m) => m.LineChart),
  { ssr: false },
);
const Line = dynamic(
  () => import("recharts").then((m) => m.Line),
  { ssr: false },
);
const XAxis = dynamic(
  () => import("recharts").then((m) => m.XAxis),
  { ssr: false },
);
const YAxis = dynamic(
  () => import("recharts").then((m) => m.YAxis),
  { ssr: false },
);
const CartesianGrid = dynamic(
  () => import("recharts").then((m) => m.CartesianGrid),
  { ssr: false },
);
const Tooltip = dynamic(
  () => import("recharts").then((m) => m.Tooltip),
  { ssr: false },
);
const ResponsiveContainer = dynamic(
  () => import("recharts").then((m) => m.ResponsiveContainer),
  { ssr: false },
);

// ─── Axis value formatter ────────────────────────────────────────────────────
function formatAxisValue(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${Math.round(n / 1e3)}K`;
  if (n < 1 && n > 0) return n.toFixed(2);
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

// ─── Custom tooltip ──────────────────────────────────────────────────────────
interface CustomTooltipProps extends TooltipContentProps<number, string> {
  colors: readonly string[];
  series: string[];
}

function CustomTooltip({ active, payload, label, colors, series }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "1px solid #E0E0E0",
        borderRadius: "4px",
        padding: "8px 10px",
        minWidth: "140px",
      }}
    >
      <p style={{ fontSize: "11px", color: "#757575", fontWeight: 400, marginBottom: "6px" }}>
        {label}
      </p>
      {payload.map((entry, i) => {
        const entryName = String(entry.name ?? "");
        const seriesIndex = series.indexOf(entryName);
        const color = seriesIndex >= 0 ? colors[seriesIndex % colors.length] : entry.color;
        const truncatedName =
          entryName.length > 20
            ? `${entryName.slice(0, 20)}…`
            : entryName;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: color,
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: "11px", color: "#757575", flexGrow: 1 }}>{truncatedName}</span>
            <span style={{ fontSize: "14px", color: "#212121", fontWeight: 600, marginLeft: "8px" }}>
              {typeof entry.value === "number"
                ? entry.value.toLocaleString("en-US", { maximumFractionDigits: 2 })
                : String(entry.value ?? "")}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── LineChartView ────────────────────────────────────────────────────────────
interface LineChartViewProps {
  data: Record<string, unknown>[];
  series: string[]; // pre-capped at 5 by caller
  colors: readonly string[]; // CHART_COLORS
  locale: string;
}

export function LineChartView({ data, series, colors, locale: _locale }: LineChartViewProps) {
  const legendItems = series.map((name, i) => ({
    name,
    color: colors[i % colors.length],
  }));

  return (
    <div>
      <ChartLegend items={legendItems} />
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" vertical={false} />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11, fill: "#757575", fontFamily: "inherit" }}
            tickLine={false}
            axisLine={{ stroke: "#E0E0E0" }}
            tickMargin={8}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#757575", fontFamily: "inherit" }}
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={formatAxisValue}
          />
          <Tooltip
            content={(props) => (
              <CustomTooltip
                {...(props as TooltipContentProps<number, string>)}
                colors={colors}
                series={series}
              />
            )}
            cursor={{ stroke: "#E0E0E0", strokeWidth: 1 }}
          />
          {series.map((key, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[i % colors.length] as string}
              strokeWidth={2}
              dot={{ r: 2 }}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
