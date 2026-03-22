/**
 * Number and date formatting for Data Palestine.
 * $13.7B not 13700000000. 24.4% not 24.42.
 */

export function formatValue(
  value: number,
  unitSymbol?: string | null,
  decimals: number = 1,
): string {
  if (unitSymbol === "$") return formatCurrency(value);
  if (unitSymbol === "%") return `${value.toFixed(decimals)}%`;
  if (value >= 1_000_000) return formatLargeNumber(value);
  if (Number.isInteger(value)) return value.toLocaleString("en-US");
  return value.toFixed(decimals);
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${value.toLocaleString("en-US")}`;
}

function formatLargeNumber(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  return value.toLocaleString("en-US");
}

export function formatYear(dateStr: string): string {
  return dateStr.slice(0, 4);
}

export function formatDate(dateStr: string, locale: string = "en"): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString(locale === "ar" ? "ar-PS" : "en-US", {
    year: "numeric",
    month: "short",
  });
}
