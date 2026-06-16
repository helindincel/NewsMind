from __future__ import annotations

from datetime import UTC, datetime

import requests
import structlog

from src.domain.entities.article import Article
from src.domain.exceptions import NewsProviderException
from src.domain.ports.i_news_provider import INewsProvider

log = structlog.get_logger(__name__)


class NewsAPIAdapter(INewsProvider):
    def __init__(self, api_key: str, base_url: str, timeout: int = 10) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "HUBB-NewsApp/1.0"})

    def fetch_top_headlines(self, page: int = 1, page_size: int = 20) -> tuple[list[Article], int]:
        params = {
            "language": "en",
            "apiKey": self._api_key,
            "pageSize": page_size,
            "page": page,
        }
        return self._fetch(f"{self._base_url}/top-headlines", params)

    def fetch_by_keyword(
        self, keyword: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Article], int]:
        params = {
            "q": keyword,
            "apiKey": self._api_key,
            "language": "en",
            "pageSize": page_size,
            "page": page,
            "sortBy": "publishedAt",
        }
        return self._fetch(f"{self._base_url}/everything", params)

    # ── private ──────────────────────────────────────────────

    def _fetch(self, url: str, params: dict) -> tuple[list[Article], int]:
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise NewsProviderException("NewsAPI request timed out") from exc
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise NewsProviderException(f"NewsAPI HTTP error: {status_code}") from exc
        except requests.exceptions.RequestException as exc:
            raise NewsProviderException(f"NewsAPI request failed: {exc}") from exc

        data = response.json()
        if data.get("status") != "ok":
            raise NewsProviderException(f"NewsAPI error: {data.get('message', 'Unknown error')}")

        articles = self._parse_articles(data.get("articles", []))
        total = data.get("totalResults", len(articles))
        log.info("newsapi.fetched", article_count=len(articles), total=total)
        return articles, total

    def _parse_articles(self, raw_articles: list) -> list[Article]:
        articles: list[Article] = []
        for raw in raw_articles:
            image_url = raw.get("urlToImage")
            if not image_url:
                continue  # skip articles without images

            content = raw.get("content") or raw.get("description") or ""
            published_at_str = raw.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                published_at = datetime.now(UTC)

            articles.append(
                Article(
                    title=raw.get("title") or "",
                    url=raw.get("url") or "",
                    content=content,
                    image_url=image_url,
                    source=(raw.get("source") or {}).get("name"),
                    published_at=published_at,
                )
            )
        return articles
