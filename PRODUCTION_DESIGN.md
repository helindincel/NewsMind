# HUBB — Production-Ready AI News Summarization Platform
### System Design Document · Staff Engineer / Cloud Architect / MLOps Perspective

---

## Ön Analiz: Mevcut Kodun Kritik Sorunları

| # | Sorun | Dosya | Satır | Risk Seviyesi |
|---|-------|-------|-------|----------------|
| 1 | API key kaynak kodda hardcoded | `app.py` | 6 | 🔴 CRITICAL |
| 2 | NLP model her request'te senkron çalışıyor | `app.py` | 78–83 | 🔴 HIGH |
| 3 | In-memory cache, process restart'ta sıfırlanıyor | `summarizer.py` | 3 | 🟠 HIGH |
| 4 | Cache boyutu sınırsız, OOM riski var | `summarizer.py` | 3 | 🟠 HIGH |
| 5 | HTTP timeout sadece 5 saniye, retry yok | `app.py` | 26 | 🟡 MEDIUM |
| 6 | Genel `Exception` yakalanıyor, hata bilgisi kullanıcıya açık | `app.py` | 90 | 🟡 MEDIUM |
| 7 | Logging yok | — | — | 🟡 MEDIUM |
| 8 | Security header yok, CSRF koruması yok | — | — | 🔴 HIGH |
| 9 | Input validation yok (keyword injection riski) | `app.py` | 67 | 🟠 HIGH |
| 10 | Flat mimari, test edilebilirlik sıfır | — | — | 🟡 MEDIUM |

---

## 1. Hedef Mimari

### 1.1 High-Level Architecture Diagram

```mermaid
graph TB
    subgraph CLIENT["Client Layer"]
        Browser["Browser / Mobile"]
    end

    subgraph EDGE["Edge / Ingress Layer"]
        CDN["Azure Front Door\n(CDN + WAF + DDoS)"]
        APIGW["Azure API Management\n(Rate Limiting · Auth · Versioning)"]
    end

    subgraph APP["Application Layer — Azure Container Apps"]
        WEB["Web API Service\n(Flask + Gunicorn)\n2–10 replicas"]
        WORKER["Summarization Worker\n(Celery)\n1–5 replicas"]
    end

    subgraph ASYNC["Async Messaging"]
        BUS["Azure Service Bus\nQueue: summarization-jobs"]
    end

    subgraph CACHE["Cache Layer"]
        REDIS["Azure Cache for Redis\n(News · Summaries · Rate Limit)"]
    end

    subgraph DATA["Data Layer"]
        PG["Azure Database\nfor PostgreSQL Flexible\n(Articles · Summaries · Analytics)"]
        BLOB["Azure Blob Storage\n(Model artifacts · Logs · Exports)"]
    end

    subgraph ML["ML / Model Layer"]
        MLFLOW["Azure ML / MLflow\n(Model Registry · Versioning)"]
        MODEL["distilbart-cnn-12-6\n(loaded by Worker)"]
    end

    subgraph SEC["Security"]
        KV["Azure Key Vault\n(Secrets · Certs · Keys)"]
        MI["Managed Identity\n(Passwordless auth)"]
    end

    subgraph OBS["Observability"]
        AI["Application Insights\n(Traces · Exceptions · Metrics)"]
        PROM["Prometheus + Grafana\n(Custom dashboards)"]
        LAW["Log Analytics Workspace"]
    end

    Browser --> CDN --> APIGW --> WEB
    WEB --> REDIS
    WEB --> PG
    WEB --> BUS
    BUS --> WORKER
    WORKER --> REDIS
    WORKER --> PG
    WORKER --> MODEL
    MLFLOW --> MODEL
    WEB --> KV
    WORKER --> KV
    KV --> MI
    WEB --> AI
    WORKER --> AI
    AI --> LAW
    PROM --> GRAFANA["Grafana"]
    MODEL --> BLOB
```

### 1.2 Veri Akışı

```
Kullanıcı → API Gateway → Web API
  ├─ Keyword var mı?
  │   ├─ Redis'te cache var mı?  → HIT  → Response (< 5ms)
  │   └─ MISS → NewsAPI çağrısı → PostgreSQL'e kaydet → Redis'e yaz
  │
  └─ Her haber için summary var mı? (Redis/PG check)
      ├─ VAR → Response'a ekle
      └─ YOK → Service Bus'a job koy → Kullanıcıya "processing" döndür
                  └─ Worker job'u alır → Model inference → PG + Redis'e yaz
                        └─ Webhook / SSE ile frontend'e bildir
```

---

## 2. Backend Architecture — Hexagonal (Ports & Adapters)

Hexagonal Architecture tercih edildi çünkü:
- NLP pipeline, Redis, PostgreSQL ve NewsAPI gibi birden fazla dış bağımlılık mevcut
- Her adapter (NewsAPI, Redis, PG, HuggingFace) izole test edilebilir
- ML modelini değiştirirken domain katmanına dokunmak gerekmez

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│   Flask Routes · REST Controllers · Request/Response DTOs   │
│   Gunicorn WSGI · CORS · Security Headers Middleware        │
└────────────────────┬────────────────────────────────────────┘
                     │ calls
