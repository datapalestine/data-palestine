/**
 * Client-side API fetcher for use in "use client" components.
 * No Next.js cache directives — uses plain fetch.
 */

import type {
  Dataset,
  DatasetDetail,
  Indicator,
  Observation,
  Geography,
  PaginatedResponse,
} from "./api-client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Params = Record<string, string | number | boolean | undefined>;

async function apiFetch<T>(
  path: string,
  locale: string,
  params?: Params,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  url.searchParams.set("lang", locale);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export async function fetchDatasets(
  locale: string,
  params?: Params,
): Promise<PaginatedResponse<Dataset>> {
  return apiFetch("/api/v1/datasets", locale, { per_page: 500, ...params });
}

export async function fetchDataset(
  slug: string,
  locale: string,
): Promise<{ data: DatasetDetail }> {
  return apiFetch(`/api/v1/datasets/${slug}`, locale);
}

export async function fetchIndicators(
  locale: string,
  params?: Params,
): Promise<PaginatedResponse<Indicator>> {
  return apiFetch("/api/v1/indicators", locale, params);
}

export async function fetchObservations(
  locale: string,
  params?: Params,
): Promise<PaginatedResponse<Observation>> {
  return apiFetch("/api/v1/observations", locale, params);
}

export async function fetchGeographies(
  locale: string,
  params?: Params,
): Promise<{ data: Geography[] }> {
  return apiFetch("/api/v1/geographies", locale, params);
}

export async function fetchDatasetGeographies(
  slug: string,
  locale: string,
): Promise<{ data: Geography[] }> {
  return apiFetch(`/api/v1/datasets/${slug}/geographies`, locale);
}

export function buildApiUrl(params: Params): string {
  const url = new URL(`${API_BASE}/api/v1/observations`);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  return url.toString();
}

export function buildExportUrl(datasetSlug: string, params?: Params): string {
  const url = new URL(`${API_BASE}/api/v1/export/${datasetSlug}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}
