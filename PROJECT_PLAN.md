# HUBB — Project Plan & Gap Analysis

> **Durum:** Aktif geliştirme | **Son güncelleme:** 2026-06-16  
> **Mimari:** Hexagonal (Ports & Adapters) | **Stack:** Python 3.11, Flask 3, Celery, Redis, PostgreSQL, HuggingFace Transformers

---

## 1. Proje Özeti

HUBB, gerçek zamanlı haber getirme ve NLP tabanlı özetleme sunan, production-ready bir haber özetleme platformudur. Monolitik Flask uygulamasından katmanlı, test edilebilir ve ölçeklenebilir bir mimariye yeniden tasarlanmıştır.

---

## 2. Tamamlanan Çalışmalar ✅

### Domain Katmanı
- [x] `Article` ve `Summary` entity'leri (`src/domain/entities/`)
- [x] `Keyword` value object (`src/domain/value_objects/keyword.py`)
- [x] Port interfaces: `INewsProvider`, `ISummarizer`, `ICache` (`src/domain/ports/`)
- [x] Repository interfaces: `IArticleRepository`, `ISummaryRepository` (`src/domain/repositories/`)
- [x] Domain exceptions: tüm hata tipleri tanımlı (`src/domain/exceptions.py`)

### Application Katmanı
- [x] `GetTopNewsUseCase` — ana sayfa haberleri (`src/application/use_cases/get_top_news.py`)
- [x] `SearchNewsUseCase` — keyword ile arama (`src/application/use_cases/search_news.py`)
- [x] DTO'lar: `NewsListDTO`, `ArticleDTO`, `SummaryDTO` (`src/application/dtos/`)

### Infrastructure Katmanı
- [x] `NewsAPIAdapter` — dış haber kaynağı adaptörü (`src/infrastructure/news/`)
- [x] `HuggingFaceAdapter` — NLP özetleme adaptörü (`src/infrastructure/ml/`)
- [x] `ModelRegistry` — singleton model yükleyici (`src/infrastructure/ml/model_loader.py`)
- [x] `InMemoryCacheAdapter` — geliştirme ortamı için cache (`src/infrastructure/cache/`)
- [x] `RedisCacheAdapter` — production cache (`src/infrastructure/cache/redis_adapter.py`)
- [x] `InMemoryArticleRepository` ve `InMemorySummaryRepository`
- [x] PostgreSQL repository'leri: `PostgresArticleRepository`, `PostgresSummaryRepository`
- [x] SQLAlchemy ORM modelleri + Alembic migration altyapısı

### API / Presentation Katmanı
- [x] Flask uygulama fabrikası (`src/api/app.py` → `create_app()`)
- [x] Dependency injection (`src/api/dependencies.py`)
- [x] Security headers middleware (`src/api/middleware/security_headers.py`)
- [x] Redis-backed rate limiter (`src/api/middleware/rate_limiter.py`)
- [x] Input validation (`src/api/middleware/request_validator.py`)
- [x] Prometheus metrics (`src/api/middleware/metrics.py`)
- [x] News routes + HTML template (`src/api/routes/news_routes.py`)
- [x] Health check endpoint (`src/api/routes/health_routes.py`)

### Workers
- [x] Celery uygulama konfigürasyonu (`src/workers/celery_app.py`)
- [x] Asenkron özetleme task'ı — retry + error handling ile (`src/workers/tasks/summarize_task.py`)

### Config & Observability
- [x] Pydantic-settings tabanlı konfigürasyon (`src/config/settings.py`)
- [x] Structured logging — structlog (`src/config/logging_config.py`)
- [x] OpenTelemetry tracing (`src/config/telemetry.py`)

### DevOps
- [x] Çok aşamalı Docker image'ları (`deployment/docker/`)
- [x] Docker Compose — API + Worker + PostgreSQL + Redis
- [x] GitHub Actions CI pipeline — lint, test, SAST, docker build (`.github/workflows/ci.yml`)
- [x] `.env.example` ortam değişkeni şablonu
- [x] `.gitignore` — gizli dosyalar korunuyor
- [x] `Makefile` — geliştirici komutları
- [x] `pyproject.toml` — Poetry bağımlılık yönetimi