┌────────────────────▼────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│   Use Cases: GetNews, SearchNews, RequestSummary            │
│   Orchestration: cache-first lookup, job dispatching        │
│   DTOs: NewsRequest, SummaryRequest, NewsResponse           │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on (interfaces only)
┌────────────────────▼────────────────────────────────────────┐
│                    DOMAIN LAYER                              │
│   Entities: Article, Summary, SearchQuery                   │
│   Value Objects: Keyword, ArticleId, TTL                    │
│   Domain Services: SummarizationPolicy, CachePolicy         │
│   Repository Interfaces: IArticleRepo, ISummaryRepo         │
│   Port Interfaces: INewsProvider, ISummarizer, ICache        │
└────────────────────┬────────────────────────────────────────┘
                     │ implemented by
┌────────────────────▼────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                         │
│   Adapters:                                                  │
│     NewsAPIAdapter  → INewsProvider                         │
│     HuggingFaceAdapter → ISummarizer                        │
│     RedisAdapter    → ICache                                │
│     PostgresAdapter → IArticleRepo, ISummaryRepo            │
│     ServiceBusAdapter → IMessageQueue                       │
│     KeyVaultAdapter → ISecretProvider                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Yeni Klasör Yapısı

```
hubb/
├── src/
│   ├── api/                          # Presentation Layer
│   │   ├── __init__.py
│   │   ├── app.py                    # Flask app factory (create_app())
│   │   ├── middleware/
│   │   │   ├── security_headers.py  # CSP, HSTS, X-Frame-Options
│   │   │   ├── rate_limiter.py      # Redis-backed rate limiting
│   │   │   ├── request_validator.py # Input sanitization
│   │   │   └── correlation_id.py    # Request tracing
│   │   ├── routes/
│   │   │   ├── news_routes.py       # GET /news, GET /news/<id>
│   │   │   ├── summary_routes.py    # POST /summaries, GET /summaries/<id>
│   │   │   └── health_routes.py     # GET /health, GET /metrics
│   │   └── schemas/
│   │       ├── news_schema.py       # Marshmallow / Pydantic schemas
│   │       └── summary_schema.py
│   │
│   ├── application/                  # Application Layer (Use Cases)
│   │   ├── __init__.py
│   │   ├── use_cases/
│   │   │   ├── get_top_news.py
│   │   │   ├── search_news.py
│   │   │   ├── request_summary.py
│   │   │   └── get_summary_status.py
│   │   └── dtos/
│   │       ├── news_dto.py
│   │       └── summary_dto.py
│   │
│   ├── domain/                       # Domain Layer (Business Logic)
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── article.py           # Article entity
│   │   │   └── summary.py           # Summary entity + SummaryStatus enum
│   │   ├── value_objects/
│   │   │   ├── keyword.py           # Validated keyword VO
│   │   │   └── article_id.py
│   │   ├── repositories/
│   │   │   ├── i_article_repository.py   # Interface
│   │   │   └── i_summary_repository.py  # Interface
│   │   └── ports/
│   │       ├── i_news_provider.py        # External news port
│   │       ├── i_summarizer.py           # ML model port
│   │       ├── i_cache.py                # Cache port
│   │       └── i_message_queue.py        # Async messaging port
│   │
│   ├── infrastructure/               # Infrastructure Layer (Adapters)
│   │   ├── __init__.py
│   │   ├── news/
│   │   │   └── newsapi_adapter.py
│   │   ├── ml/
│   │   │   ├── huggingface_adapter.py
│   │   │   └── model_loader.py       # Lazy singleton model loading
│   │   ├── cache/
│   │   │   └── redis_adapter.py
│   │   ├── database/
│   │   │   ├── postgres_adapter.py
│   │   │   ├── models.py             # SQLAlchemy ORM models
│   │   │   └── migrations/           # Alembic migrations
│   │   ├── messaging/
│   │   │   └── service_bus_adapter.py
│   │   └── secrets/
│   │       └── keyvault_adapter.py
│   │
│   ├── workers/                      # Celery / Background Workers
│   │   ├── __init__.py
│   │   ├── celery_app.py             # Celery factory
│   │   ├── tasks/
│   │   │   ├── summarize_task.py     # @celery.task: summarize article
│   │   │   └── fetch_news_task.py    # @celery.task: scheduled news fetch
│   │   └── beat_schedule.py          # Celery Beat: periodic tasks
│   │
│   ├── config/                       # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic BaseSettings
│   │   ├── logging_config.py         # structlog configuration
│   │   └── telemetry.py              # OpenTelemetry setup
│   │
│   └── common/
│       ├── exceptions.py             # Domain exceptions
│       ├── pagination.py
│       └── health.py                 # Health check aggregator
│
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   │   ├── test_news_api.py
│   │   ├── test_redis.py
│   │   └── test_postgres.py
│   ├── e2e/
│   │   └── test_news_flow.py
│   └── conftest.py                   # pytest fixtures, test containers
│
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.worker
│   │   └── docker-compose.yml        # Local development
│   ├── k8s/                          # AKS manifests (if needed)
│   │   ├── api-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   └── hpa.yaml
│   └── bicep/                        # Azure IaC
│       ├── main.bicep
│       ├── modules/
│       │   ├── container-apps.bicep
│       │   ├── redis.bicep
│       │   ├── postgres.bicep
│       │   └── keyvault.bicep
│       └── parameters/
│           ├── dev.bicepparam
│           └── prod.bicepparam
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
│
├── .env.example                      # Commit edilir, gerçek değerler değil
├── pyproject.toml                    # Dependencies (Poetry)
├── Makefile                          # make test, make lint, make run
└── README.md
```

