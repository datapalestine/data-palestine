import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { DataExplorer } from "@/components/data/DataExplorer";

export default async function ExplorePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("explore");

  // Serialize translations for the client component
  const translations = {
    title: t("title"),
    subtitle: t("subtitle"),
    filters: {
      dataset: t("filters.dataset"),
      indicator: t("filters.indicator"),
      category: t("filters.category"),
      geography: t("filters.geography"),
      timeRange: t("filters.timeRange"),
      yearFrom: t("filters.yearFrom"),
      yearTo: t("filters.yearTo"),
      source: t("filters.source"),
      apply: t("filters.apply"),
      clearAll: t("filters.clearAll"),
      selectDataset: t("filters.selectDataset"),
      selectIndicator: t("filters.selectIndicator"),
      filtersLabel: t("filters.filtersLabel"),
    },
    results: {
      showing: t.raw("results.showing"),
      noResults: t("results.noResults"),
      noSelection: t("results.noSelection"),
      sortBy: t("results.sortBy"),
      chartError: t("results.chartError"),
    },
    export: {
      title: t("export.title"),
      csv: t("export.csv"),
      json: t("export.json"),
      excel: t("export.excel"),
      api: t("export.api"),
      copied: t("export.copied"),
    },
    chart: {
      lineChart: t("chart.lineChart"),
      barChart: t("chart.barChart"),
      table: t("chart.table"),
      map: t("chart.map"),
      overflowBadge: t.raw("chart.overflowBadge"),
      source: t.raw("chart.source"),
    },
    table: {
      timePeriod: t("table.timePeriod"),
      geography: t("table.geography"),
      indicator: t("table.indicator"),
      value: t("table.value"),
      source: t("table.source"),
    },
    info: {
      observations: t.raw("info.observations"),
      timeRange: t.raw("info.timeRange"),
      source: t.raw("info.source"),
    },
  };

  return (
    <div className="bg-[#FAFAFA] min-h-screen">
      {/* Page header */}
      <div className="border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <h1 className="text-xl font-bold text-neutral-900">
            {translations.title}
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            {translations.subtitle}
          </p>
        </div>
      </div>

      <Suspense
        fallback={
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
            <div className="h-96 animate-pulse rounded-lg bg-neutral-100" />
          </div>
        }
      >
        <DataExplorer locale={locale} t={translations} />
      </Suspense>
    </div>
  );
}
