import { getTranslations } from "next-intl/server";
import Link from "next/link";

export default async function CuratePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("nav");

  return (
    <div className="mx-auto max-w-2xl px-4 py-20 text-center sm:px-6">
      <div className="mb-6 text-5xl text-neutral-300">&#9881;</div>
      <h1 className="text-2xl font-bold text-neutral-900">
        {locale === "ar" ? "قريبًا" : "Coming Soon"}
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-neutral-500">
        {locale === "ar"
          ? "نعمل على بناء أداة تتيح للمساهمين مراجعة وتنظيف البيانات بشكل تعاوني. ترقبوا التحديثات!"
          : "We're building a collaborative tool that lets contributors review and clean datasets. Stay tuned!"}
      </p>
      <p className="mt-2 text-sm text-neutral-400">
        {locale === "ar"
          ? "في هذه الأثناء، يمكنك المساهمة عبر GitHub."
          : "In the meantime, you can contribute via GitHub."}
      </p>
      <div className="mt-8 flex items-center justify-center gap-3">
        <Link
          href={`/${locale}`}
          className="rounded-md bg-[#2E7D32] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#1B5E20] transition-colors"
        >
          {t("home")}
        </Link>
        <a
          href="https://github.com/datapalestine/data-palestine"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          GitHub
        </a>
      </div>
    </div>
  );
}
