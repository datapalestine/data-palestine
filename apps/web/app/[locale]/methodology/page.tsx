import { getTranslations } from "next-intl/server";

const SOURCES = [
  {
    name: "PCBS",
    name_ar: "الجهاز المركزي للإحصاء الفلسطيني",
    url: "https://www.pcbs.gov.ps",
    data_en: "Demographics, economy, labor, health, education, construction indices, price indices",
    data_ar: "السكان، الاقتصاد، العمل، الصحة، التعليم، مؤشرات البناء، مؤشرات الأسعار",
    method_en: "CSV and Excel downloads from statistical tables",
    method_ar: "تحميل ملفات CSV وExcel من الجداول الإحصائية",
    frequency_en: "Monthly to annual",
    frequency_ar: "شهري إلى سنوي",
    status: "active" as const,
  },
  {
    name: "World Bank",
    name_ar: "البنك الدولي",
    url: "https://data.worldbank.org",
    data_en: "GDP, population, unemployment, life expectancy",
    data_ar: "الناتج المحلي الإجمالي، السكان، البطالة، متوسط العمر المتوقع",
    method_en: "REST API (JSON)",
    method_ar: "واجهة برمجة REST (JSON)",
    frequency_en: "Annual",
    frequency_ar: "سنوي",
    status: "active" as const,
  },
  {
    name: "Tech for Palestine",
    name_ar: "تقنية من أجل فلسطين",
    url: "https://data.techforpalestine.org",
    data_en: "Gaza and West Bank casualties, infrastructure damage",
    data_ar: "ضحايا غزة والضفة الغربية، أضرار البنية التحتية",
    method_en: "JSON API (GitHub-hosted datasets)",
    method_ar: "واجهة JSON (مجموعات بيانات مستضافة على GitHub)",
    frequency_en: "Daily",
    frequency_ar: "يومي",
    status: "active" as const,
  },
  {
    name: "OCHA / HDX",
    name_ar: "مكتب تنسيق الشؤون الإنسانية",
    url: "https://data.humdata.org",
    data_en: "Humanitarian needs, displacement, food insecurity",
    data_ar: "الاحتياجات الإنسانية، النزوح، انعدام الأمن الغذائي",
    method_en: "HDX API and CSV downloads",
    method_ar: "واجهة HDX وتحميل CSV",
    frequency_en: "Varies",
    frequency_ar: "متفاوت",
    status: "planned" as const,
  },
  {
    name: "B'Tselem",
    name_ar: "بتسيلم",
    url: "https://www.btselem.org",
    data_en: "Human rights documentation, fatalities data",
    data_ar: "توثيق حقوق الإنسان، بيانات الوفيات",
    method_en: "Web scraping (JavaScript application)",
    method_ar: "استخلاص من الويب (تطبيق JavaScript)",
    frequency_en: "Ongoing",
    frequency_ar: "مستمر",
    status: "planned" as const,
  },
];

const PIPELINE_STEPS = [
  {
    num: "1",
    title_en: "Collection",
    title_ar: "الجمع",
    desc_en:
      "We download raw data files (CSV, Excel) from official sources, or fetch from APIs. All original files are permanently archived and never modified.",
    desc_ar:
      "نحمّل ملفات البيانات الخام (CSV، Excel) من المصادر الرسمية، أو نجلبها من واجهات البرمجة. جميع الملفات الأصلية تُؤرشف بشكل دائم ولا تُعدّل.",
  },
  {
    num: "2",
    title_en: "Extraction",
    title_ar: "الاستخلاص",
    desc_en:
      "We parse the raw files to extract structured data: values, dates, geographic breakdowns, and indicator names. For PCBS data, this includes handling multi-row headers, Arabic month names, and multi-sheet Excel workbooks.",
    desc_ar:
      "نحلل الملفات الخام لاستخلاص بيانات منظمة: القيم، التواريخ، التوزيع الجغرافي، وأسماء المؤشرات. بالنسبة لبيانات الجهاز المركزي، يشمل ذلك التعامل مع العناوين متعددة الصفوف، وأسماء الأشهر بالعربية، ومصنفات Excel متعددة الأوراق.",
  },
  {
    num: "3",
    title_en: "Cleaning",
    title_ar: "التنظيف",
    desc_en:
      "We standardize names, normalize geography codes to PCBS/OCHA standards (PS for Palestine, PS-WBK for West Bank, PS-GZA for Gaza, and individual governorate codes), detect and separate percent-change indicators, and deduplicate overlapping time series.",
    desc_ar:
      "نوحّد الأسماء، ونعياري رموز الجغرافيا وفق معايير الجهاز المركزي ومكتب التنسيق (PS لفلسطين، PS-WBK للضفة الغربية، PS-GZA لقطاع غزة، ورموز المحافظات)، ونكشف مؤشرات نسبة التغير ونفصلها، ونزيل التكرار في السلاسل الزمنية المتداخلة.",
  },
  {
    num: "4",
    title_en: "Validation",
    title_ar: "التحقق",
    desc_en:
      "Every observation is checked for range plausibility, completeness, and consistency. We run automated and manual accuracy checks comparing our database against original sources.",
    desc_ar:
      "يُتحقق من كل ملاحظة من حيث معقولية النطاق والاكتمال والاتساق. نجري فحوصات دقة تلقائية نقارن فيها قاعدة بياناتنا بالمصادر الأصلية.",
  },
  {
    num: "5",
    title_en: "Publication",
    title_ar: "النشر",
    desc_en:
      "Clean data is served through our REST API and displayed on the website. Every observation links back to its source document.",
    desc_ar:
      "تُقدّم البيانات النظيفة عبر واجهة REST الخاصة بنا وتُعرض على الموقع. كل ملاحظة ترتبط بوثيقة المصدر الأصلية.",
  },
];

