"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";

const STORAGE_KEY = "explorer_disclaimer_dismissed";

export function ExplorerDisclaimer() {
  const t = useTranslations("explore.disclaimer");
  const [dismissed, setDismissed] = useState(true); // default true to avoid flash on SSR

  useEffect(() => {
    // Check sessionStorage on client mount — if not dismissed, show the banner
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (!stored) setDismissed(false);
  }, []);

  if (dismissed) return null;

  const handleDismiss = () => {
    sessionStorage.setItem(STORAGE_KEY, "1");
    setDismissed(true);
  };

  return (
    <div
      className="flex items-start justify-between gap-4 rounded-lg border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 px-5 py-4 shadow-sm"
      role="status"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-amber-100">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#D97706" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-amber-900">
            {t("title")}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-amber-800/80">
            {t("body")}
          </p>
        </div>
      </div>
      <button
        onClick={handleDismiss}
        aria-label={t("dismiss")}
        className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-amber-400 transition-colors hover:bg-amber-100 hover:text-amber-600"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
