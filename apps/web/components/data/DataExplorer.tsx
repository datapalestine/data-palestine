"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  fetchDatasets,
  fetchDataset,
  fetchObservations,
  fetchDatasetGeographies,
  buildApiUrl,
  buildExportUrl,
} from "@/lib/api-fetch";
import type {
  Dataset,
  DatasetDetail,
  Observation,
  Geography,
  IndicatorRef,
} from "@/lib/api-client";
import { LineChartView } from "@/components/charts/LineChartView";
import { BarChartView } from "@/components/charts/BarChartView";
import { ExplorerDisclaimer } from "@/components/data/ExplorerDisclaimer";
import { MAX_CHART_SERIES, CHART_COLORS } from "@/lib/constants";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function formatPeriod(period: string, precision: string): string {
  if (precision === "year") return period.slice(0, 4);
  if (precision === "month") {
    const d = new Date(period);
    return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  }
  if (precision === "quarter") {
    const d = new Date(period);
    const q = Math.floor(d.getUTCMonth() / 3) + 1;
    return `Q${q} ${d.getUTCFullYear()}`;
  }
  return period.slice(0, 10);
}

function formatValue(v: number | null, symbol?: string | null): string {
  if (v === null || v === undefined) return "—";
  const abs = Math.abs(v);
  let formatted: string;
  if (abs >= 1e9) formatted = `${(v / 1e9).toFixed(1)}B`;
  else if (abs >= 1e6) formatted = `${(v / 1e6).toFixed(1)}M`;
  else if (abs >= 1e3) formatted = v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  else formatted = v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (symbol === "%") return `${formatted}%`;
  if (symbol === "$") return `$${formatted}`;
  return formatted;
}

// ─── Translations type (matches explore page) ───────────
interface T {
  title: string;
  subtitle: string;
  filters: {
    dataset: string;
    indicator: string;
    category: string;
    geography: string;
    timeRange: string;
    yearFrom: string;
    yearTo: string;
    source: string;
    apply: string;
    clearAll: string;
    selectDataset: string;
    selectIndicator: string;
    filtersLabel: string;
  };
  results: { showing: string; noResults: string; noSelection: string; sortBy: string; chartError: string };
  export: { title: string; csv: string; json: string; excel: string; api: string; copied: string };
  chart: { lineChart: string; barChart: string; table: string; map: string; overflowBadge: string; source: string };
  table: { timePeriod: string; geography: string; indicator: string; value: string; source: string };
  info: { observations: string; timeRange: string; source: string };
}

