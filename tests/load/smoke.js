import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 5,
  duration: "30s",
  thresholds: {
    http_req_duration: ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
  },
};

const BASE_URL = __ENV.API_URL || "http://localhost:8000";

export default function () {
  // Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, {
    "health status 200": (r) => r.status === 200,
    "health responds ok": (r) => r.json().status === "ok",
  });

  // Health DB
  const healthDb = http.get(`${BASE_URL}/health/db`);
  check(healthDb, {
    "health/db status 200": (r) => r.status === 200,
  });

  // System status
  const system = http.get(`${BASE_URL}/health/system`);
  check(system, {
    "system status 200": (r) => r.status === 200,
  });

  // Markets list
  const markets = http.get(`${BASE_URL}/api/v1/markets`);
  check(markets, {
    "markets status 200": (r) => r.status === 200,
  });

  // Leaderboard
  const lb = http.get(`${BASE_URL}/api/v1/social/leaderboard`);
  check(lb, {
    "leaderboard status 200": (r) => r.status === 200,
  });

  sleep(1);
}