---

## 4. NLP Pipeline Tasarımı

### Değerlendirme Matrisi

| Çözüm | Latency | Setup Complexity | Azure Entegrasyonu | Maliyet | Karar |
|-------|---------|-----------------|-------------------|---------|-------|
| Senkron (mevcut) | Yüksek (~2–8s) | Sıfır | — | — | ❌ Elendi |
| Celery + Redis | Düşük (async) | Orta | Azure Redis | Düşük | ✅ **Seçildi** |
| Azure Service Bus | Düşük (async) | Düşük | Native | Orta | ✅ Alternatif |
| Azure Functions | Çok düşük (serverless) | Orta | Native | Düşük | ⚠️ Cold start |
| RabbitMQ | Düşük | Yüksek | Manuel | Yüksek | ❌ Elendi |

### Karar: Celery + Azure Cache for Redis

**Neden?**
- Mevcut Python stack'e minimal değişiklikle entegre olur
- Azure Cache for Redis hem cache hem Celery broker görevi görür (tek servis, çift fayda)
- Worker'lar Container Apps'te bağımsız scale edilebilir
- Retry, dead-letter queue, task monitoring (Flower) native olarak desteklenir
- Azure Service Bus ikincil seçenek olarak ileride drop-in replace yapılabilir

### Async Summarization Akışı

```
POST /summaries  (article_id)
     │
     ├─ Summary DB'de var mı? → VAR → 200 + summary
     │
     └─ YOK → Celery task enqueue → 202 Accepted + job_id
                    │
              Worker picks up
                    │
              HuggingFace model inference
                    │
              ├─ Redis'e yaz (TTL: 24 saat)
              ├─ PostgreSQL'e kaydet
              └─ WebSocket / SSE ile notify (opsiyonel)

GET /summaries/{job_id}/status → pending | processing | completed | failed
```

### Model Loading Stratejisi

```python
# infrastructure/ml/model_loader.py
# Model worker başladığında bir kez yüklenir, her task'ta yeniden yüklenmez
class ModelRegistry:
    _instance: Optional[pipeline] = None

    @classmethod
    def get_model(cls) -> pipeline:
        if cls._instance is None:
            model_path = settings.MODEL_PATH  # Blob Storage'dan veya local
            cls._instance = pipeline(
                "summarization",
                model=model_path,
                device=0 if torch.cuda.is_available() else -1
            )
        return cls._instance
```

---

## 5. Cache Stratejisi

### Redis Cache Tasarımı

```
┌─────────────────┬──────────────────────────────────┬──────────┬────────────────────┐
│ Cache Tipi      │ Key Pattern                      │ TTL      │ Invalidation        │
├─────────────────┼──────────────────────────────────┼──────────┼────────────────────┤
│ Top Headlines   │ news:top:{page}:{page_size}      │ 30 dk    │ Scheduled job       │
│ Keyword Search  │ news:kw:{hash(keyword)}:{page}   │ 15 dk    │ TTL expire          │
│ Article Detail  │ article:{article_id}              │ 2 saat   │ Manual (rare)       │
│ Summary         │ summary:{article_id}:{model_ver} │ 24 saat  │ Model version bump  │
│ Rate Limit      │ ratelimit:{ip}:{window}           │ 60 sn    │ TTL expire          │
│ Job Status      │ job:{job_id}                      │ 1 saat   │ TTL expire          │
└─────────────────┴──────────────────────────────────┴──────────┴────────────────────┘
```

### Key Tasarım Kuralları

```python
# Hash kullan: keyword'ü doğrudan key'e koyma (injection riski, uzunluk sorunu)
import hashlib

def make_news_cache_key(keyword: str, page: int, page_size: int) -> str:
    kw_hash = hashlib.sha256(keyword.lower().strip().encode()).hexdigest()[:16]
    return f"news:kw:{kw_hash}:{page}:{page_size}"

# Model versiyonu key'e dahil: model güncellenince eski summary'ler geçersiz olur
def make_summary_cache_key(article_id: str, model_version: str) -> str:
    return f"summary:{article_id}:{model_version}"
```

### Cache Optimizasyonları