### Testler
- [x] Unit testler: `Article`, `Keyword`, `Summary` entity'leri
- [x] Unit testler: `GetTopNewsUseCase`, `SearchNewsUseCase`
- [x] Unit testler: API güvenlik başlıkları, observability
- [x] Unit testler: `InMemoryCacheAdapter`
- [x] Unit testler: `NewsAPIAdapter`
- [x] Integration testler: cache ve database
- [x] Load testi altyapısı (k6) — `tests/load/load_test.js`

---

## 3. Eksikler & Açık Konular 🔴

### 3.1 Kod Eksikleri (Implementasyon Bekleniyor)

| # | Eksik | Öncelik | Açıklama |
|---|-------|---------|----------|
| 1 | `src/domain/ports/i_message_queue.py` | 🔴 HIGH | Tasarım dokümanında tanımlı ama implemente edilmemiş. Celery task'ları bu interface üzerinden çağrılmalı |
| 2 | `src/domain/value_objects/article_id.py` | 🟡 MEDIUM | Tasarım dokümanında belirtilen `ArticleId` value object eksik |
| 3 | `src/api/routes/summary_routes.py` | 🔴 HIGH | `POST /summaries` ve `GET /summaries/<id>` endpoint'leri eksik; Celery task tetiklemek için gerekli |
| 4 | `src/application/use_cases/request_summary.py` | 🔴 HIGH | Özet talep etme use case'i eksik |
| 5 | `src/application/use_cases/get_summary_status.py` | 🔴 HIGH | Özet durumu sorgulama use case'i eksik |
| 6 | `src/api/middleware/correlation_id.py` | 🟡 MEDIUM | Request tracing için correlation ID middleware eksik |
| 7 | `src/api/schemas/` | 🟡 MEDIUM | Marshmallow/Pydantic serialization schema'ları eksik; şu an dict comprehension kullanılıyor |
| 8 | Celery task'ta üretim adaptörleri | 🟡 MEDIUM | `summarize_task.py` içinde `USE_REDIS=true` durumunda Postgres/Redis injection tamamlanmamış |

### 3.2 Test Eksikleri

| # | Eksik Test | Öncelik |
|---|-----------|---------|
| 1 | `PostgresArticleRepository` ve `PostgresSummaryRepository` unit testleri | 🟠 HIGH |
| 2 | `HuggingFaceAdapter` unit testleri (mock model ile) | 🟠 HIGH |
| 3 | `RedisCacheAdapter` unit testleri (fakeredis ile) | 🟠 HIGH |
| 4 | `summarize_task` Celery task testleri | 🟡 MEDIUM |
| 5 | API endpoint entegrasyon testleri (`/`, `/health`) | 🟡 MEDIUM |
| 6 | `summary_routes` testleri (henüz route yok) | 🟡 MEDIUM |
| 7 | Test coverage %50 minimum — mevcut durum kontrol edilmeli | 🟠 HIGH |

### 3.3 Dokümantasyon Eksikleri

| # | Eksik | Öncelik |
|---|-------|---------|
| 1 | `CONTRIBUTING.md` — katkı kuralları ve geliştirme ortamı kurulumu | 🟡 MEDIUM |
| 2 | `CHANGELOG.md` — versiyon geçmişi | 🟢 LOW |
| 3 | API endpoint dokümantasyonu (OpenAPI/Swagger) | 🟡 MEDIUM |

### 3.4 Güvenlik & Production Hazırlığı

| # | Konu | Öncelik |
|---|------|---------|
| 1 | `SECRET_KEY` default değeri `"change-me-in-production"` — validation gerekli | 🔴 CRITICAL |
| 2 | `ALLOWED_ORIGINS=*` — production'da spesifik domain listesi olmalı | 🔴 HIGH |
| 3 | Docker Compose'da PostgreSQL şifresi hardcoded — secret management gerekli | 🟠 HIGH |
| 4 | Rate limiter `InMemoryRateLimiter` kullanıyor — production'da Redis backend şart | 🟠 HIGH |
| 5 | Model dosyaları `.gitignore`'da değil — büyük binary dosyalar repo'ya girerse sorun olur | 🟡 MEDIUM |

---

## 4. Geliştirme Fazları

### Faz 1 — Temel Altyapı ✅ TAMAMLANDI
- Hexagonal mimari
- In-memory cache + repository
- Temel Flask API + güvenlik başlıkları
- Unit testler

