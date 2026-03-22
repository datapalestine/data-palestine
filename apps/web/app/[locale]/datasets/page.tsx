import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { getDatasets } from "@/lib/api-client";

const CATEGORIES = [
  { slug: "economy", label_en: "Economy & Trade", label_ar: "الاقتصاد والتجارة" },
  { slug: "population", label_en: "Demographics", label_ar: "السكان" },
  { slug: "labor", label_en: "Labor", label_ar: "العمل" },
  { slug: "health", label_en: "Health", label_ar: "الصحة" },
  { slug: "infrastructure", label_en: "Infrastructure", label_ar: "البنية التحتية" },
  { slug: "environment", label_en: "Environment", label_ar: "البيئة" },
  { slug: "governance", label_en: "Governance", label_ar: "الحوكمة" },
];

export default async function DataCatalogPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const { locale } = await params;
  const query = await searchParams;
  const t = await getTranslations("explore");
  const tHome = await getTranslations("home");

  const category = query.category;
  const search = query.search;
  const page = Number(query.page) || 1;

  const { data: datasets, meta } = await getDatasets(locale, {
    category,
    search,
    page,
    per_page: 21,
    sort: "name",
  });

  return (
    <div className="bg-[#FAFAFA]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Page header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              {t("title")}
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              {t("results.showing", { count: meta.total })}
            </p>
          </div>

          {/* Search */}
          <form
            action={`/${locale}/datasets`}
            className="flex w-full gap-2 sm:w-72"
          >
            {category && (
              <input type="hidden" name="category" value={category} />
            )}
            <input
              type="search"
              name="search"
              defaultValue={search}
              placeholder="Search..."
              className="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-[#1B5E20] focus:outline-none focus:ring-1 focus:ring-[#1B5E20]"
            />
          </form>
        </div>

        {/* Category filter pills */}
        <div className="mt-5 flex gap-2 overflow-x-auto pb-1">
          <Link
            href={`/${locale}/datasets`}
            className={`shrink-0 rounded-full border px-4 py-1.5 text-[13px] font-medium transition-colors ${
              !category
                ? "border-[#1B5E20] bg-[#1B5E20] text-white"
                : "border-neutral-300 bg-white text-neutral-600 hover:border-neutral-400"
            }`}
          >
            {locale === "ar" ? "الكل" : "All"}
          </Link>
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/${locale}/datasets?category=${cat.slug}`}
              className={`shrink-0 rounded-full border px-4 py-1.5 text-[13px] font-medium transition-colors ${
                category === cat.slug
                  ? "border-[#1B5E20] bg-[#1B5E20] text-white"
                  : "border-neutral-300 bg-white text-neutral-600 hover:border-neutral-400"
              }`}
            >
              {locale === "ar" ? cat.label_ar : cat.label_en}
            </Link>
          ))}
        </div>

        {/* Dataset grid */}
        {datasets.length === 0 ? (
          <div className="mt-16 text-center">
            <p className="text-neutral-500">{t("results.noResults")}</p>
          </div>
        ) : (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {datasets.map((ds) => (
              <Link
                key={ds.slug}
                href={`/${locale}/datasets/${ds.slug}`}
                className="group flex flex-col rounded-lg border border-neutral-200 bg-white p-5 transition-all hover:border-neutral-300 hover:shadow-sm"
              >
                {ds.category && (
                  <span
                    className={`badge-${ds.category.slug} inline-block self-start rounded-full px-2.5 py-0.5 text-[11px] font-medium`}
                  >
                    {ds.category.name}
                  </span>
                )}
                <h3 className="mt-2 line-clamp-2 text-sm font-semibold text-neutral-900 group-hover:text-[#1B5E20]">
                  {ds.name}
                </h3>
                <p className="mt-1.5 line-clamp-2 flex-1 text-[12px] leading-relaxed text-neutral-500">
                  {ds.description}
                </p>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 border-t border-neutral-100 pt-3 text-[11px] text-neutral-400">
                  <span className="font-medium tabular-nums">
                    {ds.indicator_count}{" "}
                    {locale === "ar" ? "مؤشر" : "indicators"}
                  </span>
                  {ds.source && (
                    <span className="truncate">{ds.source.organization}</span>
                  )}
                  {ds.temporal_coverage.start && ds.temporal_coverage.end && (
                    <span className="tabular-nums">
                      {ds.temporal_coverage.start.slice(0, 4)}–
                      {ds.temporal_coverage.end.slice(0, 4)}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {meta.total_pages > 1 && (
          <div className="mt-8 flex items-center justify-center gap-2">
            {page > 1 && (
              <Link
                href={`/${locale}/datasets?page=${page - 1}${category ? `&category=${category}` : ""}${search ? `&search=${search}` : ""}`}
                className="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm text-neutral-600 hover:bg-neutral-50"
              >
                ←
              </Link>
            )}
            <span className="px-3 text-[13px] tabular-nums text-neutral-500">
              {page} / {meta.total_pages}
            </span>
            {page < meta.total_pages && (
              <Link
                href={`/${locale}/datasets?page=${page + 1}${category ? `&category=${category}` : ""}${search ? `&search=${search}` : ""}`}
                className="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm text-neutral-600 hover:bg-neutral-50"
              >
                →
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