// ─── Component ──────────────────────────────────────────
export function DataExplorer({ locale, t }: { locale: string; t: T }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Prevent page-level scroll — explorer fits in viewport
  useEffect(() => {
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
    };
  }, []);

  // ─── Data state ───────────────────────────────────────
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetail | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [geoTree, setGeoTree] = useState<Geography[]>([]);
  const [loading, setLoading] = useState(false);
  const [obsLoading, setObsLoading] = useState(false);
  const [copiedApi, setCopiedApi] = useState(false);

  // ─── Filter state from URL ────────────────────────────
  const datasetSlug = searchParams.get("dataset") || "";
  const indicatorParam = searchParams.get("indicators") || "";
  const geoParam = searchParams.get("geography") || "";
  const yearFrom = searchParams.get("year_from") || "";
  const yearTo = searchParams.get("year_to") || "";
  const activeTab = (searchParams.get("view") as "table" | "line" | "bar") || "table";

  const selectedIndicators = useMemo(
    () => (indicatorParam ? indicatorParam.split(",") : []),
    [indicatorParam],
  );
  const selectedGeos = useMemo(
    () => (geoParam ? geoParam.split(",") : []),
    [geoParam],
  );

  // ─── Local UI state (not in URL) ─────────────────────
  const [localDataset, setLocalDataset] = useState(datasetSlug);
  const [localIndicators, setLocalIndicators] = useState<string[]>(selectedIndicators);
  const [localGeos, setLocalGeos] = useState<string[]>(selectedGeos);
  const [localYearFrom, setLocalYearFrom] = useState(yearFrom);
  const [localYearTo, setLocalYearTo] = useState(yearTo);
  const [indicatorSearch, setIndicatorSearch] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  // ─── Fetch all datasets on mount ──────────────────────
  useEffect(() => {
    fetchDatasets(locale).then((r) => setDatasets(r.data)).catch(() => {});
  }, [locale]);

  // ─── When dataset changes, fetch detail + geos ────────
  useEffect(() => {
    if (!localDataset) {
      setDatasetDetail(null);
      setGeoTree([]);
      return;
    }
    setLoading(true);
    Promise.all([
      fetchDataset(localDataset, locale),
      fetchDatasetGeographies(localDataset, locale).catch(() => ({ data: [] })),
    ]).then(([detail, geos]) => {
      setDatasetDetail(detail.data);
      setGeoTree(geos.data);

      // Auto-select first 3 indicators + all geographies + auto-apply
      const allInds = detail.data.indicators.slice(0, 3).map((i: { id: number }) => String(i.id));
      const allGeos: string[] = [];
      function walkGeos(nodes: Geography[]) {
        for (const n of nodes) { allGeos.push(n.code); if (n.children) walkGeos(n.children); }
      }
      walkGeos(geos.data);

      setLocalIndicators(allInds);
      setLocalGeos(allGeos);
      setLoading(false);

      // Auto-apply: push to URL so observations load immediately
      if (allInds.length > 0) {
        const params = new URLSearchParams();
        params.set("dataset", localDataset);
        params.set("indicators", allInds.join(","));
        if (allGeos.length) params.set("geography", allGeos.join(","));
        router.push(`${pathname}?${params.toString()}`);
      }
    }).catch(() => setLoading(false));
  }, [localDataset, locale]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Fetch observations from URL params ───────────────
  useEffect(() => {
    if (!datasetSlug || !indicatorParam) {
      setObservations([]);
      return;
    }
    setObsLoading(true);
    const params: Record<string, string> = {
      dataset: datasetSlug,
      indicator: indicatorParam,
      per_page: "1000",
    };
    if (geoParam) params.geography = geoParam;
    if (yearFrom) params.year_from = yearFrom;
    if (yearTo) params.year_to = yearTo;
    fetchObservations(locale, params)
      .then((r) => { setObservations(r.data); setObsLoading(false); })
      .catch(() => setObsLoading(false));
  }, [datasetSlug, indicatorParam, geoParam, yearFrom, yearTo, locale]);

  // ─── Sync URL → local state when URL changes externally
  useEffect(() => {
    setLocalDataset(datasetSlug);
    setLocalIndicators(selectedIndicators);
    setLocalGeos(selectedGeos);
    setLocalYearFrom(yearFrom);
    setLocalYearTo(yearTo);
  }, [datasetSlug, selectedIndicators, selectedGeos, yearFrom, yearTo]);

  // ─── Push filters to URL ──────────────────────────────
  const applyFilters = useCallback(() => {
    const params = new URLSearchParams();
    if (localDataset) params.set("dataset", localDataset);
    if (localIndicators.length) params.set("indicators", localIndicators.join(","));
    if (localGeos.length) params.set("geography", localGeos.join(","));
    if (localYearFrom) params.set("year_from", localYearFrom);
    if (localYearTo) params.set("year_to", localYearTo);
    if (activeTab !== "table") params.set("view", activeTab);
    router.push(`${pathname}?${params.toString()}`);
    setMobileOpen(false);
  }, [localDataset, localIndicators, localGeos, localYearFrom, localYearTo, activeTab, pathname, router]);

  const clearFilters = useCallback(() => {
    setLocalDataset("");
    setLocalIndicators([]);
    setLocalGeos([]);
    setLocalYearFrom("");
    setLocalYearTo("");
    setIndicatorSearch("");
    router.push(pathname);
  }, [pathname, router]);

  const setTab = useCallback((tab: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "table") params.delete("view");
    else params.set("view", tab);
    router.push(`${pathname}?${params.toString()}`);
  }, [searchParams, pathname, router]);

  // ─── Indicator helpers ────────────────────────────────
  const filteredIndicators = useMemo(() => {
    if (!datasetDetail) return [];
    if (!indicatorSearch.trim()) return datasetDetail.indicators;
    const q = indicatorSearch.toLowerCase();
    return datasetDetail.indicators.filter((i) => i.name.toLowerCase().includes(q));
  }, [datasetDetail, indicatorSearch]);

  const toggleIndicator = useCallback((id: string) => {
    setLocalIndicators((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const toggleAllIndicators = useCallback(() => {
    if (!datasetDetail) return;
    const allIds = datasetDetail.indicators.map((i) => String(i.id));
    setLocalIndicators((prev) => prev.length === allIds.length ? [] : allIds);
  }, [datasetDetail]);

  // ─── Geography helpers ────────────────────────────────
  const allGeoCodes = useMemo(() => {
    const codes: string[] = [];
    function walk(nodes: Geography[]) {
      for (const n of nodes) {
        codes.push(n.code);
        if (n.children) walk(n.children);
      }
    }
    walk(geoTree);
    return codes;
  }, [geoTree]);

  const getDescendantCodes = useCallback((node: Geography): string[] => {
    const codes = [node.code];
    if (node.children) {
      for (const c of node.children) codes.push(...getDescendantCodes(c));
    }
    return codes;
  }, []);

  const toggleGeo = useCallback((node: Geography) => {
    const codes = getDescendantCodes(node);
    setLocalGeos((prev) => {
      const allSelected = codes.every((c) => prev.includes(c));
      if (allSelected) return prev.filter((c) => !codes.includes(c));
      return [...new Set([...prev, ...codes])];
    });
  }, [getDescendantCodes]);

  const geoCheckState = useCallback(
    (node: Geography) => {
      const codes = getDescendantCodes(node);
      const selected = codes.filter((c) => localGeos.includes(c)).length;
      return {
        checked: selected === codes.length,
        indeterminate: selected > 0 && selected < codes.length,
      };
    },
    [localGeos, getDescendantCodes],
  );

  // ─── Computed display values ──────────────────────────
  const timeRange = useMemo(() => {
    if (observations.length === 0) return "";
    const periods = observations.map((o) => o.time_period).sort();
    const first = formatPeriod(periods[0], observations[0].time_precision);
    const last = formatPeriod(periods[periods.length - 1], observations[observations.length - 1].time_precision);
    return first === last ? first : `${first} – ${last}`;
  }, [observations]);

  const sourceName = useMemo(() => {
    if (observations.length === 0) return "";
    return observations[0]?.source?.organization || "";
  }, [observations]);

  const uniquePeriods = useMemo(() => {
    return [...new Set(observations.map((o) => o.time_period))].sort();
  }, [observations]);

  // ─── Chart data ───────────────────────────────────────
  const chartData = useMemo(() => {
    if (observations.length === 0) return [];
    // Build a series per indicator+geography combo
    const seriesKeys = new Set<string>();
    const byPeriod: Record<string, Record<string, number>> = {};
    for (const obs of observations) {
      const period = formatPeriod(obs.time_period, obs.time_precision);
      const key = observations.some((o) =>
        o.indicator.id === obs.indicator.id && o.geography.code !== obs.geography.code
      )
        ? `${obs.indicator.name} (${obs.geography.name})`
        : uniquePeriods.length > 1
          ? obs.indicator.name
          : `${obs.indicator.name} – ${obs.geography.name}`;
      seriesKeys.add(key);
      if (!byPeriod[period]) byPeriod[period] = {};
      if (obs.value !== null) byPeriod[period][key] = obs.value;
    }
    const sorted = Object.keys(byPeriod).sort();
    return sorted.map((p) => ({ period: p, ...byPeriod[p] }));
  }, [observations, uniquePeriods]);

  const seriesNames = useMemo(() => {
    if (chartData.length === 0) return [];
    const keys = new Set<string>();
    for (const row of chartData) {
      for (const k of Object.keys(row)) {
        if (k !== "period") keys.add(k);
      }
    }
    return [...keys];
  }, [chartData]);

  const visibleSeries = useMemo(
    () => seriesNames.slice(0, MAX_CHART_SERIES),
    [seriesNames]
  );

  // ─── Copy API URL ─────────────────────────────────────
  const handleCopyApi = useCallback(() => {
    const params: Record<string, string> = {};
    if (datasetSlug) params.dataset = datasetSlug;
    if (indicatorParam) params.indicator = indicatorParam;
    if (geoParam) params.geography = geoParam;
    if (yearFrom) params.year_from = yearFrom;
    if (yearTo) params.year_to = yearTo;
    navigator.clipboard.writeText(buildApiUrl(params));
    setCopiedApi(true);
    setTimeout(() => setCopiedApi(false), 2000);
  }, [datasetSlug, indicatorParam, geoParam, yearFrom, yearTo]);

  // ─── Sorted observations for table ────────────────────
  const [sortCol, setSortCol] = useState<string>("period");
  const [sortAsc, setSortAsc] = useState(false);
  const [pageSize, setPageSize] = useState(15);
  const [currentPage, setCurrentPage] = useState(1);

  // Reset page when observations change
  useEffect(() => { setCurrentPage(1); }, [observations]);

  const sortedObs = useMemo(() => {
    const copy = [...observations];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortCol === "period") cmp = a.time_period.localeCompare(b.time_period);
      else if (sortCol === "geo") cmp = a.geography.name.localeCompare(b.geography.name);
      else if (sortCol === "indicator") cmp = a.indicator.name.localeCompare(b.indicator.name);
      else if (sortCol === "value") cmp = (a.value ?? 0) - (b.value ?? 0);
      return sortAsc ? cmp : -cmp;
    });
    return copy;
  }, [observations, sortCol, sortAsc]);

  const handleSort = (col: string) => {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  };

  const sortIcon = (col: string) =>
    sortCol === col ? (sortAsc ? " ↑" : " ↓") : "";

  // ─── RENDER ───────────────────────────────────────────
  return (
    <div className="mx-auto max-w-7xl px-4 py-2 sm:px-6" style={{ height: "calc(100vh - 165px)", overflow: "hidden" }}>
      {/* Mobile toggle — hidden on desktop via CSS */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="explorer-mobile-toggle mb-4 w-full cursor-pointer items-center justify-between rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        <span>{t.filters.filtersLabel}</span>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`transition-transform duration-200 ${mobileOpen ? "rotate-180" : ""}`}>
          <path d="M4 6l4 4 4-4" />
        </svg>
      </button>

      <div className="explorer-layout flex flex-col gap-4" style={{ height: "100%" }}>
        {/* ═══ LEFT SIDEBAR — visible on desktop via CSS, toggle on mobile ═══ */}
        <aside
          className="explorer-sidebar explorer-sidebar-width w-full"
          data-open={mobileOpen ? "true" : "false"}
          style={{ maxHeight: "100%", overflowY: "auto" }}
        >
          <div className="rounded-lg border border-neutral-200 bg-white">
            {/* DATASET */}
            <div className="border-b border-neutral-100 p-4">
              <label htmlFor="ds-select" className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
                {t.filters.dataset}
              </label>
              <select
                id="ds-select"
                value={localDataset}
                onChange={(e) => {
                  setLocalDataset(e.target.value);
                  setLocalIndicators([]);
                  setLocalGeos([]);
                  setIndicatorSearch("");
                }}
                dir="auto"
                className="w-full cursor-pointer rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 transition-colors hover:border-neutral-400 focus:border-[#1B5E20] focus:outline-none focus:ring-1 focus:ring-[#1B5E20]"
              >
                <option value="">{t.filters.selectDataset}</option>
                {datasets.map((ds) => (
                  <option key={ds.slug} value={ds.slug}>
                    {ds.name}
                  </option>
                ))}
              </select>
              {datasets.length > 0 && (
                <p className="mt-1 text-[10px] text-neutral-400">{datasets.length} datasets</p>
              )}
            </div>

            {/* INDICATORS */}
            {datasetDetail && datasetDetail.indicators.length > 0 && (
              <div className="border-b border-neutral-100 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
                    {t.filters.indicator}{" "}
                    <span className="font-normal normal-case">
                      ({localIndicators.length} / {datasetDetail.indicators.length})
                    </span>
                  </label>
                  <button
                    onClick={toggleAllIndicators}
                    className="cursor-pointer text-[11px] font-medium text-[#1B5E20] transition-colors hover:text-[#0D3B10] hover:underline"
                  >
                    {localIndicators.length === datasetDetail.indicators.length
                      ? (locale === "ar" ? "إلغاء الكل" : "Deselect all")
                      : (locale === "ar" ? "تحديد الكل" : "Select all")}
                  </button>
                </div>

                {datasetDetail.indicators.length > 8 && (
                  <input
                    type="text"
                    value={indicatorSearch}
                    onChange={(e) => setIndicatorSearch(e.target.value)}
                    placeholder={locale === "ar" ? "بحث..." : "Filter indicators..."}
                    className="mb-2 w-full rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-[12px] text-neutral-900 placeholder:text-neutral-400 transition-colors focus:border-[#1B5E20] focus:outline-none focus:ring-1 focus:ring-[#1B5E20]"
                  />
                )}

                <div className="space-y-0.5 rounded-md border border-neutral-100 p-1" style={{ maxHeight: "140px", overflowY: "auto" }}>
                  {filteredIndicators.map((ind) => {
                    const id = String(ind.id);
                    const checked = localIndicators.includes(id);
                    return (
                      <label
                        key={ind.id}
                        className={`flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 text-[12px] transition-colors hover:bg-neutral-50 ${checked ? "bg-[#1B5E20]/5 text-[#1B5E20]" : "text-neutral-700"}`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleIndicator(id)}
                          className="mt-0.5 cursor-pointer accent-[#1B5E20]"
                        />
                        <span className="leading-snug" dir="auto">{ind.name}</span>
                      </label>
                    );
                  })}
                  {indicatorSearch && filteredIndicators.length === 0 && (
                    <p className="px-2 py-2 text-[12px] text-neutral-400">{t.results.noResults}</p>
                  )}
                </div>
              </div>
            )}

            {loading && localDataset && (
              <div className="border-b border-neutral-100 p-4">
                <div className="h-4 w-24 animate-pulse rounded bg-neutral-100" />
                <div className="mt-2 space-y-2">
                  {[1,2,3].map((i) => <div key={i} className="h-5 animate-pulse rounded bg-neutral-100" />)}
                </div>
              </div>
            )}

            {/* GEOGRAPHY */}
            {datasetDetail && (
              <div className="border-b border-neutral-100 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
                    {t.filters.geography}
                    {geoTree.length > 0 && (
                      <span className="font-normal normal-case">
                        {" "}({localGeos.length} / {allGeoCodes.length})
                      </span>
                    )}
                  </label>
                  {geoTree.length > 0 && (
                    <button
                      onClick={() => {
                        if (localGeos.length === allGeoCodes.length) {
                          setLocalGeos([]);
                        } else {
                          setLocalGeos([...allGeoCodes]);
                        }
                      }}
                      className="cursor-pointer text-[11px] font-medium text-[#1B5E20] transition-colors hover:text-[#0D3B10] hover:underline"
                    >
                      {localGeos.length === allGeoCodes.length
                        ? (locale === "ar" ? "إلغاء الكل" : "Deselect all")
                        : (locale === "ar" ? "تحديد الكل" : "Select all")}
                    </button>
                  )}
                </div>
                {geoTree.length === 0 ? (
                  <p className="text-[12px] text-neutral-400">
                    {locale === "ar" ? "اختر مجموعة بيانات أولاً" : "Select a dataset first"}
                  </p>
                ) : (
                  <div className="space-y-0.5" style={{ maxHeight: "160px", overflowY: "auto" }}>
                    {geoTree.map((country) => (
                      <GeoNode key={country.code} node={country} level={0}
                        localGeos={localGeos} toggleGeo={toggleGeo} geoCheckState={geoCheckState} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TIME RANGE */}
            <div className="border-b border-neutral-100 p-4">
              <label className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
                {t.filters.timeRange}
              </label>
              <div className="flex items-center gap-2">
                <input type="number" placeholder={t.filters.yearFrom} value={localYearFrom}
                  onChange={(e) => setLocalYearFrom(e.target.value)} min={1990} max={2030}
                  className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm tabular-nums text-neutral-900 transition-colors focus:border-[#1B5E20] focus:outline-none focus:ring-1 focus:ring-[#1B5E20]" />
                <span className="text-neutral-300">–</span>
                <input type="number" placeholder={t.filters.yearTo} value={localYearTo}
                  onChange={(e) => setLocalYearTo(e.target.value)} min={1990} max={2030}
                  className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm tabular-nums text-neutral-900 transition-colors focus:border-[#1B5E20] focus:outline-none focus:ring-1 focus:ring-[#1B5E20]" />
              </div>
            </div>

            {/* BUTTONS */}
            <div className="p-4">
              <button onClick={applyFilters}
                disabled={!localDataset || localIndicators.length === 0}
                className="w-full cursor-pointer rounded-md bg-[#1B5E20] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#0D3B10] disabled:cursor-not-allowed disabled:opacity-40">
                {t.filters.apply}
              </button>
              <button onClick={clearFilters}
                className="mt-2 w-full cursor-pointer text-center text-[12px] text-neutral-500 transition-colors hover:text-neutral-700 hover:underline">
                {t.filters.clearAll}
              </button>
            </div>
          </div>
        </aside>

        {/* ═══ CENTER — TABLE/CHART ═══ */}
        <main className="min-w-0 flex-1" style={{ maxHeight: "100%", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
              {/* ── Disclaimer banner ── */}
              <div className="shrink-0 mb-3">
                <ExplorerDisclaimer />
              </div>
              {/* ── Tab bar ── */}
              <div className="flex rounded-lg border border-neutral-200 bg-white p-1 shrink-0">
                {(["table", "line", "bar"] as const).map((tab) => {
                  const labels = { table: t.chart.table, line: t.chart.lineChart, bar: t.chart.barChart };
                  return (
                    <button key={tab} onClick={() => setTab(tab)}
                      className={`flex-1 cursor-pointer rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                        activeTab === tab
                          ? "bg-[#1B5E20] text-white"
                          : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900"
                      }`}>
                      {labels[tab]}
                    </button>
                  );
                })}
              </div>

              {/* ── Content ── */}
              <div className="flex-1 min-h-0 mt-3">
              {activeTab === "table" ? (
                /* TABLE — always shows structure */
                <div className="rounded-lg border border-neutral-200 bg-white" style={{ maxHeight: "100%", display: "flex", flexDirection: "column" }}>
                  <div className="overflow-x-auto flex-1" style={{ overflowY: "auto" }}>
                  <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
                    <thead>
                      <tr className="sticky top-0 z-10 border-b border-neutral-200 bg-neutral-50">
                        <th onClick={() => handleSort("period")} style={{ width: "12%", resize: "horizontal", overflow: "hidden" }}
                          className="cursor-pointer px-3 py-2 text-start text-[10px] font-semibold uppercase tracking-wider text-neutral-500 transition-colors hover:text-neutral-900">
                          {t.table.timePeriod}{sortIcon("period")}
                        </th>
                        <th onClick={() => handleSort("geo")} style={{ width: "16%", resize: "horizontal", overflow: "hidden" }}
                          className="cursor-pointer px-3 py-2 text-start text-[10px] font-semibold uppercase tracking-wider text-neutral-500 transition-colors hover:text-neutral-900">
                          {t.table.geography}{sortIcon("geo")}
                        </th>
                        <th onClick={() => handleSort("indicator")} style={{ width: "36%", resize: "horizontal", overflow: "hidden" }}
                          className="cursor-pointer px-3 py-2 text-start text-[10px] font-semibold uppercase tracking-wider text-neutral-500 transition-colors hover:text-neutral-900">
                          {t.table.indicator}{sortIcon("indicator")}
                        </th>
                        <th onClick={() => handleSort("value")} style={{ width: "14%" }}
                          className="cursor-pointer px-3 py-2 text-end text-[10px] font-semibold uppercase tracking-wider text-neutral-500 transition-colors hover:text-neutral-900">
                          {t.table.value}{sortIcon("value")}
                        </th>
                        <th style={{ width: "22%", overflow: "hidden" }}
                          className="px-3 py-2 text-start text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                          {t.table.source}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {obsLoading ? (
                        [1,2,3,4,5].map((i) => (
                          <tr key={i} className="border-b border-neutral-100">
                            <td colSpan={5} className="px-4 py-3">
                              <div className="h-4 animate-pulse rounded bg-neutral-100" />
                            </td>
                          </tr>
                        ))
                      ) : sortedObs.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-4 py-12 text-center text-sm text-neutral-400">
                            {locale === "ar"
                              ? "لا توجد بيانات. اختر مجموعة بيانات واضغط تطبيق."
                              : "No data to display. Select a dataset and click Apply Filters."}
                          </td>
                        </tr>
                      ) : (
                        sortedObs.slice((currentPage - 1) * pageSize, currentPage * pageSize).map((obs) => (
                          <tr key={obs.id} className="border-b border-neutral-100 transition-colors hover:bg-neutral-50">
                            <td className="whitespace-nowrap px-3 py-2 text-[12px] tabular-nums text-neutral-900">
                              {formatPeriod(obs.time_period, obs.time_precision)}
                            </td>
                            <td className="whitespace-nowrap px-3 py-2 text-[12px] text-neutral-700">{obs.geography.name}</td>
                            <td className="px-3 py-2 text-[12px] text-neutral-700" style={{ maxWidth: "220px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={obs.indicator.name}>{obs.indicator.name}</td>
                            <td className="whitespace-nowrap px-3 py-2 text-end text-[12px] tabular-nums font-medium text-neutral-900">
                              {formatValue(obs.value, obs.unit_symbol)}
                            </td>
                            <td className="px-3 py-2 text-[11px] text-neutral-400" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={obs.source?.organization || ""}>{obs.source?.organization || ""}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                  </div>

                  {/* Pagination */}
                  {sortedObs.length > 0 && (() => {
                    const start = (currentPage - 1) * pageSize + 1;
                    const end = Math.min(currentPage * pageSize, sortedObs.length);
                    return (
                    <div className="flex items-center justify-between border-t border-neutral-200 px-3 py-2">
                      <div className="flex items-center gap-2 text-[10px] text-neutral-400">
                        <span>{start}–{end} of {sortedObs.length}</span>
                        <span className="text-neutral-300">·</span>
                        <select
                          value={pageSize}
                          onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                          className="cursor-pointer rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] text-neutral-500 focus:border-[#1B5E20] focus:outline-none"
                        >
                          {[15, 30, 50].map((n) => (
                            <option key={n} value={n}>{n}</option>
                          ))}
                        </select>
                        <span>per page</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                          disabled={currentPage <= 1}
                          className="cursor-pointer rounded border border-neutral-200 px-2 py-0.5 text-[11px] text-neutral-600 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {locale === "ar" ? "السابق" : "Prev"}
                        </button>
                        <span className="px-2 text-[11px] tabular-nums text-neutral-500">
                          {currentPage} / {Math.ceil(sortedObs.length / pageSize)}
                        </span>
                        <button
                          onClick={() => setCurrentPage((p) => Math.min(Math.ceil(sortedObs.length / pageSize), p + 1))}
                          disabled={currentPage >= Math.ceil(sortedObs.length / pageSize)}
                          className="cursor-pointer rounded border border-neutral-200 px-2 py-0.5 text-[11px] text-neutral-600 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {locale === "ar" ? "التالي" : "Next"}
                        </button>
                      </div>
                    </div>
                    );
                  })()}
                </div>
              ) : activeTab === "line" ? (
                /* LINE CHART */
                uniquePeriods.length < 3 ? (
                  <div className="flex items-center justify-center rounded-lg border border-neutral-200 bg-white py-12 text-sm text-neutral-500">
                    {locale === "ar"
                      ? "الرسم البياني الخطي يتطلب 3 فترات زمنية على الأقل. استخدم الرسم الشريطي."
                      : "Line chart requires 3+ time periods. Switch to Bar Chart for comparison."}
                  </div>
                ) : (
                  <div className="rounded-lg border border-neutral-200 bg-white p-4">
                    {seriesNames.length > MAX_CHART_SERIES && (
                      <p className="mt-1 px-4 text-[11px] text-[#757575]">
                        {locale === "ar"
                          ? `عرض 5 من ${seriesNames.length} مؤشر — اختر أقل للمقارنة الكاملة`
                          : `Showing 5 of ${seriesNames.length} indicators — select fewer to compare all`}
                      </p>
                    )}
                    <LineChartView
                      data={chartData}
                      series={visibleSeries}
                      colors={CHART_COLORS}
                      locale={locale}
                    />
                    {datasetDetail?.source?.organization && (
                      <p className="mt-2 px-4 pb-3 text-[11px] font-normal text-[#757575]">
                        {locale === "ar" ? `المصدر: ${datasetDetail.source.organization}` : `Source: ${datasetDetail.source.organization}`}
                      </p>
                    )}
                  </div>
                )
              ) : (
                /* BAR CHART */
                <div className="rounded-lg border border-neutral-200 bg-white p-4">
                  {seriesNames.length > MAX_CHART_SERIES && (
                    <p className="mt-1 px-4 text-[11px] text-[#757575]">
                      {locale === "ar"
                        ? `عرض 5 من ${seriesNames.length} مؤشر — اختر أقل للمقارنة الكاملة`
                        : `Showing 5 of ${seriesNames.length} indicators — select fewer to compare all`}
                    </p>
                  )}
                  <BarChartView
                    data={chartData}
                    series={visibleSeries}
                    colors={CHART_COLORS}
                    locale={locale}
                  />
                  {datasetDetail?.source?.organization && (
                    <p className="mt-2 px-4 pb-3 text-[11px] font-normal text-[#757575]">
                      {locale === "ar" ? `المصدر: ${datasetDetail.source.organization}` : `Source: ${datasetDetail.source.organization}`}
                    </p>
                  )}
                </div>
              )}

              </div>{/* close flex-1 content wrapper */}

              {/* Disclaimer */}
              <p className="shrink-0 pt-1 text-[10px] text-neutral-400">
                {locale === "ar"
                  ? "البيانات من مصادر رسمية. تم استخراجها برمجياً."
                  : "Data from official sources. Extracted programmatically."}{" "}
                <a href="https://github.com/datapalestine/data-palestine/issues/new" target="_blank" rel="noopener noreferrer"
                  className="text-neutral-500 underline transition-colors hover:text-neutral-700">
                  {locale === "ar" ? "إبلاغ" : "Report issue"}
                </a>
              </p>
            </div>
        </main>

        {/* ═══ RIGHT — INFO PANEL ═══ */}
        <aside className="explorer-info-panel" style={{ maxHeight: "100%", overflowY: "auto" }}>
          {datasetSlug && datasetDetail ? (
            <div className="rounded-lg border border-neutral-200 bg-white">
              {/* Header */}
              <div className="border-b border-neutral-100 px-4 py-2.5">
                <h3 className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                  {locale === "ar" ? "تفاصيل مجموعة البيانات" : "Dataset Details"}
                </h3>
              </div>
              {/* Dataset name */}
              <div className="border-b border-neutral-100 px-4 py-3">
                <h2 className="text-[13px] font-semibold leading-snug text-neutral-900">
                  {datasetDetail.name}
                </h2>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 border-b border-neutral-100">
                <div className="border-e border-neutral-100 px-4 py-3">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">
                    {locale === "ar" ? "نقاط البيانات" : "Data Points"}
                  </p>
                  <p className="mt-0.5 text-[16px] font-bold tabular-nums text-neutral-900">
                    {observations.length.toLocaleString()}
                  </p>
                </div>
                <div className="px-4 py-3">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">
                    {locale === "ar" ? "التحديث" : "Frequency"}
                  </p>
                  <p className="mt-0.5 text-[13px] font-semibold capitalize text-neutral-900">
                    {datasetDetail.update_frequency || "—"}
                  </p>
                </div>
              </div>

              {/* Metadata rows */}
              {timeRange && (
                <div className="border-b border-neutral-100 px-4 py-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">
                      {locale === "ar" ? "الفترة" : "Coverage"}
                    </span>
                    <span className="text-[12px] font-medium tabular-nums text-neutral-800">{timeRange}</span>
                  </div>
                </div>
              )}
              <div className="border-b border-neutral-100 px-4 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <span className="shrink-0 text-[10px] font-medium uppercase tracking-wider text-neutral-400">
                    {locale === "ar" ? "المصدر" : "Source"}
                  </span>
                  <span className="text-end text-[11px] font-medium text-neutral-800">
                    {sourceName || datasetDetail.source?.organization || "—"}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="p-4 pt-6 space-y-3">
                <a href={buildExportUrl(datasetSlug)} target="_blank" rel="noopener noreferrer"
                  className="flex w-full cursor-pointer items-center gap-3 rounded-md bg-[#1B5E20] px-4 py-2.5 text-[12px] font-medium text-white transition-colors hover:bg-[#0D3B10]">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  {locale === "ar" ? "تحميل CSV" : "Download CSV"}
                </a>
                <button onClick={handleCopyApi}
                  className="flex w-full cursor-pointer items-center gap-3 rounded-md border border-neutral-200 px-4 py-2.5 text-[12px] font-medium text-neutral-700 transition-colors hover:bg-neutral-50">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  {copiedApi ? (locale === "ar" ? "تم النسخ!" : "Copied!") : (locale === "ar" ? "نسخ رابط API" : "Copy API URL")}
                </button>
                {datasetDetail.source?.url && (
                  <a href={datasetDetail.source.url} target="_blank" rel="noopener noreferrer"
                    className="flex w-full cursor-pointer items-center gap-3 rounded-md border border-neutral-200 px-4 py-2.5 text-[12px] font-medium text-neutral-700 transition-colors hover:bg-neutral-50">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                      <polyline points="15 3 21 3 21 9" />
                      <line x1="10" y1="14" x2="21" y2="3" />
                    </svg>
                    {locale === "ar" ? "ملف المصدر" : "Source File"}
                  </a>
                )}
              </div>
            </div>
          ) : (
            /* Empty state */
            <div className="rounded-lg border border-neutral-200 bg-white p-4">
              <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
                {locale === "ar" ? "تفاصيل مجموعة البيانات" : "Dataset Details"}
              </h3>
              <div className="flex flex-col items-center py-6 text-center">
                <svg width="32" height="32" viewBox="0 0 48 48" fill="none" className="mb-3 text-neutral-300">
                  <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" />
                  <path d="M16 20h16M16 28h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <p className="text-[12px] text-neutral-400">
                  {locale === "ar"
                    ? "اختر مجموعة بيانات لعرض التفاصيل"
                    : "Select a dataset to view details, metadata, and export options."}
                </p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

// ─── Geography tree node ────────────────────────────────
function GeoNode({
  node, level, localGeos, toggleGeo, geoCheckState,
}: {
  node: Geography;
  level: number;
  localGeos: string[];
  toggleGeo: (n: Geography) => void;
  geoCheckState: (n: Geography) => { checked: boolean; indeterminate: boolean };
}) {
  const state = geoCheckState(node);
  const padStart = level * 16;

  return (
    <>
      <label
        className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-[12px] transition-colors hover:bg-neutral-50"
        style={{ paddingInlineStart: `${padStart + 8}px` }}
      >
        <input
          type="checkbox"
          checked={state.checked}
          ref={(el) => { if (el) el.indeterminate = state.indeterminate; }}
          onChange={() => toggleGeo(node)}
          className="cursor-pointer accent-[#1B5E20]"
        />
        <span className={state.checked ? "font-medium text-[#1B5E20]" : "text-neutral-700"}>
          {node.name}
        </span>
      </label>
      {node.children?.map((child) => (
        <GeoNode key={child.code} node={child} level={level + 1}
          localGeos={localGeos} toggleGeo={toggleGeo} geoCheckState={geoCheckState} />
      ))}
    </>
  );
}