### Faz 2 — Asenkron Pipeline ⚙️ KISMİ
- [x] Celery + Redis broker konfigürasyonu
- [x] `summarize_article` task (temel implementasyon)
- [ ] `IMessageQueue` port interface
- [ ] `summary_routes.py` — POST/GET endpoint'leri
- [ ] `request_summary.py` ve `get_summary_status.py` use case'leri

### Faz 3 — Production Backend 🔜 SIRADAKI
- [ ] PostgreSQL + Alembic migration'larını çalıştır
- [ ] Redis cache'i etkinleştir (`USE_REDIS=true`)
- [ ] Celery worker'ı Docker Compose ile entegre et
- [ ] End-to-end testi: haber getir → Celery'ye gönder → özet yaz → veritabanına kaydet

### Faz 4 — Observability & Quality 🔜
- [ ] OpenTelemetry trace'lerini Jaeger/Grafana'ya bağla
- [ ] Prometheus + Grafana dashboard kurulumu
- [ ] Test coverage %80'in üzerine çıkar
- [ ] CI pipeline'ına `safety check` CVE taraması ekle

### Faz 5 — Cloud Deployment 🔜 (Azure)
- [ ] Azure Container Apps veya AKS deployment
- [ ] Azure Key Vault secret yönetimi
- [ ] Azure Database for PostgreSQL Flexible Server
- [ ] Azure Cache for Redis
- [ ] Azure Front Door + WAF
- [ ] Azure Monitor + Application Insights entegrasyonu

---

## 5. Teknoloji Kararları

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Web framework | Flask 3 | Hafif, WSGI, production-proven |
| ORM | SQLAlchemy 2 | Type-safe, async desteği |
| ML | HuggingFace Transformers | `distilbart-cnn-12-6` başarılı özetleme |
| Async queue | Celery + Redis | Mature ekosistem, retry/backoff desteği |
| Cache | Redis | TTL yönetimi, distributed cache |
| Config | pydantic-settings | Type-safe env değişkenleri |
| Logging | structlog | JSON structured logs, otel entegrasyonu |
| Tracing | OpenTelemetry | Vendor-agnostic, OTLP protokol |
| Test | pytest + pytest-cov | Standart Python test framework |
| SAST | bandit | Python-specific güvenlik analizi |
| Lint | ruff | Hızlı, kapsamlı Python linter |

---

## 6. Dizin Yapısı (Mevcut Durum)

```
hubb/
├── .github/workflows/ci.yml     # CI pipeline
├── deployment/docker/            # Dockerfile + compose
├── src/
│   ├── api/                      # Presentation Layer
│   │   ├── middleware/           # security, rate_limit, metrics, validation
│   │   ├── routes/               # news_routes, health_routes [summary_routes EKSİK]
│   │   └── templates/            # index.html
│   ├── application/              # Use Cases + DTOs
│   │   ├── use_cases/            # get_top_news, search_news [request_summary EKSİK]
│   │   └── dtos/                 # news_dto, summary_dto
│   ├── config/                   # settings, logging, telemetry
│   ├── domain/                   # Core business logic
│   │   ├── entities/             # article, summary
│   │   ├── ports/                # i_cache, i_news_provider, i_summarizer [i_message_queue EKSİK]
│   │   ├── repositories/         # i_article_repository, i_summary_repository
│   │   └── value_objects/        # keyword [article_id EKSİK]
│   ├── infrastructure/           # Adapters
│   │   ├── cache/                # in_memory, redis
│   │   ├── database/             # in_memory, postgres, models, migrations
│   │   ├── ml/                   # huggingface, model_loader
│   │   └── news/                 # newsapi_adapter
│   └── workers/                  # Celery app + summarize_task
└── tests/
    ├── unit/                     # Domain, application, API, infrastructure
    └── integration/              # Cache, database
```

---

## 7. Hızlı Başlangıç (Geliştirici)

```bash
# 1. Bağımlılıkları yükle
make install

# 2. Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasında NEWS_API_KEY değerini doldur

# 3. Uygulamayı başlat (in-memory mod)
make run

# 4. Testleri çalıştır
make test

# 5. Full stack (PostgreSQL + Redis + Celery)
make docker-up
```
