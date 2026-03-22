/**
 * Geography codes, category slugs, and other constants.
 */

export const GEOGRAPHY_CODES = {
  NATIONAL: "PS",
  WEST_BANK: "PS-WBK",
  GAZA: "PS-GZA",
} as const;

export const WEST_BANK_GOVERNORATES = [
  "PS-WBK-JEN",
  "PS-WBK-TBS",
  "PS-WBK-TKM",
  "PS-WBK-NBS",
  "PS-WBK-QQA",
  "PS-WBK-SLT",
  "PS-WBK-RBH",
  "PS-WBK-JRH",
  "PS-WBK-JEM",
  "PS-WBK-BTH",
  "PS-WBK-HBN",
] as const;

export const GAZA_GOVERNORATES = [
  "PS-GZA-NGZ",
  "PS-GZA-GZA",
  "PS-GZA-DEB",
  "PS-GZA-KYS",
  "PS-GZA-RFH",
] as const;

export const CATEGORY_SLUGS = [
  "population",
  "economy",
  "labor",
  "education",
  "health",
  "conflict",
  "displacement",
  "infrastructure",
  "environment",
  "governance",
] as const;

export const LOCALES = ["en", "ar"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "ar";
