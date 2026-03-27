"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

export function Footer() {
  const t = useTranslations("footer");
  const tNav = useTranslations("nav");
  const locale = useLocale();

  return (
    <footer className="border-t border-neutral-800 bg-[#212121] text-neutral-300">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-3">
          {/* About */}
          <div>
            <h3 className="text-sm font-semibold text-white">Data Palestine</h3>
            <p className="mt-3 text-[13px] leading-relaxed text-neutral-400">
              {t("tagline")}
            </p>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="text-sm font-semibold text-white">
              {t("dataAccess")}
            </h3>
            <ul className="mt-3 space-y-2 text-[13px]">
              <li>
                <Link
                  href={`/${locale}/datasets`}
                  className="text-neutral-400 hover:text-white"
                >
                  {tNav("catalog")}
                </Link>
              </li>
              <li>
                <Link
                  href={`/${locale}/explore`}
                  className="text-neutral-400 hover:text-white"
                >
                  {tNav("explore")}
                </Link>
              </li>
              <li>
                <Link
                  href={`/${locale}/developers`}
                  className="text-neutral-400 hover:text-white"
                >
                  {tNav("developers")}
                </Link>
              </li>
              <li>
                <Link
                  href={`/${locale}/methodology`}
                  className="text-neutral-400 hover:text-white"
                >
                  {tNav("methodology")}
                </Link>
              </li>
              <li>
                <Link
                  href={`/${locale}/contribute/curate`}
                  className="text-neutral-400 hover:text-white"
                >
                  {locale === "ar" ? "ساعد في تنظيف البيانات" : "Help Clean Data"}
                </Link>
              </li>
            </ul>
          </div>

          {/* Organization */}
          <div>
            <h3 className="text-sm font-semibold text-white">
              {t("organization")}
            </h3>
            <ul className="mt-3 space-y-2 text-[13px]">
              <li>
                <Link
                  href={`/${locale}/about`}
                  className="text-neutral-400 hover:text-white"
                >
                  {tNav("about")}
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/datapalestine/data-palestine"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-neutral-400 hover:text-white"
                >
                  {locale === "ar" ? "ساهم على GitHub" : "Contribute on GitHub"}
                </a>
              </li>
              <li>
                <span className="text-neutral-400">{t("builtWith")}</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-neutral-700 pt-6 text-[12px] text-neutral-500">
          {t("copyright", {
            year: new Date().getFullYear(),
            license: "CC-BY-4.0",
          })}
        </div>
      </div>
    </footer>
  );
}
