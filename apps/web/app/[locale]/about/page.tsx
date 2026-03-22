import { getTranslations } from "next-intl/server";

export default async function AboutPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("about");

  return (
    <div className="bg-[#FAFAFA]">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
        <h1 className="text-2xl font-bold text-neutral-900 sm:text-3xl">
          {t("title")}
        </h1>

        <div className="mt-8 space-y-8">
          {/* Mission */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {locale === "ar" ? "مهمتنا" : "Our Mission"}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {locale === "ar"
                ? "Data Palestine منصة بيانات مفتوحة غير ربحية تجمع وتحدّث وتخدم البيانات الإحصائية والإنسانية والاجتماعية والاقتصادية الفلسطينية. نحوّل ملفات PDF المتناثرة والواجهات القديمة وقواعد البيانات المعزولة إلى منصة موحدة قابلة للبحث ومدعومة بواجهة برمجة تطبيقات."
                : "Data Palestine is a nonprofit open data platform that aggregates, modernizes, and serves Palestinian statistical, humanitarian, and socioeconomic data. We transform scattered PDFs, outdated interfaces, and siloed databases into a unified, searchable, API-driven platform."}
            </p>
          </section>

          {/* Data Sources */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {locale === "ar" ? "مصادر البيانات" : "Data Sources"}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {locale === "ar"
                ? "نجمع البيانات من مصادر رسمية موثوقة:"
                : "We aggregate data from verified official sources:"}
            </p>
            <ul className="mt-3 space-y-1.5 text-sm text-neutral-600">
              <li>
                <span className="font-medium text-neutral-800">PCBS</span>:{" "}
                {locale === "ar"
                  ? "الجهاز المركزي للإحصاء الفلسطيني"
                  : "Palestinian Central Bureau of Statistics"}
              </li>
              <li>
                <span className="font-medium text-neutral-800">World Bank</span>:{" "}
                {locale === "ar"
                  ? "مؤشرات التنمية العالمية"
                  : "World Development Indicators"}
              </li>
              <li>
                <span className="font-medium text-neutral-800">Tech for Palestine</span>:{" "}
                {locale === "ar"
                  ? "بيانات النزاع والضحايا"
                  : "Conflict and casualty data"}
              </li>
            </ul>
          </section>

          {/* Methodology */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {locale === "ar" ? "المنهجية" : "Methodology"}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {locale === "ar"
                ? "يتم استخلاص جميع البيانات برمجياً من المصادر الأصلية. كل نقطة بيانات مرتبطة بوثيقة المصدر الأصلية مع عنوان URL والتاريخ. نحن لا نحرّر البيانات أو نضيف تفسيراً. نقدم الأرقام كما هي من المصادر الرسمية."
                : "All data is extracted programmatically from original sources. Every data point links back to its original source document with URL and date. We do not editorialize or add interpretation. We present the numbers as published by official sources."}
            </p>
          </section>

          {/* Open Source */}
          <section className="rounded-lg border border-neutral-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-neutral-900">
              {locale === "ar" ? "مشروع مفتوح المصدر" : "Open Source"}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {locale === "ar"
                ? "Data Palestine مشروع مفتوح المصدر بالكامل تحت رخصة MIT. الكود المصدري وجميع خطوط أنابيب البيانات متاحة على GitHub."
                : "Data Palestine is fully open source under the MIT license. The source code and all data pipelines are available on GitHub."}
            </p>

            <div className="mt-4">
              <a
                href="https://github.com/datapalestine/data-palestine"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-700"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                {locale === "ar" ? "عرض على GitHub" : "View on GitHub"}
              </a>
            </div>

            <h3 className="mt-6 text-sm font-semibold text-neutral-900">
              {locale === "ar" ? "طرق المساهمة" : "Ways to Contribute"}
            </h3>
            <ul className="mt-2 space-y-1.5 text-sm text-neutral-600">
              <li>
                {locale === "ar"
                  ? "• الإبلاغ عن أخطاء في البيانات عبر قوالب GitHub"
                  : "• Report data inaccuracies via GitHub issue templates"}
              </li>
              <li>
                {locale === "ar"
                  ? "• إضافة مصادر بيانات جديدة عبر خطوط الأنابيب"
                  : "• Add new data sources via data pipelines"}
              </li>
              <li>
                {locale === "ar"
                  ? "• تحسين واجهة المستخدم والترجمات"
                  : "• Improve the UI and translations"}
              </li>
              <li>
                {locale === "ar"
                  ? "• المساهمة في التوثيق والمنهجية"
                  : "• Contribute to documentation and methodology"}
              </li>
            </ul>
          </section>

          {/* License */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {locale === "ar" ? "الترخيص" : "License"}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {locale === "ar"
                ? "كود المشروع مرخص تحت MIT. البيانات مرخصة تحت CC-BY-4.0، يمكنك استخدامها بحرية مع ذكر المصدر."
                : "Project code is MIT licensed. Data is licensed under CC-BY-4.0, free to use with attribution."}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