```
Read-Through:  Uygulama cache miss'te DB'ye düşer, Redis'e yazar
Write-Through: Yeni summary hem Redis hem PG'ye aynı anda yazılır
Cache Stampede Koruması: Redis SETNX ile lock + jitter TTL
Max Memory Policy: allkeys-lru (Azure Redis varsayılanı)
Serialization: msgpack (JSON'dan %30–60 daha hızlı + küçük)
```

---

## 6. Security Tasarımı

### 6.1 Secret Management

```
ASLA yapılmaması gereken (mevcut durum):
  API_KEY = "3981648866734d75902b4b10fc53ff32"  ← Git geçmişine giriyor!

Doğru yaklaşım:
  1. Azure Key Vault → Managed Identity → uygulama okur
  2. Local dev: .env (gitignore'da) → python-dotenv
  3. CI/CD: GitHub Secrets → Container Apps environment variables
```

```python
# config/settings.py — Pydantic BaseSettings
from pydantic_settings import BaseSettings
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class Settings(BaseSettings):
    NEWS_API_KEY: str          # Runtime'da KV'den inject edilir
    REDIS_URL: str
    DATABASE_URL: str
    MODEL_VERSION: str = "sshleifer/distilbart-cnn-12-6"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### 6.2 Security Katmanları

```
Layer 1 — Network:
  Azure Front Door WAF → OWASP CRS rule set aktif
  DDoS Protection Standard
  Private Endpoint: Redis, PostgreSQL, Service Bus

Layer 2 — API Gateway:
  Azure API Management: JWT validation, subscription keys
  Rate limiting: 100 req/min per IP (unauthenticated)
  IP allowlist (opsiyonel, B2B senaryosu için)

Layer 3 — Application:
  Input Validation (Pydantic):
    - keyword max 100 karakter
    - whitelist chars: alphanumeric + boşluk + tire
    - page: 1–100 arası integer
  Security Headers (Flask middleware):
    Content-Security-Policy: default-src 'self'
    X-Content-Type-Options: nosniff
    X-Frame-Options: DENY
    Strict-Transport-Security: max-age=31536000; includeSubDomains
    Permissions-Policy: geolocation=(), microphone=()
  CSRF: Flask-WTF (form tabanlı) veya Double Submit Cookie (SPA)

Layer 4 — Data:
  PostgreSQL: TLS zorunlu, pg_trgm indexing, parameterized queries
  Redis: AUTH + TLS, RESP3 protokolü

Layer 5 — Identity:
  Managed Identity: şifresi olmayan servis kimliği
  Azure RBAC: least-privilege principle
  Service Principal: CI/CD için minimum scope
```

### 6.3 Dependency Scanning

```yaml
# .github/workflows/security.yml
- name: Safety Check (CVE scan)
  run: pip install safety && safety check

- name: Bandit (SAST)
  run: pip install bandit && bandit -r src/

- name: Trivy (Container vulnerability scan)
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: hubb-api:${{ github.sha }}
    exit-code: '1'
    severity: 'CRITICAL,HIGH'
```

---

## 7. Observability

### 7.1 Structured Logging (structlog)

**Ne işe yarar?** JSON formatında makine-okunabilir loglar üretir, query'lenebilir.  
**Neden gerekli?** Şu anda logging yok, hata debug'ı imkansız.

```python
# config/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer()      # Azure Log Analytics uyumlu
    ]
)

# Kullanım
log = structlog.get_logger()
log.info("news.fetched", keyword="climate", article_count=20, cache_hit=False, duration_ms=342)
log.error("summary.failed", article_id="abc123", error="CUDA OOM", model_version="12-6")
```

### 7.2 OpenTelemetry

**Ne işe yarar?** Distributed tracing: request'in tüm sistemdeki yolculuğunu izler.  
**Neden gerekli?** Web API → Service Bus → Worker → Model zincirinde hangi adımın yavaş olduğunu görmek için.

```python
# config/telemetry.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

provider = TracerProvider()
# Hem Application Insights hem Jaeger/Grafana'ya gönder
provider.add_span_processor(BatchSpanProcessor(AzureMonitorTraceExporter(
    connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
)))
trace.set_tracer_provider(provider)
```

### 7.3 Application Insights

**Ne işe yarar?** Azure native APM: exception tracking, dependency tracking, custom metrics.  
**Neden gerekli?** Hangi haber keyword'lerinin en çok arandığını, model inference latency dağılımını, API hata oranlarını görmek için.

```python
# Özel metrikler
from applicationinsights import TelemetryClient

tc = TelemetryClient(settings.APPINSIGHTS_INSTRUMENTATION_KEY)
tc.track_metric("summarization.latency_ms", latency)
tc.track_metric("cache.hit_rate", hit_rate)
tc.track_event("news.searched", {"keyword": keyword, "results": count})
```

### 7.4 Prometheus + Grafana

**Ne işe yarar?** Infrastructure ve application metrikleri: request/s, error rate, queue depth.  
**Neden gerekli?** SLO/SLA takibi, auto-scaling trigger için threshold alertler.

```python
# api/routes/health_routes.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
SUMMARY_LATENCY = Histogram('summarization_seconds', 'Time for summarization', buckets=[0.1, 0.5, 1, 3, 8])
CACHE_HIT = Counter('cache_hits_total', 'Cache hits', ['cache_type'])
QUEUE_DEPTH = Gauge('celery_queue_depth', 'Celery queue depth')

