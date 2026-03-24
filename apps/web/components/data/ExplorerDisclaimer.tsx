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
      style={{
        background: "#FFFDE7",
        border: "1px solid #F9A825",
        borderRadius: "6px",
        padding: "12px 16px",
      }}
      className="flex items-start justify-between gap-4"
      role="status"
    >
      <div>
        <p style={{ fontSize: "14px", fontWeight: 600, color: "#212121" }}>
          {t("title")}
        </p>
        <p style={{ fontSize: "14px", fontWeight: 400, color: "#212121", marginTop: "4px" }}>
          {t("body")}
        </p>
      </div>
      <button
        onClick={handleDismiss}
        aria-label={t("dismiss")}
        style={{
          fontSize: "20px",
          color: "#757575",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: "12px",
          margin: "-12px -12px -12px 0",
          lineHeight: 1,
          flexShrink: 0,
        }}
      >
        ×
      </button>
    </div>
  );
}
