from __future__ import annotations

import re
from dataclasses import dataclass

_VALID_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-]{1,100}$")


@dataclass(frozen=True)
class Keyword:
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise ValueError("Keyword cannot be empty")
        if len(stripped) > 100:
            raise ValueError("Keyword too long (max 100 characters)")
        if not _VALID_PATTERN.match(stripped):
            raise ValueError(
                "Keyword contains invalid characters. "
                "Only letters, numbers, spaces and hyphens are allowed."
            )

    def normalized(self) -> str:
        return self.value.strip().lower()

    def __str__(self) -> str:
        return self.value
