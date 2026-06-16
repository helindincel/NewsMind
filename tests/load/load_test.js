/**
 * HUBB API — k6 Load Test Suite
 *
 * Scenarios:
 *   baseline   — steady 10 RPS for 1 min  (smoke / baseline)
 *   ramp_up    — ramp from 0 → 50 VU over 2 min, hold 3 min, ramp down
 *   spike      — sudden burst to 200 VU for 30 s then back to 10 VU
 *
 * Usage (local, app must be running on port 5000):
 *   k6 run tests/load/load_test.js
 *
 * Override base URL:
 *   k6 run -e BASE_URL=http://localhost:8000 tests/load/load_test.js
 *
 * Run a specific scenario only:
 *   k6 run --env SCENARIO=baseline tests/load/load_test.js
 *
 * Install k6: https://k6.io/docs/get-started/installation/
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ── Custom metrics ────────────────────────────────────────────────────────────
const errorRate = new Rate("errors");
const cacheHitDuration = new Trend("cache_hit_duration_ms", true);
const cacheMissDuration = new Trend("cache_miss_duration_ms", true);
const newsEndpointErrors = new Counter("news_endpoint_errors");

// ── Config ────────────────────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://localhost:5000";
const SCENARIO = __ENV.SCENARIO || "all";

// ── Thresholds ────────────────────────────────────────────────────────────────
export const options = {
  thresholds: {
    // 95th percentile response time under 2 s
    http_req_duration: ["p(95)<2000"],
    // Error rate below 1%
    errors: ["rate<0.01"],
    // Health endpoint always fast
    "http_req_duration{endpoint:health}": ["p(99)<200"],
  },

  scenarios:
    SCENARIO === "baseline"
      ? { baseline: baselineScenario() }
      : SCENARIO === "ramp_up"
      ? { ramp_up: rampUpScenario() }
      : SCENARIO === "spike"
      ? { spike: spikeScenario() }
      : {
          baseline: baselineScenario(),
          ramp_up: { ...rampUpScenario(), startTime: "1m30s" },
          spike: { ...spikeScenario(), startTime: "7m" },
        },
};

function baselineScenario() {
  return {
    executor: "constant-arrival-rate",
    rate: 10,
    timeUnit: "1s",
    duration: "1m",
    preAllocatedVUs: 20,
    maxVUs: 50,
    tags: { scenario: "baseline" },
  };
}

function rampUpScenario() {
  return {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "2m", target: 50 },
      { duration: "3m", target: 50 },
      { duration: "1m", target: 0 },
    ],
    tags: { scenario: "ramp_up" },
  };
}

function spikeScenario() {
  return {
    executor: "ramping-vus",
    startVUs: 10,
    stages: [
      { duration: "10s", target: 200 },
      { duration: "30s", target: 200 },
      { duration: "20s", target: 10 },
    ],
    tags: { scenario: "spike" },
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function tag(endpoint) {
  return { tags: { endpoint } };
}

// ── Main VU function ──────────────────────────────────────────────────────────
export default function () {
  // Weight distribution: health 10%, top news 50%, search 30%, metrics 10%
  const rand = Math.random();

  if (rand < 0.1) {
    healthCheck();
  } else if (rand < 0.6) {
    topNews();
  } else if (rand < 0.9) {
    searchNews();
  } else {
    metricsEndpoint();
  }

  sleep(Math.random() * 0.5 + 0.1); // 100–600 ms think time
}

function healthCheck() {
  group("health", () => {
    const res = http.get(`${BASE_URL}/health`, tag("health"));
    const ok = check(res, {
      "health 200": (r) => r.status === 200,
      "health body has status": (r) => r.json("status") !== undefined,
    });
    errorRate.add(!ok);
  });
}

function topNews() {
  group("top_news", () => {
    const res = http.get(`${BASE_URL}/api/news?page=1&page_size=10`, tag("api_news"));
    const ok = check(res, {
      "top news 2xx": (r) => r.status >= 200 && r.status < 300,
      "top news has articles key": (r) => {
        try {
          return r.json("articles") !== undefined;
        } catch {
          return false;
        }
      },
    });

    if (!ok) newsEndpointErrors.add(1);
    errorRate.add(!ok);

    // Track cache behaviour via X-Cache-Hit header (if set by app)
    const cacheHit = res.headers["X-Cache-Hit"];
    if (cacheHit === "true") {
      cacheHitDuration.add(res.timings.duration);
    } else {
      cacheMissDuration.add(res.timings.duration);
    }
  });
}

function searchNews() {
  const keywords = ["technology", "science", "health", "business", "sports"];
  const kw = keywords[Math.floor(Math.random() * keywords.length)];

  group("search_news", () => {
    const res = http.get(
      `${BASE_URL}/api/news?keyword=${kw}&page=1&page_size=10`,
      tag("api_news_search")
    );
    const ok = check(res, {
      "search 2xx": (r) => r.status >= 200 && r.status < 300,
    });
    errorRate.add(!ok);
  });
}

function metricsEndpoint() {
  group("metrics", () => {
    const res = http.get(`${BASE_URL}/metrics`, tag("metrics"));
    check(res, {
      "metrics 200": (r) => r.status === 200,
      "metrics content-type prometheus": (r) =>
        (r.headers["Content-Type"] || "").includes("text/plain"),
    });
  });
}

// ── Summary handler ───────────────────────────────────────────────────────────
export function handleSummary(data) {
  return {
    "tests/load/results/summary.json": JSON.stringify(data, null, 2),
    stdout: textSummary(data),
  };
}

function textSummary(data) {
  const metrics = data.metrics;
  const p95 = metrics.http_req_duration
    ? metrics.http_req_duration.values["p(95)"].toFixed(0)
    : "N/A";
  const errRate = metrics.errors
    ? (metrics.errors.values.rate * 100).toFixed(2)
    : "0.00";
  const reqs = metrics.http_reqs ? metrics.http_reqs.values.count : 0;

  return `
╔══════════════════════════════════════════════╗
║          HUBB Load Test Summary              ║
╠══════════════════════════════════════════════╣
║  Total requests  : ${String(reqs).padStart(24)} ║
║  Error rate      : ${String(errRate + "%").padStart(24)} ║
║  p(95) latency   : ${String(p95 + " ms").padStart(24)} ║
╚══════════════════════════════════════════════╝
`;
}
