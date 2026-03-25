import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { getIndicators, getDatasets, getObservations } from "@/lib/api-client";
import { formatValue, formatYear } from "@/lib/formatters";
import { Sparkline, BarSparkline } from "@/components/charts/Sparkline";

// --- Key indicator codes (World Bank) ---
const KEY_INDICATOR_CODES = [
  "population_total",
  "gdp_current_usd",
  "unemployment_rate",
  "life_expectancy",
];

const KEY_INDICATOR_LABELS: Record<string, { en: string; ar: string }> = {
  population_total: { en: "Population", ar: "السكان" },
  gdp_current_usd: { en: "GDP (current US$)", ar: "الناتج المحلي الإجمالي" },
  unemployment_rate: { en: "Unemployment", ar: "البطالة" },
  life_expectancy: { en: "Life Expectancy", ar: "متوسط العمر المتوقع" },
};

// --- Highlight card configs ---
interface HighlightConfig {
  id: string;
  title_en: string;
  title_ar: string;
  color: string;
  fillColor: string;
  dataset: string;
  indicatorCode: string;
  format: "currency" | "percent" | "number" | "large";
  chartType: "line" | "bar";
  source_en: string;
}

const HIGHLIGHTS: HighlightConfig[] = [
  {
    id: "life",
    title_en: "Life expectancy",
    title_ar: "متوسط العمر المتوقع",
    color: "#2E7D32",
    fillColor: "#2E7D32",
    dataset: "world-bank-development-indicators",
    indicatorCode: "life_expectancy",
    format: "number",
    chartType: "line",
    source_en: "World Bank",
  },
  {
    id: "conflict",
    title_en: "Lives lost in Gaza",
    title_ar: "أرواح فُقدت في غزة",
    color: "#757575",
    fillColor: "#757575",
    dataset: "gaza-daily-casualties",
    indicatorCode: "gaza_killed_cum",
    format: "number",
    chartType: "line",
    source_en: "Tech for Palestine / MoH",
  },
  {
    id: "children",
    title_en: "Children killed in Gaza",
    title_ar: "أطفال قُتلوا في غزة",
    color: "#C62828",
    fillColor: "#C62828",
    dataset: "gaza-daily-casualties",
    indicatorCode: "gaza_killed_children_cum",
    format: "number",
    chartType: "line",
    source_en: "Tech for Palestine / MoH",
  },
  {
    id: "infrastructure",
    title_en: "Homes destroyed in Gaza",
    title_ar: "منازل دُمرت في غزة",
    color: "#EF6C00",
    fillColor: "#EF6C00",
    dataset: "gaza-infrastructure-damage",
    indicatorCode: "gaza_residential_destroyed",
    format: "number",
    chartType: "line",
    source_en: "Tech for Palestine / OCHA",
  },
];

async function getHighlightData(locale: string, config: HighlightConfig) {
  try {
    const { data: indicators } = await getIndicators(locale, {
      dataset: config.dataset,
      per_page: 50,
    });

    const ind = indicators.find((i) => i.code === config.indicatorCode);
    if (!ind) return null;

    // Fetch time series for sparkline
    const { data: obs } = await getObservations(locale, {
      indicator: ind.id,
      sort: "time",
      order: "asc",
      per_page: 500,
    });

    if (obs.length === 0) return null;

    const values = obs
      .filter((o) => o.value !== null)
      .map((o) => o.value as number);

    const latest = obs[obs.length - 1];
    const latestValue = latest.value ?? 0;
    const latestYear = formatYear(latest.time_period);

    // Trend: compare last two
    let trend: "up" | "down" | "flat" = "flat";
    if (obs.length >= 2) {
      const prev = obs[obs.length - 2].value;
      if (prev !== null && latest.value !== null) {
        trend = latest.value > prev ? "up" : latest.value < prev ? "down" : "flat";
      }
    }

    return {
      name: ind.name,
      value: latestValue,
      year: latestYear,
      trend,
      sparkData: values,
      unitSymbol: ind.unit_symbol,
      decimals: ind.decimals,
      datasetSlug: config.dataset,
    };
  } catch (e) {
    console.error(`Failed to fetch highlight ${config.id}:`, e);
    return null;
  }
}

async function getKeyIndicatorData(locale: string) {
  const { data: indicators } = await getIndicators(locale, {
    dataset: "world-bank-development-indicators",
    per_page: 10,
  });

  const results = [];
  for (const code of KEY_INDICATOR_CODES) {
    const ind = indicators.find((i) => i.code === code);
    if (!ind || !ind.latest_value) continue;

    let trend: "up" | "down" | "flat" = "flat";
    try {
      const { data: obs } = await getObservations(locale, {
        indicator: ind.id,
        sort: "time",
        order: "desc",
        per_page: 2,
      });
      if (obs.length >= 2 && obs[0].value !== null && obs[1].value !== null) {
        trend = obs[0].value > obs[1].value ? "up" : obs[0].value < obs[1].value ? "down" : "flat";
      }
    } catch {}

    results.push({
      code: ind.code,
      name: KEY_INDICATOR_LABELS[ind.code]?.[locale as "en" | "ar"] || ind.name,
      value: ind.latest_value.value,
      unit_symbol: ind.unit_symbol,
      decimals: ind.decimals,
      year: formatYear(ind.latest_value.time_period),
      trend,
    });
  }
  return results;
}

