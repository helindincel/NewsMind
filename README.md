# HUBB — AI News Summarization Platform

> Production-ready, hexagonal architecture ile inşa edilmiş gerçek zamanlı haber özetleme platformu.

[![CI](https://github.com/your-org/hubb/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/hubb/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Özellikler

- **Gerçek zamanlı haberler** — NewsAPI üzerinden top headlines ve keyword araması
- **AI özetleme** — `sshleifer/distilbart-cnn-12-6` (HuggingFace Transformers)
- **Asenkron pipeline** — Celery + Redis ile özetleme kuyruğu
- **Çok katmanlı önbellekleme** — In-memory (geliştirme) veya Redis (production)
- **Güvenlik** — CSP, HSTS, X-Frame-Options, rate limiting, input validation
- **Observability** — OpenTelemetry tracing, Prometheus metrics, structlog
- **Production hazır** — Docker, docker-compose, GitHub Actions CI

---

## Mimari

Hexagonal (Ports & Adapters) mimari ile altyapı bağımlılıkları domain logic'ten tamamen izole edilmiştir.

```
Presentation  →  Application (Use Cases)  →  Domain  ←  Infrastructure
   Flask            GetTopNews                Entities     NewsAPIAdapter
   Routes           SearchNews                Ports        HuggingFaceAdapter
   Middleware       RequestSummary            Repositories RedisAdapter
                    DTOs                      Exceptions   PostgresAdapter
```

---

## Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- [Poetry](https://python-poetry.org/) (bağımlılık yönetimi)
- NewsAPI anahtarı — [newsapi.org](https://newsapi.org/) ücretsiz plan yeterlidir

### Kurulum

```bash
# 1. Bağımlılıkları yükle
make install

# 2. Ortam değişkenlerini ayarla
cp .env.example .env
```

`.env` dosyasını açıp `NEWS_API_KEY` değerini girin:

```env
NEWS_API_KEY=your_newsapi_key_here
```

### Çalıştırma

```bash
# In-memory mod (Redis/PostgreSQL gerektirmez)
make run
```

Tarayıcıda `http://localhost:5000` adresini açın.

### Full Stack (Docker)

```bash
# PostgreSQL + Redis + API + Worker
make docker-up
```

---

## Ortam Değişkenleri

Tüm konfigürasyon `.env` dosyası üzerinden yönetilir. Şablon için `.env.example` dosyasına bakın.

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `NEWS_API_KEY` | — | **Zorunlu.** NewsAPI anahtarı |
| `SECRET_KEY` | `change-me` | Flask secret key — production'da güçlü bir değer kullanın |
| `ENVIRONMENT` | `development` | `development` veya `production` |
| `USE_REDIS` | `false` | `true` yapıldığında Redis cache etkinleşir |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis bağlantı URL'i |
| `DATABASE_URL` | — | PostgreSQL bağlantı URL'i (production) |
| `MODEL_NAME` | `sshleifer/distilbart-cnn-12-6` | HuggingFace model adı |
| `RATE_LIMIT_PER_MINUTE` | `60` | Dakika başı istek limiti |

---

## Geliştirici Komutları

```bash
make install        # Bağımlılıkları yükle (Poetry)
make run            # Geliştirme sunucusunu başlat
make test           # Testleri coverage ile çalıştır
make lint           # Ruff linter
make type-check     # mypy tip kontrolü
make security-scan  # Bandit (SAST) + Safety (CVE)
make docker-build   # Docker image'larını derle
make docker-up      # Full stack docker-compose
```

---

## Testler

```bash
make test
# veya
poetry run pytest tests/ -v --cov=src
```

Test yapısı:

```
tests/
├── unit/
│   ├── domain/          # Article, Keyword, Summary entity testleri
│   ├── application/     # Use case testleri
│   ├── api/             # Güvenlik, observability testleri
│   └── infrastructure/  # Cache, newsapi adapter testleri
├── integration/         # Cache ve database entegrasyon testleri
└── load/                # k6 yük testi (tests/load/load_test.js)
```

---

## Proje Yapısı

```
hubb/
├── .github/workflows/ci.yml     # CI pipeline (lint, test, SAST, docker)
├── deployment/docker/            # Dockerfile.api, Dockerfile.worker, docker-compose.yml
├── src/
│   ├── api/                      # Presentation Layer
│   │   ├── middleware/           # Güvenlik, rate limiting, metrics, validation
│   │   ├── routes/               # news_routes, health_routes
│   │   └── templates/            # Jinja2 HTML şablonları
│   ├── application/              # Use Cases ve DTOs
│   ├── config/                   # Settings, logging, telemetry
│   ├── domain/                   # Core domain (entities, ports, repositories)
│   ├── infrastructure/           # Dış adaptörler (NewsAPI, HuggingFace, Redis, Postgres)
│   └── workers/                  # Celery task'ları
├── tests/
├── .env.example
├── Makefile
├── pyproject.toml
└── PROJECT_PLAN.md               # Proje planı ve gap analizi
```

---

## API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/` | Ana sayfa — top headlines |
| `POST` | `/` | Keyword araması |
| `GET` | `/?keyword=<q>&page=<n>` | Sayfalı keyword araması |
| `GET` | `/health` | Sağlık kontrolü |
| `GET` | `/metrics` | Prometheus metrikleri |

---

## İlk Çalıştırmada Not

Özetleme modeli (`distilbart-cnn-12-6`) ilk çalıştırmada HuggingFace Hub'dan otomatik indirilir (~1 GB). Bu işlem birkaç dakika sürebilir.

---

## Planlanan Geliştirmeler

Eksikler ve yol haritası için [PROJECT_PLAN.md](PROJECT_PLAN.md) dosyasına bakın.
