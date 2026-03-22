import { getTranslations } from "next-intl/server";

const API_BASE = "https://datapalestine.org/api/v1";

const ENDPOINTS = [
  {
    method: "GET",
    path: "/datasets",
    desc_en: "List all datasets with pagination and filtering.",
    desc_ar: "عرض جميع مجموعات البيانات مع ترقيم الصفحات والتصفية.",
    params: "category, search, page, per_page, sort, lang",
    example: `{
  "data": [
    {
      "id": 1,
      "slug": "world-bank-development-indicators",
      "name": "World Bank Development Indicators",
      "category": { "slug": "economy", "name": "Economy & Trade" },
      "indicator_count": 4
    }
  ],
  "meta": { "total": 483, "page": 1, "per_page": 20, "total_pages": 25 }
}`,
  },
  {
    method: "GET",
    path: "/datasets/{slug}",
    desc_en: "Single dataset with full metadata and indicator list.",
    desc_ar: "مجموعة بيانات واحدة مع البيانات الوصفية الكاملة وقائمة المؤشرات.",
    params: "lang",
    example: `{
  "data": {
    "slug": "world-bank-development-indicators",
    "name": "World Bank Development Indicators",
    "indicators": [
      { "id": 1, "code": "gdp_current_usd", "name": "GDP (current US$)" }
    ]
  }
}`,
  },
  {
    method: "GET",
    path: "/indicators",
    desc_en: "List indicators. Filter by dataset or search by name.",
    desc_ar: "عرض المؤشرات. تصفية حسب مجموعة البيانات أو البحث بالاسم.",
    params: "dataset, search, page, per_page, lang",
    example: `{
  "data": [
    {
      "id": 1, "code": "gdp_current_usd",
      "name": "GDP (current US$)",
      "latest_value": { "value": 13711100000, "time_period": "2024-01-01" }
    }
  ]
}`,
  },
  {
    method: "GET",
    path: "/observations",
    desc_en: "Query data points. The main endpoint for fetching actual values.",
    desc_ar: "استعلام نقاط البيانات. نقطة الوصول الرئيسية لجلب القيم الفعلية.",
    params:
      "dataset, indicator, geography, year_from, year_to, time_precision, page, per_page, sort, order",
    example: `{
  "data": [
    {
      "time_period": "2024-01-01",
      "value": 13711100000,
      "geography": { "code": "PS", "name": "Palestine" },
      "indicator": { "code": "gdp_current_usd", "name": "GDP (current US$)" }
    }
  ]
}`,
  },
  {
    method: "GET",
    path: "/geographies",
    desc_en: "Geography list or tree. Returns Palestine, territories, and governorates.",
    desc_ar: "قائمة أو شجرة الجغرافيا. تعيد فلسطين والأقاليم والمحافظات.",
    params: "level, tree, lang",
    example: `{
  "data": [
    { "code": "PS", "name": "Palestine", "level": "country", "children": [
      { "code": "PS-WBK", "name": "West Bank", "level": "territory" }
    ]}
  ]
}`,
  },
  {
    method: "GET",
    path: "/export/{slug}",
    desc_en: "Download all observations for a dataset as a CSV file.",
    desc_ar: "تحميل جميع الملاحظات لمجموعة بيانات كملف CSV.",
    params: "geography, year_from, year_to",
    example: null,
  },
];