const CATEGORIES = [
  { slug: "economy", label_en: "Economy", label_ar: "الاقتصاد" },
  { slug: "population", label_en: "Demographics", label_ar: "السكان" },
  { slug: "labor", label_en: "Labor", label_ar: "العمل" },
  { slug: "health", label_en: "Health", label_ar: "الصحة" },
  { slug: "conflict", label_en: "Conflict", label_ar: "النزاع" },
  { slug: "infrastructure", label_en: "Infrastructure", label_ar: "البنية التحتية" },
  { slug: "governance", label_en: "Governance", label_ar: "الحوكمة" },
];

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("home");

  // Timeout wrapper to prevent SSR from hanging indefinitely
  const withTimeout = <T,>(promise: Promise<T>, fallback: T, ms = 10000): Promise<T> =>
    Promise.race([promise, new Promise<T>((resolve) => setTimeout(() => resolve(fallback), ms))]);

  // Fetch essentials first (2 calls)
  const datasetsRes = await withTimeout(
    getDatasets(locale, { per_page: 4, sort: "updated", order: "desc" }),
    { data: [], meta: { total: 0, page: 1, per_page: 4, total_pages: 0 } },
  );
  const datasets = datasetsRes.data;
  const totalDatasets = datasetsRes.meta.total;

  let totalIndicators = 15250;
  let totalObservations = 87672;
  try {
    const statsRes = await withTimeout(getIndicators(locale, { per_page: 1 }), null);
    if (statsRes) totalIndicators = statsRes.meta.total;
  } catch {}

  // Fetch highlights sequentially to avoid overloading 1-CPU server
  const highlightData: (Awaited<ReturnType<typeof getHighlightData>>)[] = [];
  for (const h of HIGHLIGHTS) {
    highlightData.push(await withTimeout(getHighlightData(locale, h), null));
  }

  // Key indicators last (makes 5 sequential API calls internally)
  const keyIndicators = await withTimeout(getKeyIndicatorData(locale), []);

  return (
    <div>
      {/* Hero */}
      <section className="bg-white">
        <div className="mx-auto max-w-5xl px-4 pb-12 pt-14 text-center sm:px-6 sm:pb-16 sm:pt-20">
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 sm:text-4xl md:text-5xl">
            {t("hero.title")}
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-neutral-500 sm:text-lg">
            {t("hero.subtitle")}
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href={`/${locale}/explore`}
              className="inline-flex w-full items-center justify-center rounded-lg bg-[#1B5E20] px-6 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#0D3B10] sm:w-auto"
            >
              {t("hero.exploreButton")}
            </Link>
            <Link
              href={`/${locale}/developers`}
              className="inline-flex w-full items-center justify-center rounded-lg border border-neutral-300 px-6 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 sm:w-auto"
            >
              {t("hero.apiButton")}
            </Link>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-6 px-4 py-4 text-center sm:gap-12 sm:px-6">
          <Stat value={totalDatasets} label={t("stats.datasets")} />
          <div className="hidden h-5 w-px bg-neutral-200 sm:block" />
          <Stat value={totalIndicators.toLocaleString()} label={t("stats.indicators")} />
          <div className="hidden h-5 w-px bg-neutral-200 sm:block" />
          <Stat value={totalObservations.toLocaleString()} label={t("stats.observations")} />
        </div>
      </section>

      {/* Palestine in Numbers — Highlight Cards */}
      <section className="bg-[#FAFAFA] py-12 sm:py-16">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <h2 className="text-lg font-semibold text-neutral-900">
            {locale === "ar" ? "فلسطين في أرقام" : "Palestine in numbers"}
          </h2>
          <p className="mt-1 text-sm text-neutral-500">
            {locale === "ar"
              ? "مؤشرات رئيسية من مصادر بيانات موثوقة"
              : "Key indicators from verified data sources"}
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {HIGHLIGHTS.map((config, i) => {
              const data = highlightData[i];
              if (!data) return null;

              const isInverse = false;
              const trendColor =
                data.trend === "flat"
                  ? "text-neutral-400"
                  : (data.trend === "up") !== isInverse
                    ? "text-[#2E7D32]"
                    : "text-[#C62828]";

              return (
                <Link
                  key={config.id}
                  href={`/${locale}/datasets/${data.datasetSlug}`}
                  className="group flex items-start justify-between rounded-lg border border-neutral-200 bg-white p-5 transition-all hover:border-neutral-300 hover:shadow-sm"
                >
                  <div className="min-w-0 flex-1">
                    <p
                      className="text-xs font-semibold uppercase tracking-wider"
                      style={{ color: config.color }}
                    >
                      {locale === "ar" ? config.title_ar : config.title_en}
                    </p>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-bold tabular-nums text-neutral-900">
                        {formatValue(data.value, data.unitSymbol, data.decimals)}
                      </span>
                      {data.trend !== "flat" && (
                        <span className={`text-xs font-semibold ${trendColor}`}>
                          {data.trend === "up" ? "▲" : "▼"}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-[11px] text-neutral-400">
                      {data.year} · {config.source_en}
                    </p>
                    <p className="mt-2 text-[11px] font-medium text-[#2E7D32] opacity-0 transition-opacity group-hover:opacity-100">
                      {locale === "ar" ? "استكشف البيانات ←" : "Explore this data →"}
                    </p>
                  </div>
                  <div className="ms-4 shrink-0">
                    {config.chartType === "bar" ? (
                      <BarSparkline
                        data={data.sparkData.slice(-24)}
                        width={100}
                        height={44}
                        color={config.color}
                      />
                    ) : (
                      <Sparkline
                        data={data.sparkData.slice(-30)}
                        width={100}
                        height={44}
                        color={config.color}
                        fillColor={config.fillColor}
                      />
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* Key Indicators (compact row) */}
      <section className="border-b border-neutral-200 bg-white py-8 sm:py-10">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <h2 className="text-lg font-semibold text-neutral-900">
            {t("keyIndicators.title")}
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {keyIndicators.map((ind) => {
              const isInverse = ind.code === "unemployment_rate";
              const trendColor =
                ind.trend === "flat"
                  ? "text-neutral-400"
                  : (ind.trend === "up") !== isInverse
                    ? "text-[#2E7D32]"
                    : "text-[#C62828]";

              return (
                <div
                  key={ind.code}
                  className="rounded-lg border border-neutral-200 bg-white px-5 py-4"
                >
                  <p className="text-[13px] font-medium text-neutral-500">
                    {ind.name}
                  </p>
                  <div className="mt-1.5 flex items-baseline gap-2">
                    <span className="text-2xl font-bold tabular-nums text-neutral-900">
                      {formatValue(ind.value, ind.unit_symbol, ind.decimals)}
                    </span>
                    {ind.trend !== "flat" && (
                      <span className={`text-xs font-semibold ${trendColor}`}>
                        {ind.trend === "up" ? "▲" : "▼"}
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-[11px] text-neutral-400">
                    {t("keyIndicators.asOf", { date: ind.year })}
                    {" · "}
                    {t("keyIndicators.source", { source: "World Bank" })}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Browse by category + recent datasets */}
      <section className="bg-white py-12 sm:py-16">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("featuredDatasets.title")}
            </h2>
            <Link
              href={`/${locale}/datasets`}
              className="text-[13px] font-medium text-[#1B5E20] hover:underline"
            >
              {t("featuredDatasets.viewAll")}
            </Link>
          </div>

          {/* Category pills */}
          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {CATEGORIES.map((cat) => (
              <Link
                key={cat.slug}
                href={`/${locale}/datasets?category=${cat.slug}`}
                className={`badge-${cat.slug} shrink-0 rounded-full px-3.5 py-1 text-[13px] font-medium transition-opacity hover:opacity-80`}
              >
                {locale === "ar" ? cat.label_ar : cat.label_en}
              </Link>
            ))}
          </div>

          {/* Dataset cards */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {datasets.map((ds) => (
              <Link
                key={ds.slug}
                href={`/${locale}/datasets/${ds.slug}`}
                className="group rounded-lg border border-neutral-200 bg-white p-5 transition-all hover:border-neutral-300 hover:shadow-sm"
              >
                {ds.category && (
                  <span
                    className={`badge-${ds.category.slug} inline-block rounded-full px-2.5 py-0.5 text-[11px] font-medium`}
                  >
                    {ds.category.name}
                  </span>
                )}
                <h3 className="mt-2 line-clamp-2 text-sm font-semibold text-neutral-900 group-hover:text-[#1B5E20]">
                  {ds.name}
                </h3>
                <div className="mt-3 flex items-center gap-3 text-[11px] text-neutral-400">
                  <span>
                    {t("featuredDatasets.indicators", {
                      count: ds.indicator_count,
                    })}
                  </span>
                  {ds.source && (
                    <>
                      <span className="text-neutral-200">·</span>
                      <span>{ds.source.organization}</span>
                    </>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-xl font-bold tabular-nums text-[#1B5E20]">
        {typeof value === "number" ? value.toLocaleString() : value}
      </span>
      <span className="text-[13px] text-neutral-500">{label}</span>
    </div>
  );
}
