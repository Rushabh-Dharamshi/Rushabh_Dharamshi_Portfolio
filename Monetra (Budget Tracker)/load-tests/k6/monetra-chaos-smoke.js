import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    checks: ["rate>0.80"],
  },
};

const BASE_URL = __ENV.MONETRA_BASE_URL || "http://localhost:5000";

export default function () {
  const health = http.get(`${BASE_URL}/api/health`);
  check(health, { "health endpoint responds": (res) => [200, 500, 503].includes(res.status) });

  const unauthenticatedDashboard = http.get(`${BASE_URL}/api/dashboard`);
  check(unauthenticatedDashboard, {
    "protected endpoint remains protected or service fails cleanly": (res) => [401, 500, 503].includes(res.status),
  });

  const invalidLogin = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({ username: "chaos-user", password: "wrong-password" }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(invalidLogin, { "invalid login rejected": (res) => [401, 500, 503].includes(res.status) });
}
