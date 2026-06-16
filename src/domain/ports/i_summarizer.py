from abc import ABC, abstractmethod


class ISummarizer(ABC):
    @abstractmethod
    def summarize(
        self, text: str, max_length: int = 60, min_length: int = 15
    ) -> str:
        ...
