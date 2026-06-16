from __future__ import annotations

import os

import pytest

os.environ.setdefault("NEWS_API_KEY", "test-key-for-tests")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")

from unittest.mock import MagicMock, patch

from src.api.app import create_app
from src.application.dtos.news_dto import ArticleDTO, NewsListDTO
from datetime import datetime, timezone


@pytest.fixture
def app():
    """Flask test application — uses mocked use cases."""
    import src.api.dependencies as deps
    # Reset singletons so each test starts with a clean in-memory adapter
    deps._article_repo = None
    deps._summary_repo = None
    deps._cache = None

    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _make_news_list_dto(n: int = 2) -> NewsListDTO:
    articles = [
        ArticleDTO(
            id=f"article-{i}",
            title=f"Headline {i}",
            url=f"https://example.com/news-{i}",
            published_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
            image_url=f"https://example.com/img-{i}.jpg",
            source="Test",
            summary_text=f"Summary {i}",
            summary_status="completed",
        )
        for i in range(n)
    ]
    return NewsListDTO(articles=articles, page=1, page_size=20, total=n)


# ── Security Headers ─────────────────────────────────────────

class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_csp_header_present(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/")
        assert "Content-Security-Policy" in resp.headers

    def test_hsts_header_present(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/")
        assert "Strict-Transport-Security" in resp.headers

    def test_server_header_removed(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/")
        assert "Server" not in resp.headers


# ── Input Validation ─────────────────────────────────────────

class TestInputValidation:
    def test_xss_in_keyword_returns_400(self, client):
        resp = client.get("/api/news?keyword=<script>alert(1)</script>")
        assert resp.status_code == 400

    def test_sql_injection_chars_return_400(self, client):
        resp = client.get("/api/news?keyword='; DROP TABLE articles;--")
        assert resp.status_code == 400

    def test_keyword_too_long_returns_400(self, client):
        resp = client.get(f"/api/news?keyword={'a' * 101}")
        assert resp.status_code == 400

    def test_valid_keyword_passes(self, client):
        with patch("src.api.routes.news_routes.get_search_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/api/news?keyword=climate")
        assert resp.status_code == 200

    def test_page_above_100_returns_400(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/api/news?page=101")
        assert resp.status_code == 400


# ── News Routes ───────────────────────────────────────────────

class TestNewsRoutes:
    def test_homepage_returns_200(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/")
        assert resp.status_code == 200

    def test_api_news_returns_json(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/api/news")
        assert resp.content_type == "application/json"
        data = resp.get_json()
        assert "articles" in data
        assert "pagination" in data

    def test_api_news_article_fields(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto(1)
            resp = client.get("/api/news")
        article = resp.get_json()["articles"][0]
        assert "id" in article
        assert "title" in article
        assert "url" in article
        assert "summary" in article

    def test_load_more_returns_success_json(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/load_more?page=2")
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["news"], list)

    def test_post_search_returns_200(self, client):
        with patch("src.api.routes.news_routes.get_search_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.post("/", data={"keyword": "technology"})
        assert resp.status_code == 200


# ── Health Route ──────────────────────────────────────────────

class TestHealthRoute:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_has_status(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["status"] in ("healthy", "degraded")
        assert "checks" in data


# ── Rate Limiter ──────────────────────────────────────────────

class TestRateLimiter:
    def test_health_exempt_from_rate_limit(self, client):
        # Health should always respond regardless of rate limit state
        for _ in range(5):
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_rate_limit_triggers_429(self, app):
        """Set very low limit and hammer the endpoint."""
        from src.api.middleware.rate_limiter import _limiter, RateLimiter
        import src.api.middleware.rate_limiter as rl_module

        original = rl_module._limiter
        rl_module._limiter = RateLimiter(max_requests=3, window_seconds=60)

        test_client = app.test_client()
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            responses = [test_client.get("/api/news") for _ in range(5)]

        rl_module._limiter = original
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes

    def test_rate_limit_header_present(self, client):
        with patch("src.api.routes.news_routes.get_top_news_use_case") as mock:
            mock.return_value.execute.return_value = _make_news_list_dto()
            resp = client.get("/api/news")
        assert "X-RateLimit-Limit" in resp.headers
