from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.domain.entities.article import Article
from src.domain.repositories.i_article_repository import IArticleRepository


class InMemoryArticleRepository(IArticleRepository):
    def __init__(self) -> None:
        self._articles: Dict[str, Article] = {}
        self._url_index: Dict[str, str] = {}  # url -> id

    def save(self, article: Article) -> Article:
        # Deduplicate by URL
        if article.url in self._url_index:
            return self._articles[self._url_index[article.url]]
        self._articles[article.id] = article
        self._url_index[article.url] = article.id
        return article

    def find_by_id(self, article_id: str) -> Optional[Article]:
        return self._articles.get(article_id)

    def find_by_keyword(
        self, keyword: str, page: int, page_size: int
    ) -> Tuple[List[Article], int]:
        kw = keyword.lower()
        filtered = [
            a
            for a in self._articles.values()
            if (a.keyword and kw in a.keyword.lower())
            or kw in a.title.lower()
        ]
        filtered.sort(key=lambda a: a.published_at, reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        return filtered[start : start + page_size], total

    def find_top_headlines(
        self, page: int, page_size: int
    ) -> Tuple[List[Article], int]:
        all_articles = sorted(
            self._articles.values(), key=lambda a: a.published_at, reverse=True
        )
        total = len(all_articles)
        start = (page - 1) * page_size
        return all_articles[start : start + page_size], total