@health_bp.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
```

**Grafana Dashboard Panelleri:**
- Request Rate (req/s) & Error Rate (%)
- P50 / P95 / P99 summarization latency
- Cache Hit Rate (target: >85%)
- Celery Queue Depth & Worker throughput
- NewsAPI success/failure rate
- Active DB connections & query latency

---

## 8. Database Gereksinimleri

### Veritabanı Seçimi

| DB | Avantaj | Dezavantaj | Karar |
|----|---------|------------|-------|
| **PostgreSQL** | ACID, full-text search (pg_trgm), JSONB, Azure managed | Dikey scale sınırı | ✅ **Seçildi** |
| Cosmos DB | Global distribution, serverless | Pahalı, NoSQL query limitleri | ⚠️ Ölçek ihtiyacı olursa |
| MongoDB | Flexible schema | Azure entegrasyonu zayıf, operasyonel yük | ❌ |

### Schema Tasarımı

```sql
-- Haberler
CREATE TABLE articles (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id   TEXT UNIQUE,           -- NewsAPI article ID
    title         TEXT NOT NULL,
    content       TEXT,
    url           TEXT NOT NULL,
    image_url     TEXT,
    source        TEXT,
    published_at  TIMESTAMPTZ NOT NULL,
    keyword       TEXT,                  -- hangi arama ile geldi
    fetched_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT articles_url_unique UNIQUE (url)
);

-- Özetler
CREATE TABLE summaries (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id    UUID REFERENCES articles(id) ON DELETE CASCADE,
    summary_text  TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending|processing|completed|failed
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    duration_ms   INTEGER,
    CONSTRAINT summaries_article_model_unique UNIQUE (article_id, model_version)
);

-- Kullanıcı Aramaları (Analytics)
CREATE TABLE search_queries (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword    TEXT NOT NULL,
    ip_hash    TEXT,                     -- SHA256(IP) — GDPR uyumlu
    result_cnt INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performans index'leri
CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_keyword ON articles(keyword);
CREATE INDEX idx_summaries_status ON summaries(status) WHERE status IN ('pending','processing');
CREATE INDEX idx_search_queries_keyword ON search_queries(keyword);
```

### Hangi Veriler Saklanır?

| Veri | Depolama | Süre | Amaç |
|------|----------|------|-------|
| Articles | PostgreSQL | 30 gün | Duplicate önleme, offline okuma |
| Summaries | PostgreSQL + Redis | PG: sonsuz, Redis: 24 saat | Yeniden hesaplamayı önleme |
| Search queries | PostgreSQL | 90 gün | Analytics, trending topics |
| Model artifacts | Azure Blob Storage | Sonsuz (versioned) | Rollback, reproducibility |
| Access logs | Log Analytics | 90 gün | Security audit |

---

## 9. API Tasarımı

### REST API Endpoints

#### `GET /news`
```
Amaç: Top headlines veya keyword search

Query params:
  keyword  (string, max 100 chars, optional)
  page     (integer, 1–100, default: 1)
  page_size (integer, 1–50, default: 20)

Response 200:
{
  "articles": [
    {
      "id": "uuid",
      "title": "...",
      "image_url": "...",
      "url": "...",
      "published_at": "2026-06-15T10:00:00Z",
      "summary": { "text": "...", "status": "completed" } | null
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 340 }
}

Hata kodları:
  400 Bad Request  — invalid keyword chars
  429 Too Many Requests — rate limit exceeded
  502 Bad Gateway  — NewsAPI unreachable
  503 Service Unavailable — circuit breaker open
```

#### `GET /news/{article_id}`
```
Amaç: Tek bir haberin detayı + summary

Response 200:
{
  "id": "uuid",
  "title": "...",
  "content": "...",
  "summary": { "text": "...", "model_version": "12-6", "status": "completed" }
}

Hata kodları:
  404 Not Found
  410 Gone (30 günlük retention doldu)
```

#### `POST /summaries`
```
Amaç: Belirli bir haber için async summarization başlat

Request body:
{ "article_id": "uuid" }

Response 202 Accepted:
{ "job_id": "uuid", "status": "pending", "status_url": "/summaries/uuid/status" }

Response 200 (zaten var):
{ "summary_text": "...", "status": "completed" }

Hata kodları:
  404 article not found
  422 article content too short
```

#### `GET /summaries/{job_id}/status`
```
Amaç: Async summarization job durumu

Response 200:
{
  "job_id": "uuid",
  "status": "pending|processing|completed|failed",
  "summary_text": "..." (only when completed),
  "error": "..." (only when failed)
}
```

#### `GET /health`
```
Amaç: Liveness + readiness probe

Response 200:
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "newsapi": "ok",
    "worker_queue_depth": 12
  },
  "version": "1.2.3",
  "model_version": "sshleifer/distilbart-cnn-12-6"
}

