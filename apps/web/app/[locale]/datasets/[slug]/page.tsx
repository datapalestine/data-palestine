import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { getDataset } from "@/lib/api-client";

export default async function DatasetDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const t = await getTranslations("dataset");
  const tCommon = await getTranslations("common");

  let dataset;
  try {
    const res = await getDataset(slug, locale);
    dataset = res.data;
  } catch {
    return (
      <div className="mx-auto max-w-4xl px-4 py-20 text-center">
        <p className="text-lg font-semibold text-neutral-900">
          Dataset not found
        </p>
        <Link
          href={`/${locale}/datasets`}
          className="mt-3 inline-block text-sm text-[#1B5E20] hover:underline"
        >
          {tCommon("backTo", { page: "datasets" })}
        </Link>
      </div>
    );
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <div className="bg-[#FAFAFA]">
      {/* Header area — white */}
      <div className="border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          {/* Breadcrumb */}
          <nav className="mb-4 text-[13px] text-neutral-400">
            <Link
              href={`/${locale}/datasets`}
              className="hover:text-[#1B5E20]"
            >
              {locale === "ar" ? "مجموعات البيانات" : "Datasets"}
            </Link>
            <span className="mx-1.5">/</span>
            <span className="text-neutral-600">{dataset.name}</span>
          </nav>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1">
              {dataset.category && (
                <span
                  className={`badge-${dataset.category.slug} inline-block rounded-full px-3 py-0.5 text-[12px] font-medium`}
                >
                  {dataset.category.name}
                </span>
              )}
              <h1 className="mt-2 text-xl font-bold text-neutral-900 sm:text-2xl">
                {dataset.name}
              </h1>
              {dataset.description && (
                <p className="mt-2 text-sm leading-relaxed text-neutral-500">
                  {dataset.description}
                </p>
              )}
            </div>

            <a
              href={`${apiBase}/api/v1/export/${slug}`}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-[#1B5E20] px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#0D3B10]"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M8 2v8m0 0L5 7m3 3l3-3M3 12h10" />
              </svg>
              {t("download")}
            </a>
          </div>
        </div>
      </div>

      {/* Content area */}
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {/* Metadata cards */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {dataset.source && (
            <MetaCard label={t("source")}>
              {dataset.source.url ? (
                <a
                  href={dataset.source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#1B5E20] hover:underline"
                >
                  {dataset.source.organization}
                </a>
              ) : (
                dataset.source.organization
              )}
            </MetaCard>
          )}
          {dataset.temporal_coverage.start && (
            <MetaCard label={t("temporal")}>
              <span className="tabular-nums">
                {dataset.temporal_coverage.start?.slice(0, 4)} –{" "}
                {dataset.temporal_coverage.end?.slice(0, 4)}
              </span>
            </MetaCard>
          )}
          {dataset.update_frequency && (
            <MetaCard label={t("frequency")}>
              <span className="capitalize">{dataset.update_frequency}</span>
            </MetaCard>
          )}
          <MetaCard label={t("license")}>{dataset.license}</MetaCard>
        </div>

        {/* Data accuracy notice */}
        <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50/50 px-4 py-3">
          <p className="text-[12px] leading-relaxed text-neutral-500">
            {locale === "ar"
              ? "تم استخلاص هذه البيانات برمجياً من مصادر رسمية وقد تحتوي على أخطاء في الاستخراج. يرجى التحقق من الأرقام الحاسمة مقابل المصدر الأصلي المذكور أعلاه."
              : "This data was extracted programmatically from official sources and may contain extraction errors. Please verify critical figures against the original source linked above."}{" "}
            <a
              href="https://github.com/datapalestine/data-palestine/issues/new?template=data-correction.md"
              className="text-[#1B5E20] underline hover:no-underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {locale === "ar" ? "الإبلاغ عن خطأ" : "Report an inaccuracy"}
            </a>
          </p>
        </div>

        {/* Methodology */}
        {dataset.methodology && (
          <div className="mt-8 rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-900">
              {t("methodology")}
            </h2>
            <p className="mt-2 text-[13px] leading-relaxed text-neutral-500">
              {dataset.methodology}
            </p>
          </div>
        )}

        {/* Indicators table */}
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-neutral-900">
            {t("indicators")}{" "}
            <span className="font-normal text-neutral-400">
              ({dataset.indicators.length})
            </span>
          </h2>
          <div className="mt-3 overflow-hidden rounded-lg border border-neutral-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50 text-start">
                  <th className="px-4 py-2.5 text-[12px] font-semibold uppercase tracking-wider text-neutral-500">
                    {locale === "ar" ? "المؤشر" : "Indicator"}
                  </th>
                  <th className="hidden px-4 py-2.5 text-[12px] font-semibold uppercase tracking-wider text-neutral-500 sm:table-cell">
                    {locale === "ar" ? "الرمز" : "Code"}
                  </th>
                  <th className="px-4 py-2.5 text-[12px] font-semibold uppercase tracking-wider text-neutral-500">
                    {locale === "ar" ? "الوحدة" : "Unit"}
                  </th>
                </tr>
              </thead>
              <tbody>
                {dataset.indicators.map((ind, i) => (
                  <tr
                    key={ind.id}
                    className={`border-b border-neutral-100 last:border-0 ${
                      i % 2 === 1 ? "bg-neutral-50/50" : ""
                    }`}
                  >
                    <td className="px-4 py-2.5 text-neutral-900">
                      {ind.name}
                    </td>
                    <td className="hidden px-4 py-2.5 font-mono text-[12px] text-neutral-400 sm:table-cell">
                      {ind.code}
                    </td>
                    <td className="px-4 py-2.5 text-neutral-500">
                      {ind.unit}
                      {ind.unit_symbol ? ` (${ind.unit_symbol})` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetaCard({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-neutral-900">{children}</dd>
    </div>
  );
}
