import { getTranslations } from "next-intl/server";
import Link from "next/link";

export default async function IndicatorDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const t = await getTranslations("indicator");

  return (
    <div className="bg-[#FAFAFA]">
      <div className="mx-auto max-w-3xl px-4 py-12 text-center sm:px-6">
        <h1 className="text-xl font-bold text-neutral-900">
          {t("timeSeries")}
        </h1>
        <p className="mt-3 text-sm text-neutral-500">
          {locale === "ar"
            ? "صفحة تفاصيل المؤشر قيد التطوير. استخدم مستكشف البيانات لعرض السلاسل الزمنية."
            : "Indicator detail page is under development. Use the Data Explorer to view time series."}
        </p>
        <Link
          href={`/${locale}/explore`}
          className="mt-4 inline-block rounded-lg bg-[#1B5E20] px-5 py-2 text-sm font-medium text-white hover:bg-[#0D3B10]"
        >
          {locale === "ar" ? "فتح مستكشف البيانات" : "Open Data Explorer"}
        </Link>
      </div>
    </div>
  );
}
