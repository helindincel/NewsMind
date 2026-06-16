from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class ICache(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...
