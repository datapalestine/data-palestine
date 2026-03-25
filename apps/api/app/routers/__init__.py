"""API route handlers."""


def localized(row, field: str, lang: str) -> str:
    """Return localized field with fallback to English when translation is missing."""
    if lang != "en":
        val = row.get(f"{field}_{lang}")
        if val:
            return val
    return row.get(f"{field}_en") or ""
