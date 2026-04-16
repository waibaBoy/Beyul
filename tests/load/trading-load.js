import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "15s", target: 10 },
    { duration: "1m", target: 50 },
    { duration: "30s", target: 50 },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<1000", "p(99)<2000"],
    http_req_failed: ["rate<0.05"],
  },
};

const BASE_URL = __ENV.API_URL || "http://localhost:8000";
const DEV_HEADERS = {
  "Content-Type": "application/json",
  "X-Satta-User-Id": "00000000-0000-0000-0000-000000000001",
  "X-Satta-Username": "loadtest_user",
  "X-Satta-Display-Name": "Load Test",
  "X-Satta-Is-Admin": "false",
};

export default function () {
  // Get markets
  const marketsRes = http.get(`${BASE_URL}/api/v1/markets`);
  check(marketsRes, { "markets 200": (r) => r.status === 200 });

  // Get portfolio
  const portfolio = http.get(`${BASE_URL}/api/v1/portfolio/me`, {
    headers: DEV_HEADERS,
  });
  check(portfolio, {
    "portfolio status ok": (r) => r.status === 200 || r.status === 401,
  });

  // Get notifications
  const notifs = http.get(`${BASE_URL}/api/v1/notifications?limit=10`, {
    headers: DEV_HEADERS,
  });
  check(notifs, {
    "notifications ok": (r) => r.status === 200 || r.status === 401,
  });

  // Fee preview
  const feePreview = http.post(
    `${BASE_URL}/api/v1/liquidity/fee-preview`,
    JSON.stringify({
      market_id: "00000000-0000-0000-0000-000000000001",
      quantity: "10",
      price: "0.5",
      is_maker: false,
    }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(feePreview, {
    "fee preview responds": (r) => r.status === 200 || r.status === 422,
  });

  sleep(0.5 + Math.random());
}
