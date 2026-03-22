/**
 * Typed API client for Data Palestine backend.
 * Matches the real API response format from app/routers/*.py
 */

// Server-side uses internal Docker network URL if available, otherwise public URL
const API_BASE =
  (typeof window === "undefined" && process.env.API_INTERNAL_URL) ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

// --- Response types ---

interface PaginationMeta {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

interface SingleResponse<T> {
  data: T;
}

// --- Entity types (matching API output) ---

interface CategoryRef {
  slug: string;
  name: string;
}

interface SourceRef {
  organization: string;
  url: string | null;
}

interface TemporalCoverage {
  start: string | null;
  end: string | null;
}

interface Dataset {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  category: CategoryRef | null;
  source: SourceRef | null;
  update_frequency: string | null;
  temporal_coverage: TemporalCoverage;
  indicator_count: number;
  tags: string[];
  featured: boolean;
  last_updated: string | null;
}

interface DatasetDetail extends Dataset {
  methodology: string | null;
  license: string;
  version: number;
  indicators: IndicatorRef[];
}

interface IndicatorRef {
  id: number;
  code: string;
  name: string;
  unit: string | null;
  unit_symbol: string | null;
  decimals: number;
}

interface LatestValue {
  value: number;
  time_period: string;
  geography: string;
}

interface Indicator {
  id: number;
  code: string;
  name: string;
  description: string | null;
  dataset: { slug: string; name: string };
  unit: string | null;
  unit_symbol: string | null;
  decimals: number;
  latest_value: LatestValue | null;
}

interface Observation {
  id: number;
  indicator: { id: number; code: string; name: string };
  geography: { code: string; name: string };
  time_period: string;
  time_precision: string;
  value: number | null;
  unit_symbol: string | null;
  value_status: string;
  source: SourceRef | null;
}

interface Geography {
  code: string;
  name: string;
  level: string;
  parent_code: string | null;
  has_data?: boolean;
  children?: Geography[];
}

// --- Client ---

type QueryParams = Record<string, string | number | boolean | undefined>;

async function apiFetch<T>(
  path: string,
  locale: string = "en",
  params?: QueryParams,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  url.searchParams.set("lang", locale);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  const res = await fetch(url.toString(), { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export async function getDatasets(
  locale: string,
  params?: QueryParams,
): Promise<PaginatedResponse<Dataset>> {
  return apiFetch("/api/v1/datasets", locale, params);
}

export async function getDataset(
  slug: string,
  locale: string,
): Promise<SingleResponse<DatasetDetail>> {
  return apiFetch(`/api/v1/datasets/${slug}`, locale);
}

export async function getIndicators(
  locale: string,
  params?: QueryParams,
): Promise<PaginatedResponse<Indicator>> {
  return apiFetch("/api/v1/indicators", locale, params);
}

export async function getObservations(
  locale: string,
  params?: QueryParams,
): Promise<PaginatedResponse<Observation>> {
  return apiFetch("/api/v1/observations", locale, params);
}

export async function getGeographies(
  locale: string,
  params?: QueryParams,
): Promise<{ data: Geography[] }> {
  return apiFetch("/api/v1/geographies", locale, params);
}

export type {
  Dataset,
  DatasetDetail,
  Indicator,
  IndicatorRef,
  Observation,
  Geography,
  LatestValue,
  PaginatedResponse,
  PaginationMeta,
};
