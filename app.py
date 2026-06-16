# ⚠️  LEGACY FILE — kept for reference only.
# The application has been refactored to a production-ready architecture.
# Start the app with:  python run.py
#
# This file is NO LONGER the entry point.
# DO NOT use API_KEY here — load it from .env via src/config/settings.py

# REMOVED: API_KEY = "..." — hardcoded secrets are a security risk (OWASP A02)


app = Flask(__name__)
summarizer = TextSummarizer()

news_cache = {}
CACHE_DURATION = 3600  # 1 saat cache

def fetch_news(keyword=None, page=1, page_size=30):
    if keyword:
        url = (
            f"https://newsapi.org/v2/everything"
            f"?q={keyword}&apiKey={API_KEY}&language=en"
            f"&pageSize={page_size}&page={page}&sortBy=publishedAt"
        )
    else:
        url = (
            f"https://newsapi.org/v2/top-headlines"
            f"?language=en&apiKey={API_KEY}&pageSize={page_size}&page={page}"
        )
    response = requests.get(url, timeout=5)
    if response.status_code != 200:
        raise Exception("API request failed")
    data = response.json()
    if "articles" not in data or not data["articles"]:
        raise Exception("No news found")

    news_list = []
    for article in data["articles"]:
        image_url = article.get("urlToImage")
        if not image_url:
            continue
        content = article.get("content") or article.get("description") or ""
        news_list.append({
            "title": article.get("title", ""),
            "text": content,
            "url": article.get("url", ""),
            "date": article.get("publishedAt", ""),
            "image_url": image_url
        })

    total_results = data.get("totalResults", len(news_list))
    return news_list, total_results

def fetch_news_cached(keyword=None, page=1, page_size=30):
    key = f"{keyword}_{page}_{page_size}"
    now = time.time()
    if key in news_cache and now - news_cache[key]['time'] < CACHE_DURATION:
        return news_cache[key]['data']
    data = fetch_news(keyword, page, page_size)
    news_cache[key] = {'data': data, 'time': now}
    return data

@app.route("/", methods=["GET", "POST"])
def index():
    news_summaries = []
    error = None
    keyword = ""
    page = 1

    try:
        if request.method == "POST":
            keyword = request.form.get("keyword", "").strip()
        else:
            keyword = request.args.get("keyword", "").strip()

        page_size = 20  # İlk sayfa 20 haber

        news_list, total_results = fetch_news_cached(keyword, page, page_size=page_size)

        for news in news_list:
            text = news["text"]
            if not text or len(text.split()) < 10:
                summary = "No sufficient content for summarization."
            else:
                summary = summarizer.summarize(text, max_length=60, min_length=15)
            news_summaries.append({
                "title": news["title"],
                "url": news["url"],
                "summary": summary,
                "image_url": news["image_url"]
            })

        total_pages = (total_results + page_size - 1) // page_size

    except Exception as e:
        error = str(e)
        total_pages = 1

    return render_template("index.html",
                           news_summaries=news_summaries,
                           error=error,
                           keyword=keyword,
                           page=page,
                           total_pages=total_pages)

@app.route("/load_more", methods=["GET"])
def load_more():
    """
    AJAX ile istenen sayfa için haberleri ve toplam haber sayısını döndürür.
    Frontend her yüklemede totalResults ile toplam sayfa sayısını güncellemelidir!
    """
    keyword = request.args.get("keyword", "").strip()
    page = int(request.args.get("page", "2"))

    try:
        page_size = 10  # Sonraki sayfalarda 10 haber
        news_list, total_results = fetch_news_cached(keyword, page, page_size=page_size)

        news_data = []
        for news in news_list:
            text = news["text"]
            if not text or len(text.split()) < 10:
                summary = "No sufficient content for summarization."
            else:
                summary = summarizer.summarize(text, max_length=60, min_length=15)
            news_data.append({
                "title": news["title"],
                "url": news["url"],
                "summary": summary,
                "image_url": news["image_url"]
            })

        return jsonify({
            "success": True,
            "news": news_data,
            "page": page,
            "totalResults": total_results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