export default async function DevelopersPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("nav");
  const isAr = locale === "ar";

  return (
    <div className="bg-[#FAFAFA]">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
        <h1 className="text-2xl font-bold text-neutral-900 sm:text-3xl">
          {t("developers")}
        </h1>
        <p className="mt-2 text-sm text-neutral-500">
          {isAr
            ? "الوصول إلى بيانات فلسطين برمجياً. لا حاجة للتسجيل."
            : "Access Palestinian data programmatically. No registration required."}
        </p>

        <div className="mt-10 space-y-12">
          {/* Section A: Quick start */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "البداية السريعة" : "Quick start"}
            </h2>

            <div className="mt-4 space-y-4">
              <CodeBlock
                label="curl"
                code={`curl ${API_BASE}/datasets`}
              />

              <CodeBlock
                label="Python"
                code={`import requests

data = requests.get("${API_BASE}/observations", params={
    "dataset": "world-bank-development-indicators",
    "indicator": "gdp_current_usd",
    "year_from": 2020
}).json()

for obs in data["data"]:
    print(f"{obs['time_period']}: \${obs['value']:,.0f}")`}
              />

              <CodeBlock
                label="JavaScript"
                code={`const res = await fetch("${API_BASE}/datasets");
const { data, meta } = await res.json();
console.log(\`\${meta.total} datasets available\`);`}
              />
            </div>
          </section>

          {/* Section B: Base URL and response format */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "عنوان الأساس وتنسيق الاستجابة" : "Base URL and response format"}
            </h2>

            <div className="mt-4 space-y-3">
              <InfoRow
                label={isAr ? "العنوان الأساسي" : "Base URL"}
                value={API_BASE}
                mono
              />
              <InfoRow
                label={isAr ? "التنسيق" : "Response format"}
                value='{ "data": T | T[], "meta": { "total", "page", "per_page", "total_pages" } }'
                mono
              />
              <InfoRow
                label={isAr ? "التواريخ" : "Dates"}
                value="ISO 8601 (2024-01-01)"
              />
              <InfoRow
                label={isAr ? "ثنائي اللغة" : "Bilingual"}
                value={isAr ? "أضف ?lang=ar للأسماء بالعربية" : "Pass ?lang=ar for Arabic names"}
              />
              <InfoRow
                label={isAr ? "المصادقة" : "Authentication"}
                value={isAr ? "غير مطلوبة" : "Not required"}
              />
              <InfoRow
                label={isAr ? "حد الطلبات" : "Rate limit"}
                value={isAr ? "100 طلب/دقيقة" : "100 requests/minute"}
              />
            </div>
          </section>

          {/* Section C: Endpoints */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "نقاط الوصول" : "Endpoints"}
            </h2>

            <div className="mt-4 space-y-4">
              {ENDPOINTS.map((ep) => (
                <div
                  key={ep.path}
                  className="rounded-lg border border-neutral-200 bg-white"
                >
                  <div className="flex items-start justify-between gap-3 px-4 py-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-[#1B5E20]/10 px-1.5 py-0.5 text-[11px] font-bold text-[#1B5E20]">
                          {ep.method}
                        </span>
                        <code dir="ltr" className="text-sm font-medium text-neutral-900">
                          {ep.path}
                        </code>
                      </div>
                      <p className="mt-1 text-[13px] text-neutral-500">
                        {isAr ? ep.desc_ar : ep.desc_en}
                      </p>
                      <p className="mt-1 text-[11px] text-neutral-400">
                        {isAr ? "المعاملات" : "Params"}:{" "}
                        <span dir="ltr" className="inline">{ep.params}</span>
                      </p>
                    </div>
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1${ep.path.replace("{slug}", "world-bank-development-indicators")}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 text-[11px] font-medium text-[#1B5E20] hover:underline"
                    >
                      {isAr ? "جرّبه" : "Try it"} &rarr;
                    </a>
                  </div>
                  {ep.example && (
                    <div dir="ltr" className="border-t border-neutral-100 bg-neutral-50 px-4 py-3 text-left">
                      <pre className="overflow-x-auto text-[11px] leading-relaxed text-neutral-600">
                        {ep.example}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Section D: Client libraries */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "مكتبات العملاء" : "Client libraries"}
            </h2>
            <p className="mt-3 text-sm text-neutral-600">
              {isAr
                ? "مكتبات Python وJavaScript وR مخطط لها. حالياً واجهة REST تعمل مع أي عميل HTTP. يتوفر توثيق OpenAPI التفاعلي على:"
                : "Python, JavaScript, and R packages are planned. The REST API works with any HTTP client. Interactive OpenAPI docs are available at:"}
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md border border-neutral-300 px-3 py-1.5 text-[13px] font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Swagger UI
              </a>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/redoc`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md border border-neutral-300 px-3 py-1.5 text-[13px] font-medium text-neutral-700 hover:bg-neutral-50"
              >
                ReDoc
              </a>
            </div>
          </section>

          {/* Section E: Use cases */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "حالات الاستخدام" : "Use cases"}
            </h2>
            <ul className="mt-3 space-y-2 text-sm text-neutral-600">
              <li className="flex gap-2">
                <span className="text-neutral-300">{"•"}</span>
                {isAr
                  ? "البحث الأكاديمي حول الاقتصاد والصحة والسكان في فلسطين"
                  : "Academic research on Palestinian economy, health, and demographics"}
              </li>
              <li className="flex gap-2">
                <span className="text-neutral-300">{"•"}</span>
                {isAr
                  ? "الصحافة القائمة على البيانات مع إسناد صحيح للمصادر"
                  : "Data-driven journalism with proper source attribution"}
              </li>
              <li className="flex gap-2">
                <span className="text-neutral-300">{"•"}</span>
                {isAr
                  ? "تصورات البيانات والقصص التفاعلية"
                  : "Data visualization and interactive stories"}
              </li>
              <li className="flex gap-2">
                <span className="text-neutral-300">{"•"}</span>
                {isAr
                  ? "تحليل السياسات والتخطيط الإنساني"
                  : "Policy analysis and humanitarian planning"}
              </li>
              <li className="flex gap-2">
                <span className="text-neutral-300">{"•"}</span>
                {isAr
                  ? "بناء تطبيقات تحتاج إلى بيانات إحصائية فلسطينية"
                  : "Applications that need Palestinian statistical data"}
              </li>
            </ul>
          </section>

          {/* Section F: Open source */}
          <section className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "مفتوح المصدر" : "Open source"}
            </h2>
            <p className="mt-3 text-sm text-neutral-600">
              {isAr
                ? "Data Palestine مفتوح المصدر بالكامل بموجب رخصة MIT. الكود المصدري وجميع خطوط أنابيب البيانات متاحة على GitHub. نرحب بالمساهمات."
                : "Data Palestine is fully open source under the MIT license. Source code and all data pipelines are on GitHub. Contributions welcome."}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <a
                href="https://github.com/datapalestine/data-palestine"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-700"
              >
                GitHub
              </a>
              <a
                href="https://github.com/datapalestine/data-palestine/blob/main/docs/CONTRIBUTING.md"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                {isAr ? "دليل المساهمة" : "Contributing guide"}
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function CodeBlock({ label, code }: { label: string; code: string }) {
  return (
    <div dir="ltr" className="rounded-lg border border-neutral-200 bg-neutral-900 text-left">
      <div className="border-b border-neutral-700 px-4 py-2">
        <span className="text-[11px] font-medium text-neutral-400">
          {label}
        </span>
      </div>
      <pre className="overflow-x-auto px-4 py-3 text-[12px] leading-relaxed text-neutral-100">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex gap-3 text-sm">
      <span className="w-32 shrink-0 font-medium text-neutral-500">
        {label}
      </span>
      <span
        dir={mono ? "ltr" : undefined}
        className={`text-neutral-700 ${mono ? "font-mono text-[13px] text-left" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}