Response 503 (unhealthy):
{ "status": "degraded", "checks": { "database": "error: connection timeout" } }
```

#### `GET /metrics`
```
Amaç: Prometheus scrape endpoint
Response: text/plain Prometheus exposition format
```

#### `GET /news/trending`
```
Amaç: Son 24 saatin en çok aranan keyword'leri

Response 200:
{ "trending": ["climate", "AI", "economy"], "window": "24h" }
```

---

## 10. Cloud Deployment — Azure

### Servis Karşılaştırması

| Servis | Maliyet | Ölçeklenebilirlik | Operasyonel Yük | Karar |
|--------|---------|-------------------|-----------------|-------|
| **Azure Container Apps** | Orta | Auto-scale (KEDA) | Düşük | ✅ **Seçildi** |
| Azure App Service | Düşük | Manuel/auto | Çok düşük | Plan B (düşük trafik) |
| AKS | Yüksek | Çok yüksek | Yüksek | Yüksek trafik (>10k RPM) |
| Azure AI Foundry | Yüksek | Yüksek | Düşük | Sadece managed LLM ihtiyacında |

### Azure Mimarisi

```
Azure Subscription
└── Resource Group: hubb-prod
    ├── Azure Front Door (WAF + CDN)
    ├── Azure API Management (Developer tier)
    ├── Azure Container Apps Environment
    │   ├── hubb-api (Container App) — min:2 max:10 replicas
    │   │   Scale rule: HTTP requests > 50/instance
    │   └── hubb-worker (Container App) — min:1 max:5 replicas
    │       Scale rule: Azure Service Bus queue depth > 10
    ├── Azure Cache for Redis (Standard C1, 1 GB)
    ├── Azure Database for PostgreSQL Flexible (Burstable B2ms)
    ├── Azure Service Bus (Standard, summarization-jobs queue)
    ├── Azure Container Registry (Basic)
    ├── Azure Key Vault (Standard)
    ├── Azure Blob Storage (LRS, model artifacts)
    ├── Application Insights + Log Analytics Workspace
    └── Azure Managed Identity (hubb-api-identity)
