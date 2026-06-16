from __future__ import annotations

import structlog
from flask import Blueprint, jsonify, render_template, request

from src.api.dependencies import get_search_news_use_case, get_top_news_use_case
from src.api.middleware.request_validator import (
    validate_keyword,
    validate_page,
    validate_page_size,
)
from src.domain.exceptions import InvalidKeywordException, NewsProviderException

log = structlog.get_logger(__name__)

news_bp = Blueprint("news", __name__)


@news_bp.route("/", methods=["GET", "POST"])
def index():
    """Main page: render top headlines or keyword search results."""
    keyword = ""
    error = None

    try:
        if request.method == "POST":
            raw_keyword = request.form.get("keyword", "")
        else:
            raw_keyword = request.args.get("keyword", "")

        keyword = validate_keyword(raw_keyword)
        page = validate_page(request.args.get("page", "1"))
        page_size = 20

        if keyword:
            result = get_search_news_use_case().execute(keyword, page, page_size)
        else:
            result = get_top_news_use_case().execute(page, page_size)

        # Convert DTOs to the format the existing template expects
        news_summaries = [
            {
                "title": a.title,
                "url": a.url,
                "image_url": a.image_url,
                "summary": a.summary_text or "No sufficient content for summarization.",
            }
            for a in result.articles
        ]

        return render_template(
            "index.html",
            news_summaries=news_summaries,
            error=error,
            keyword=keyword,
            page=result.page,
            total_pages=result.total_pages,
        )

    except InvalidKeywordException as exc:
        error = str(exc)
    except NewsProviderException as exc:
        log.error("news.provider_error", error=str(exc))
        error = "Could not fetch news at this time. Please try again later."
    except Exception as exc:
        log.error("news.unexpected_error", error=str(exc))
        error = "An unexpected error occurred. Please try again later."

    return render_template(
        "index.html",
        news_summaries=[],
        error=error,
        keyword=keyword,
        page=1,
        total_pages=1,
    )


@news_bp.route("/load_more", methods=["GET"])
def load_more():
    """AJAX endpoint: loads the next page of news cards."""
    raw_keyword = request.args.get("keyword", "")
    keyword = validate_keyword(raw_keyword)
    page = validate_page(request.args.get("page", "2"), default=2)
    page_size = 10

    try:
        if keyword:
            result = get_search_news_use_case().execute(keyword, page, page_size)
        else:
            result = get_top_news_use_case().execute(page, page_size)

        news_data = [
            {
                "title": a.title,
                "url": a.url,
                "image_url": a.image_url,
                "summary": a.summary_text or "No sufficient content for summarization.",
            }
            for a in result.articles
        ]

        return jsonify(
            {
                "success": True,
                "news": news_data,
                "page": result.page,
                "totalResults": result.total,
            }
        )

    except NewsProviderException as exc:
        log.error("load_more.provider_error", error=str(exc))
        return jsonify({"success": False, "error": "Could not fetch news."}), 502
    except Exception as exc:
        log.error("load_more.unexpected_error", error=str(exc))
        return jsonify({"success": False, "error": "Unexpected error."}), 500


@news_bp.route("/api/news", methods=["GET"])
def api_news():
    """JSON API: returns news list for programmatic consumers."""
    raw_keyword = request.args.get("keyword", "")
    keyword = validate_keyword(raw_keyword)
    page = validate_page(request.args.get("page", "1"))
    page_size = validate_page_size(request.args.get("page_size", "20"))

    try:
        if keyword:
            result = get_search_news_use_case().execute(keyword, page, page_size)
        else:
            result = get_top_news_use_case().execute(page, page_size)

        return jsonify(
            {
                "articles": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "url": a.url,
                        "image_url": a.image_url,
                        "source": a.source,
                        "published_at": a.published_at.isoformat(),
                        "summary": {
                            "text": a.summary_text,
                            "status": a.summary_status,
                        },
                    }
                    for a in result.articles
                ],
                "pagination": {
                    "page": result.page,
                    "page_size": result.page_size,
                    "total": result.total,
                    "total_pages": result.total_pages,
                },
            }
        )
    except NewsProviderException as exc:
        log.error("api.news.provider_error", error=str(exc))
        return jsonify({"error": "News provider unavailable"}), 502
    except Exception as exc:
        log.error("api.news.unexpected_error", error=str(exc))
        return jsonify({"error": "Internal server error"}), 500
