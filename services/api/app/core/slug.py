import re
from urllib.parse import unquote


_non_slug_characters = re.compile(r"[^a-z0-9]+")
_repeated_hyphens = re.compile(r"-+")


def normalize_slug(value: str | None, *, fallback: str | None = None) -> str | None:
    source = value if value and value.strip() else fallback
    if source is None:
        return None

    decoded = unquote(source).strip().lower()
    collapsed = _non_slug_characters.sub("-", decoded)
    normalized = _repeated_hyphens.sub("-", collapsed).strip("-")
    return normalized or None
