"use client";

interface ChartLegendItem {
  name: string;
  color: string;
}

interface ChartLegendProps {
  items: ChartLegendItem[];
}

export function ChartLegend({ items }: ChartLegendProps) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 pb-2">
      {items.map((item) => (
        <div key={item.name} className="flex items-center gap-1.5 min-w-0">
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: item.color }}
          />
          <span
            className="text-[11px] text-[#4B5563] truncate"
            style={{ maxWidth: "180px" }}
            title={item.name}
          >
            {item.name}
          </span>
        </div>
      ))}
    </div>
  );
}
