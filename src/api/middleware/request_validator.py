from __future__ import annotations

import re

from flask import abort

# Keyword: alphanumeric + space + hyphen, max 100 chars
_KEYWORD_RE = re.compile(r"^[a-zA-Z0-9\s\-]{1,100}$")


def validate_keyword(keyword: str) -> str:
    """
    Sanitize and validate a news search keyword.
    Raises 400 if the keyword contains invalid characters or is too long.
    Returns the stripped keyword.
    """
    stripped = keyword.strip()
    if not stripped:
        return ""
    if len(stripped) > 100:
        abort(400, description="Keyword too long (max 100 characters)")
    if not _KEYWORD_RE.match(stripped):
        abort(
            400,
            description=(
                "Keyword contains invalid characters. "
                "Only letters, numbers, spaces and hyphens are allowed."
            ),
        )
    return stripped


def validate_page(raw: str, default: int = 1) -> int:
    """Return a validated page number in [1, 100]."""
    try:
        page = int(raw)
    except (TypeError, ValueError):
        return default
    if page < 1:
        return 1
    if page > 100:
        abort(400, description="Page number must be between 1 and 100")
    return page


def validate_page_size(raw: str, default: int = 20, maximum: int = 50) -> int:
    """Return a validated page size in [1, maximum]."""
    try:
        size = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(size, maximum))