```

### Aylık Maliyet Tahmini (Dev/Test)

| Servis | SKU | Tahmini Maliyet/Ay |
|--------|-----|---------------------|
| Container Apps (2 cont.) | Consumption | ~$20–50 |
| Redis Cache | C0 Basic | ~$16 |
| PostgreSQL Flexible | Burstable B1ms | ~$12 |
| Service Bus | Standard | ~$10 |
| Key Vault | Standard | ~$5 |
| Container Registry | Basic | ~$5 |
| App Insights | Pay-as-you-go | ~$0–20 |
| **TOPLAM** | | **~$68–118/ay** |

### Bicep IaC Örneği (özet)

```bicep
// deployment/bicep/modules/container-apps.bicep
resource hubbApi 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'hubb-api'
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${managedIdentityId}': {} } }
  properties: {
    configuration: {
      ingress: { external: true, targetPort: 8000 }
      secrets: [{ name: 'appinsights-key', keyVaultUrl: kvSecretUri, identity: managedIdentityId }]
    }
    template: {
      scale: { minReplicas: 2, maxReplicas: 10
        rules: [{ name: 'http-scaling', http: { metadata: { concurrentRequests: '50' } } }]
      }
      containers: [{
        image: '${acrLoginServer}/hubb-api:${imageTag}'
        env: [
          { name: 'ENVIRONMENT', value: 'production' }
          { name: 'APPINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-key' }
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
    }
  }
}
```

---

## 11. CI/CD Pipeline

### GitHub Actions — CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      
      - name: Install dependencies
        run: pip install poetry && poetry install

      # Stage 1: Lint
      - name: Ruff (linting + formatting)
        run: poetry run ruff check src/ tests/

      - name: mypy (type checking)
        run: poetry run mypy src/

      # Stage 2: Security
      - name: Bandit (SAST)
        run: poetry run bandit -r src/ -ll

      - name: Safety (CVE scan)
        run: poetry run safety check

      - name: Detect secrets (git-secrets)
        uses: trufflesecurity/trufflehog@main
        with: { path: ./ }

      # Stage 3: Tests
      - name: Unit tests
        run: poetry run pytest tests/unit/ -v --cov=src --cov-report=xml

      - name: Integration tests (Testcontainers)
        run: poetry run pytest tests/integration/ -v
        env:
          REDIS_URL: redis://localhost:6379
          DATABASE_URL: postgresql://test:test@localhost:5432/hubb_test

      # Stage 4: Docker Build
      - name: Build API image
        run: |
          docker build -f deployment/docker/Dockerfile.api \
            -t ${{ secrets.ACR_LOGIN_SERVER }}/hubb-api:${{ github.sha }} .

      - name: Trivy container scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: hubb-api:${{ github.sha }}
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      # Stage 5: Push
      - name: Push to ACR
        if: github.ref == 'refs/heads/main'
        run: |
          az acr login --name ${{ secrets.ACR_NAME }}
          docker push ${{ secrets.ACR_LOGIN_SERVER }}/hubb-api:${{ github.sha }}
          docker push ${{ secrets.ACR_LOGIN_SERVER }}/hubb-api:latest
```

### GitHub Actions — CD

```yaml
# .github/workflows/cd.yml
name: CD

on:
  workflow_run:
    workflows: [CI]
    branches: [main]
    types: [completed]

jobs:
  deploy-staging:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment: staging
    runs-on: ubuntu-latest
    steps:
      - name: Azure Login (OIDC — no stored password)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy to Container Apps (staging)
        run: |
          az containerapp update \
            --name hubb-api-staging \
            --resource-group hubb-staging \
            --image ${{ secrets.ACR_LOGIN_SERVER }}/hubb-api:${{ github.sha }}

      - name: Smoke test staging
        run: |
          curl -f https://hubb-api-staging.azurecontainerapps.io/health || exit 1

  deploy-production:
    needs: deploy-staging
    environment: production   # Manual approval gate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production (Blue-Green)
        run: |
          az containerapp ingress traffic set \
            --name hubb-api \
            --resource-group hubb-prod \
            --revision-weight latest=100
```

---

## 12. MLOps Perspektifi

### 12.1 Model Versioning (Azure ML + MLflow)

```python
# Her model yüklendiğinde versiyonu logla
import mlflow

with mlflow.start_run(run_name="distilbart-evaluation"):
    mlflow.log_param("model_name", "sshleifer/distilbart-cnn-12-6")
    mlflow.log_param("quantization", "none")
    mlflow.log_metric("rouge_l", 0.412)
    mlflow.log_metric("avg_latency_ms", 2340)
    mlflow.set_tag("stage", "production")
    mlflow.transformers.log_model(model, "summarizer")

# Registry'ye kaydet
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage("hubb-summarizer", version=3, stage="Production")
```

### 12.2 Rollback Stratejisi

```
Model version tag'leri:
  Production (aktif)
  Staging    (test edilen)
  Archived   (eski, rollback için)

Rollback prosedürü:
  1. Grafana'da ROUGE score veya error rate spike algılanır
  2. Alert: Azure Monitor → PagerDuty
  3. Tek komut: az containerapp update --image hubb-worker:v2-prev
  4. Blue-green ile trafiği anında eski versiyona çevir
  5. MLflow'da model stage'ini Archived → Production yap
```

### 12.3 A/B Testing

```python
# Worker: hangi model versiyonunu kullanacağını feature flag'den al
from unleash import UnleashClient

unleash = UnleashClient(url=settings.UNLEASH_URL, app_name="hubb")

def get_model_for_article(article_id: str) -> str:
    if unleash.is_enabled("new-model-v4", context={"userId": article_id}):
        return "facebook/bart-large-cnn"    # Yeni model (10% traffic)
    return "sshleifer/distilbart-cnn-12-6"  # Mevcut model (90% traffic)
```

### 12.4 Model Monitoring & Drift Detection

```
Output Drift:
  - Günlük ortalama summary uzunluğu izlenir
  - ROUGE score (referans dataset ile) haftalık hesaplanır
  - Anormal kısalma/uzama → drift alert

Performance Drift:
  - P95 inference latency > 5 saniye → alert
  - Error rate > %2 → automatic rollback trigger

Data Drift:
  - Gelen haber içerik uzunluğu dağılımı izlenir
  - NewsAPI'den truncated content artışı → model input quality degradation

Tool:
  Azure ML Data Drift Monitor veya Evidently AI (open source)
```

---

## 13. Production Risk Analizi

| # | Risk | Etki | Olasılık | Çözüm |
|---|------|------|----------|-------|
| 1 | NewsAPI rate limit (100 req/gün free tier) | YÜKSEK | YÜKSEK | Paid plan, aggressive caching, fallback provider (GNews API) |
| 2 | HuggingFace model CUDA OOM | YÜKSEK | ORTA | Batch size limiti, CPU fallback, max_input_tokens hard limit |
| 3 | Redis bağlantı kaybı | ORTA | DÜŞÜK | Circuit breaker, DB fallback, retry with exponential backoff |
| 4 | PostgreSQL disk dolu (articles birikimi) | ORTA | ORTA | 30 günlük retention job (Celery Beat), storage alerts |
| 5 | API key sızması (mevcut durum) | KRİTİK | MEVCUT | Key rotation + Azure Key Vault (acil aksiyon!) |
| 6 | DDoS / scraping | YÜKSEK | ORTA | Azure Front Door WAF, rate limiting, CAPTCHA |
| 7 | Celery worker crash, job kaybı | ORTA | DÜŞÜK | Redis persistence (AOF), dead-letter queue, task idempotency |
| 8 | Model versiyonu güncelleme (uyumsuz output) | ORTA | ORTA | A/B test + canary deployment, ROUGE threshold gate |
| 9 | Container image vulnerability | YÜKSEK | ORTA | Trivy scan CI/CD, weekly base image rebuild |
| 10 | Summarization kalitesi (kısa/anlamsız) | DÜŞÜK | YÜKSEK | Min token threshold, fallback: first 2 sentences |
| 11 | Azure region outage | YÜKSEK | ÇOK DÜŞÜK | Multi-region deployment (Active-Passive), Azure Front Door geo-routing |
| 12 | GDPR: IP adresi loglanıyor | YÜKSEK | MEVCUT | IP'yi loglamadan önce SHA256 hash'le, retention policy 90 gün |

---

## 14. Yol Haritası (Roadmap)

### Phase 1 — Architecture Refactor (Hafta 1–2)

**Hedef:** Çalışan uygulamayı katmanlı mimariye taşı, test edilebilir hale getir.

| İş | Çıktı |
|----|-------|
| Hexagonal architecture'a geçiş | `src/` yapısı oluşturulur |
| Pydantic settings + .env | Hardcoded API key kaldırılır (**ACİL**) |
| Adapter pattern (NewsAPI, HuggingFace) | Mocklanabilir interface'ler |
| Unit testler (%70 coverage) | `tests/unit/` |
| Dockerfile (API + Worker) | Konteynerize uygulama |

**Teknik Borç Azaltımı:** API key güvenlik riski ortadan kalkar. Monolitik yapı çözülür.

---

### Phase 2 — Security Hardening (Hafta 3)

**Hedef:** OWASP Top 10 güvenlik açıklarını kapat.

| İş | Çıktı |
|----|-------|
| Azure Key Vault entegrasyonu | Sıfır hardcoded secret |
| Security headers middleware | CSP, HSTS, X-Frame-Options |
| Input validation (Pydantic) | Injection koruması |
| Rate limiting (Redis) | DDoS koruması |
| Bandit + Safety CI entegrasyonu | Her PR'da otomatik scan |

**Teknik Borç Azaltımı:** Güvenlik açıkları kapatılır, GDPR uyumu başlar.

---

### Phase 3 — Scalability (Hafta 4–5)

**Hedef:** Async summarization, Redis cache, PostgreSQL entegrasyonu.

| İş | Çıktı |
|----|-------|
| Celery + Azure Redis kurulumu | Senkron NLP kaldırılır |
| PostgreSQL schema + Alembic | Veriler persist edilir |
| Redis cache adapter (TTL, key design) | Cache hit rate >85% |
| Circuit breaker (NewsAPI) | Graceful degradation |
| Celery Beat: news fetch job | Proaktif cache warming |

**Teknik Borç Azaltımı:** Request timeout riski ortadan kalkar. In-memory cache OOM riski yok.

---

### Phase 4 — Observability (Hafta 6)

**Hedef:** Sistemi kör çalıştırmaktan çıkar, tam görünürlük sağla.

| İş | Çıktı |
|----|-------|
| structlog JSON logging | Aranabilir log stream |
| OpenTelemetry tracing | Distributed trace görünürlüğü |
| Application Insights entegrasyonu | Azure native APM |
| Prometheus /metrics endpoint | Scraped metrikler |
| Grafana dashboards (5 panel) | SLO takibi |
| Alert rules (latency, error rate) | PagerDuty entegrasyonu |

**Teknik Borç Azaltımı:** Sessiz hatalar görünür olur. SLA tanımlanabilir.

---

### Phase 5 — Production Release (Hafta 7–8)

**Hedef:** Azure'a production grade deploy, MLOps pipeline tamamlandı.

| İş | Çıktı |
|----|-------|
| Bicep IaC (tam Azure stack) | Tekrarlanabilir infra deploy |
| GitHub Actions CI/CD | Otomatik pipeline |
| Azure Container Apps (prod) | Production ortamı |
| MLflow model registry | Model versioning |
| Load test (k6, 100 concurrent) | Baseline performance raporu |
| Runbook + incident playbook | Operasyonel olgunluk |
| Penetration test (OWASP ZAP) | Security sign-off |

**Teknik Borç Azaltımı:** Manuel deployment ortadan kalkar. İlk production SLO: %99.5 uptime, P95 < 200ms (news), P95 < 8s (summarization).

---

## Özet: Öncelik Sırası

```
Bugün:    1. API key'i kaynak koddan kaldır → .env + Key Vault (SECURITY)
Bu hafta: 2. Hexagonal architecture + unit tests
          3. Celery async summarization
Ay sonuna: 4. Redis + PostgreSQL entegrasyonu
           5. Observability stack
           6. CI/CD pipeline
           7. Production Azure deploy
```

---

*Doküman: HUBB Production Architecture Design v1.0 — 2026-06-15*  
*Hazırlayan: Staff Engineer / Cloud Architect / MLOps Engineer review*
