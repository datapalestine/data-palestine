"""API route handlers."""

import re

# Matches at least one Arabic Unicode character
_HAS_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def localized(row, field: str, lang: str) -> str:
    """Return localized field with fallback to English when translation is missing.

    Falls back to English when:
    - The localized value is NULL or empty
    - The localized value is not actually in the target language
      (e.g. name_ar contains English text from unclean PCBS imports)
    """
    en_val = row.get(f"{field}_en") or ""
    if lang == "en":
        return en_val
    val = row.get(f"{field}_{lang}")
    if not val:
        return en_val
    # For Arabic: if the "Arabic" value has no Arabic characters, it's a fake
    # translation (raw English title stored in the Arabic column). Use English.
    if lang == "ar" and not _HAS_ARABIC.search(val):
        return en_val
    return val