export default async function MethodologyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("methodology");
  const isAr = locale === "ar";

  return (
    <div className="bg-[#FAFAFA]">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
        <h1 className="text-2xl font-bold text-neutral-900 sm:text-3xl">
          {t("title")}
        </h1>
        <p className="mt-2 text-sm text-neutral-500">{t("subtitle")}</p>

        <div className="mt-10 space-y-12">
          {/* Section A: Our approach */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {isAr ? "منهجنا" : "Our approach"}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {isAr
                ? "Data Palestine تجمع البيانات من مصادر فلسطينية ودولية رسمية. نحن لا ننتج بيانات أصلية، بل نجمع الإحصائيات الموجودة من مؤسسات موثوقة ونتنظفها ونوحدها ونقدمها بشكل منظم. كل نقطة بيانات يمكن تتبعها إلى مصدرها الأصلي."
                : "Data Palestine aggregates data from official Palestinian and international sources. We do not generate original data. We collect, clean, standardize, and serve existing statistics from trusted institutions. Every data point traces back to its original source."}
            </p>
          </section>

          {/* Section B: Data sources */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("sources")}
            </h2>
            <div className="mt-4 space-y-3">
              {SOURCES.map((src) => (
                <div
                  key={src.name}
                  className="rounded-lg border border-neutral-200 bg-white p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-semibold text-[#1B5E20] hover:underline"
                        >
                          {isAr ? src.name_ar : src.name}
                        </a>
                        {src.status === "planned" && (
                          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                            {isAr ? "قريباً" : "Coming soon"}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-[13px] text-neutral-600">
                        {isAr ? src.data_ar : src.data_en}
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-neutral-400">
                    <span>
                      {isAr ? "الطريقة" : "Method"}:{" "}
                      {isAr ? src.method_ar : src.method_en}
                    </span>
                    <span>
                      {isAr ? "التحديث" : "Updates"}:{" "}
                      {isAr ? src.frequency_ar : src.frequency_en}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section C: Data processing pipeline */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("process")}
            </h2>
            <div className="mt-4 space-y-4">
              {PIPELINE_STEPS.map((step) => (
                <div key={step.num} className="flex gap-4">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#1B5E20] text-xs font-bold text-white">
                    {step.num}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      {isAr ? step.title_ar : step.title_en}
                    </h3>
                    <p className="mt-1 text-[13px] leading-relaxed text-neutral-600">
                      {isAr ? step.desc_ar : step.desc_en}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section D: Accuracy and limitations */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("limitations")}
            </h2>
            <p className="mt-3 text-sm text-neutral-600">
              {isAr
                ? "نحرص على الدقة من خلال الفحوصات الآلية والمراجعة اليدوية. لكن حجم البيانات كبير وفريقنا صغير، لذا نعترف بالقيود التالية:"
                : "We work to ensure accuracy through automated checks and manual review. But the volume of data is large and our team is small, so we acknowledge the following limitations:"}
            </p>
            <ul className="mt-3 list-disc space-y-2 ps-5 text-[13px] leading-relaxed text-neutral-600 marker:text-neutral-300">
              <li>
                {isAr
                  ? "البيانات مستخلصة برمجياً وقد تحتوي على أخطاء في الاستخراج. نراجع يدوياً ما نستطيع لكن لا يمكننا التحقق من كل قيمة على حدة."
                  : "Data is extracted programmatically and may contain extraction errors. We manually review what we can, but we cannot verify every individual value."}
              </li>
              <li>
                {isAr
                  ? "بعض جداول الجهاز المركزي للإحصاء تحتوي على عناوين معقدة متعددة الصفوف يصعب تحليلها. نواصل تحسين المحللات."
                  : "Some PCBS tables have multi-row headers that are difficult to parse. We continue to improve our parsers."}
              </li>
              <li>
                {isAr
                  ? "ليست جميع بيانات الجهاز المركزي متوفرة بتنسيق منظم. بعضها موجود فقط في ملفات PDF لم نعالجها بعد. لدينا أكثر من 6,700 ملف Excel أرشيفي بانتظار المعالجة."
                  : "Not all PCBS data is available in structured format. Some exists only in PDFs we have not yet processed. We have over 6,700 archived Excel files waiting to be parsed."}
              </li>
              <li>
                {isAr
                  ? "بعض المؤشرات بها فجوات في السلاسل الزمنية حيث لا تتوفر بيانات المصدر."
                  : "Some indicators have gaps in time series where source data is unavailable."}
              </li>
            </ul>
            <p className="mt-4 text-[13px] text-neutral-600">
              {isAr
                ? "إذا وجدت خطأ في البيانات، أخبرنا عبر"
                : "If you spot an error, let us know via"}{" "}
              <a
                href="https://github.com/datapalestine/data-palestine/issues/new?template=data-correction.md"
                className="text-[#1B5E20] underline hover:no-underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
              {" "}
              {isAr ? "أو أرسل بريداً إلكترونياً إلى" : "or email us at"}{" "}
              <a
                href="mailto:info@datapalestine.org"
                className="text-[#1B5E20] underline hover:no-underline"
              >
                info@datapalestine.org
              </a>
            </p>
          </section>

          {/* Section E: Verification and help needed */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("quality")}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {isAr
                ? "نشغّل نظام تحقق آلي يقارن القيم المخزنة بالمصادر الأصلية: واجهة البنك الدولي، ملفات CSV الخام، وقيم خلايا Excel. حالياً جميع فحوصات الدقة ناجحة (21 من 21). سكربت التحقق متاح على GitHub للشفافية."
                : "We run automated verification that spot-checks stored values against original sources: the World Bank API, raw CSV files, and Excel cell values. Currently all accuracy checks are passing (21 of 21). The verification script is available on GitHub for transparency."}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {isAr
                ? "نحتاج مساعدتكم. هذا المشروع يُديره فريق صغير، والبيانات الفلسطينية المتاحة أكبر بكثير مما يمكننا معالجته وحدنا. إذا كنت باحثاً أو مطوراً أو متخصصاً في البيانات، يمكنك المساهمة بمراجعة البيانات، وإضافة مصادر جديدة، وتحسين المحللات، والمساعدة في التحقق من الأرقام مقابل المصادر الأصلية."
                : "We need your help. This project is run by a small team, and the volume of available Palestinian data is far more than we can process alone. If you are a researcher, developer, or data specialist, you can contribute by reviewing data, adding new sources, improving parsers, and helping verify figures against original sources."}
            </p>
            <div className="mt-4">
              <a
                href="https://github.com/datapalestine/data-palestine/blob/main/docs/CONTRIBUTING.md"
                className="inline-flex items-center gap-2 rounded-lg bg-[#1B5E20] px-4 py-2 text-sm font-medium text-white hover:bg-[#0D3B10]"
                target="_blank"
                rel="noopener noreferrer"
              >
                {isAr ? "كيف تساهم" : "How to contribute"}
              </a>
            </div>
          </section>

          {/* Section F: Open data principles */}
          <section>
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("transparency")}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              {isAr
                ? "نتبع مبادئ FAIR: قابلة للعثور، قابلة للوصول، قابلة للتشغيل المتبادل، قابلة لإعادة الاستخدام. جميع البيانات متاحة عبر واجهة البرمجة بدون تسجيل. الكود مفتوح المصدر بموجب رخصة MIT. البيانات الوصفية متاحة بموجب CC-BY 4.0."
                : "We follow the FAIR principles: Findable, Accessible, Interoperable, Reusable. All data is available through the API with no registration required. Code is open source under the MIT license. Data metadata is CC-BY 4.0."}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
