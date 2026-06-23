import http from "k6/http";
import { check, group, sleep } from "k6";
import { Counter, Rate } from "k6/metrics";

const BASE_URL = __ENV.MONETRA_BASE_URL || "http://localhost:5000";
const TEST_RUN_ID = __ENV.MONETRA_TEST_RUN_ID || `${Date.now()}`;
const STRICT_AI = String(__ENV.MONETRA_STRICT_AI || "false").toLowerCase() === "true";
const THINK_TIME_SECONDS = Number(__ENV.MONETRA_THINK_TIME_SECONDS || "0.2");
const LOAD_PROFILE = String(__ENV.MONETRA_LOAD_PROFILE || "full").toLowerCase();

const profiles = {
  ci: {
    authVus: 2,
    authIterations: 4,
    journeyVus: 2,
    journeyIterations: 4,
    isolationVus: 2,
    isolationIterations: 4,
    readVus: 8,
    readDuration: "15s",
    budgetVus: 3,
    budgetIterations: 8,
    invalidVus: 2,
    invalidIterations: 4,
    aiVus: 1,
    aiIterations: 2,
    thresholds: {
      checks: ["rate>=0.95"],
      monetra_business_failure_rate: ["rate<0.05"],
      monetra_isolation_failure_rate: ["rate==0"],
      monetra_unexpected_status_count: ["count==0"],
      http_req_duration: ["p(95)<10000", "p(99)<20000"],
      "http_req_duration{suite:read-concurrency}": ["p(95)<8000"],
      "http_req_duration{suite:write-concurrency}": ["p(95)<10000"],
    },
  },
  full: {
    authVus: 8,
    authIterations: 24,
    journeyVus: 12,
    journeyIterations: 36,
    isolationVus: 6,
    isolationIterations: 18,
    readVus: 50,
    readDuration: "45s",
    budgetVus: 20,
    budgetIterations: 60,
    invalidVus: 8,
    invalidIterations: 32,
    aiVus: 4,
    aiIterations: 12,
    thresholds: {
      checks: ["rate>=0.97"],
      monetra_business_failure_rate: ["rate<0.01"],
      monetra_isolation_failure_rate: ["rate==0"],
      monetra_unexpected_status_count: ["count==0"],
      http_req_duration: ["p(95)<2500", "p(99)<5000"],
      "http_req_duration{suite:read-concurrency}": ["p(95)<1500"],
      "http_req_duration{suite:write-concurrency}": ["p(95)<2500"],
    },
  },
};

const activeProfile = profiles[LOAD_PROFILE] || profiles.full;

export const options = {
  scenarios: {
    auth_lifecycle: {
      executor: "shared-iterations",
      vus: activeProfile.authVus,
      iterations: activeProfile.authIterations,
      exec: "authLifecycle",
      tags: { suite: "auth" },
    },
    end_to_end_finance_journeys: {
      executor: "shared-iterations",
      vus: activeProfile.journeyVus,
      iterations: activeProfile.journeyIterations,
      exec: "endToEndFinanceJourney",
      tags: { suite: "e2e-finance" },
    },
    user_isolation_probes: {
      executor: "shared-iterations",
      vus: activeProfile.isolationVus,
      iterations: activeProfile.isolationIterations,
      exec: "userIsolationProbe",
      tags: { suite: "isolation" },
    },
    concurrent_dashboard_reads: {
      executor: "constant-vus",
      vus: activeProfile.readVus,
      duration: activeProfile.readDuration,
      exec: "dashboardReadPressure",
      tags: { suite: "read-concurrency" },
    },
    concurrent_budget_updates: {
      executor: "shared-iterations",
      vus: activeProfile.budgetVus,
      iterations: activeProfile.budgetIterations,
      exec: "budgetUpdatePressure",
      tags: { suite: "write-concurrency" },
    },
    invalid_and_security_inputs: {
      executor: "shared-iterations",
      vus: activeProfile.invalidVus,
      iterations: activeProfile.invalidIterations,
      exec: "invalidAndSecurityInputs",
      tags: { suite: "negative-paths" },
    },
    reports_rag_and_agent_resilience: {
      executor: "shared-iterations",
      vus: activeProfile.aiVus,
      iterations: activeProfile.aiIterations,
      exec: "reportsRagAndAgentResilience",
      tags: { suite: "ai-reporting" },
    },
  },
  thresholds: activeProfile.thresholds,
};

const businessFailureRate = new Rate("monetra_business_failure_rate");
const isolationFailureRate = new Rate("monetra_isolation_failure_rate");
const unexpectedStatusCount = new Counter("monetra_unexpected_status_count");

function sleepBriefly() {
  if (THINK_TIME_SECONDS > 0) {
    sleep(THINK_TIME_SECONDS);
  }
}

function uniqueId(prefix) {
  return `${prefix}-${TEST_RUN_ID}-${__VU}-${__ITER}-${Math.random().toString(16).slice(2)}`;
}

function uniqueUser(prefix) {
  const id = uniqueId(prefix).toLowerCase();
  const passwordToken = Math.random().toString(16).slice(2);
  return {
    username: id,
    email: `${id}@monetra.test`,
    password: `LoadTest-${TEST_RUN_ID}-${__VU}-${__ITER}-${passwordToken}-A1!`,
  };
}

function jsonHeaders(cookies) {
  const headers = { "Content-Type": "application/json" };
  const cookie = cookieHeader(cookies);
  if (cookie) {
    headers.Cookie = cookie;
  }
  return headers;
}

function authHeaders(cookies) {
  return { Cookie: cookieHeader(cookies) };
}

function cookieHeader(cookies) {
  return Object.entries(cookies || {})
    .flatMap(([name, values]) => values.map((value) => `${name}=${value.value}`))
    .join("; ");
}

function dataFrom(response, fallback = null) {
  try {
    const parsed = response.json();
    return parsed && Object.prototype.hasOwnProperty.call(parsed, "data") ? parsed.data : parsed;
  } catch (_) {
    return fallback;
  }
}

function request(method, path, body, params, expectedStatuses, label) {
  const response = http.request(method, `${BASE_URL}${path}`, body, params || {});
  const ok = expectedStatuses.includes(response.status);
  const passed = check(response, {
    [`${label} status ${expectedStatuses.join("/")}`]: () => ok,
  });
  if (!passed) {
    unexpectedStatusCount.add(1, { label, status: String(response.status) });
  }
  return response;
}

function registerSession(prefix) {
  const user = uniqueUser(prefix);
  const response = request(
    "POST",
    "/api/auth/register",
    JSON.stringify(user),
    { headers: jsonHeaders() },
    [200, 201],
    "register user",
  );
  const body = dataFrom(response, {});
  check(body, {
    "register returns authenticated user": (data) => Boolean(data && data.authenticated),
    "register returns user id": (data) => Number(data && data.user_id) > 0,
  });
  businessFailureRate.add(!(body && body.authenticated));
  return { user, cookies: response.cookies, userId: body && body.user_id };
}

function loginSession(user) {
  const response = request(
    "POST",
    "/api/auth/login",
    JSON.stringify({ username: user.username, password: user.password }),
    { headers: jsonHeaders() },
    [200],
    "login user",
  );
  const body = dataFrom(response, {});
  check(body, {
    "login returns authenticated session": (data) => Boolean(data && data.authenticated),
  });
  businessFailureRate.add(!(body && body.authenticated));
  return response.cookies;
}

function createExpense(cookies, payload, expectedStatuses = [201]) {
  return request(
    "POST",
    "/api/expenses",
    JSON.stringify(payload),
    { headers: jsonHeaders(cookies) },
    expectedStatuses,
    `create ${payload.entry_type || "expense"} transaction`,
  );
}

function createStandardFinanceData(cookies, marker) {
  createExpense(cookies, {
    date: "2026-05-18",
    category: "Income",
    description: `Salary ${marker}`,
    amount: "2500.00",
    entry_type: "income",
  });
  createExpense(cookies, {
    date: "2026-05-18",
    category: "Groceries",
    description: `Weekly food shop ${marker}`,
    amount: "74.35",
    entry_type: "expense",
  });
  createExpense(cookies, {
    date: "2026-05-19",
    category: "Bills",
    description: `Energy bill ${marker}`,
    amount: "118.20",
    entry_type: "expense",
  });
}

export function authLifecycle() {
  group("auth lifecycle", () => {
    const session = registerSession("auth-user");
    sleepBriefly();

    const sessionCheck = request(
      "GET",
      "/api/auth/session",
      null,
      { headers: authHeaders(session.cookies) },
      [200],
      "current session",
    );
    check(dataFrom(sessionCheck, {}), {
      "session remains authenticated": (data) => Boolean(data && data.authenticated),
    });

    request("POST", "/api/auth/logout", null, { headers: authHeaders(session.cookies) }, [200], "logout");
    const loginCookies = loginSession(session.user);
    request("GET", "/api/dashboard", null, { headers: authHeaders(loginCookies) }, [200], "dashboard after relogin");

    const reset = request(
      "POST",
      "/api/auth/forgot-password",
      JSON.stringify({ username: session.user.username, email: session.user.email }),
      { headers: jsonHeaders() },
      [200],
      "forgot password",
    );
    check(dataFrom(reset, {}), {
      "forgot password returns controlled response": (data) => Boolean(data && data.message),
    });
  });
}

export function endToEndFinanceJourney() {
  group("end-to-end finance journey", () => {
    const session = registerSession("journey-user");
    const marker = uniqueId("journey");
    const cookies = session.cookies;

    createStandardFinanceData(cookies, marker);

    request(
      "PUT",
      "/api/settings/budget",
      JSON.stringify({ monthly_budget: 1400 }),
      { headers: jsonHeaders(cookies) },
      [200],
      "update monthly budget",
    );
    request(
      "PUT",
      "/api/settings/income",
      JSON.stringify({ monthly_income: 2500, month: "2026-05" }),
      { headers: jsonHeaders(cookies) },
      [200],
      "update monthly income",
    );

    const goal = request(
      "POST",
      "/api/savings-goals",
      JSON.stringify({
        name: `Emergency fund ${marker}`,
        target_amount: 3000,
        current_amount: 500,
        target_date: "2026-12-31",
      }),
      { headers: jsonHeaders(cookies) },
      [201],
      "create savings goal",
    );
    const goalData = dataFrom(goal, {});
    if (goalData && goalData.id) {
      request(
        "PUT",
        `/api/savings-goals/${goalData.id}`,
        JSON.stringify({
          name: `Emergency fund ${marker}`,
          target_amount: 3000,
          current_amount: 750,
          target_date: "2026-12-31",
        }),
        { headers: jsonHeaders(cookies) },
        [200],
        "update savings goal",
      );
    } else {
      businessFailureRate.add(1);
    }

    const recurring = request(
      "POST",
      "/api/recurring-items",
      JSON.stringify({
        category: "Bills",
        description: `Broadband ${marker}`,
        amount: 32.5,
        entry_type: "expense",
        frequency: "monthly",
        start_date: "2026-05-20",
        end_date: null,
        active: true,
      }),
      { headers: jsonHeaders(cookies) },
      [201],
      "create recurring item",
    );
    check(dataFrom(recurring, {}), {
      "recurring item has id": (data) => Number(data && data.id) > 0,
    });

    const dashboard = request("GET", "/api/dashboard", null, { headers: authHeaders(cookies) }, [200], "dashboard");
    check(dataFrom(dashboard, {}), {
      "dashboard includes finance totals": (data) => data && Number(data.monthly_income) >= 0 && Number(data.current_month_total) >= 0,
    });

    request("GET", "/api/analytics/categories", null, { headers: authHeaders(cookies) }, [200], "category analytics");
    request("GET", "/api/analytics/financial-pulse", null, { headers: authHeaders(cookies) }, [200], "financial pulse");
    request("GET", "/api/recurring-items/calendar?days=60", null, { headers: authHeaders(cookies) }, [200], "recurring calendar");
    request("GET", "/api/predictions/next-month", null, { headers: authHeaders(cookies) }, [200, 400], "prediction");
    request("GET", "/api/expenses/export", null, { headers: authHeaders(cookies) }, [200], "csv export");
    sleepBriefly();
  });
}

export function userIsolationProbe() {
  group("user data isolation", () => {
    const owner = registerSession("owner-user");
    const outsider = registerSession("outsider-user");
    const marker = uniqueId("private-expense");

    const created = createExpense(owner.cookies, {
      date: "2026-05-21",
      category: "Private",
      description: marker,
      amount: "44.44",
      entry_type: "expense",
    });
    const createdData = dataFrom(created, {});

    const ownerList = request("GET", "/api/expenses", null, { headers: authHeaders(owner.cookies) }, [200], "owner expense list");
    const outsiderList = request("GET", "/api/expenses", null, { headers: authHeaders(outsider.cookies) }, [200], "outsider expense list");
    const ownerExpenses = dataFrom(ownerList, []);
    const outsiderExpenses = dataFrom(outsiderList, []);

    const ownerCanSeeOwnData = Array.isArray(ownerExpenses) && ownerExpenses.some((expense) => expense.description === marker);
    const outsiderCannotSeeData = Array.isArray(outsiderExpenses) && !outsiderExpenses.some((expense) => expense.description === marker);
    const outsiderCannotFetchById = createdData && createdData.id
      ? request("GET", `/api/expenses/${createdData.id}`, null, { headers: authHeaders(outsider.cookies) }, [404], "outsider direct expense fetch").status === 404
      : false;

    check(null, {
      "owner sees own record": () => ownerCanSeeOwnData,
      "outsider cannot list private record": () => outsiderCannotSeeData,
      "outsider cannot fetch private record by id": () => outsiderCannotFetchById,
    });

    isolationFailureRate.add(!(ownerCanSeeOwnData && outsiderCannotSeeData && outsiderCannotFetchById));
  });
}

export function dashboardReadPressure() {
  group("dashboard read pressure", () => {
    const session = registerSession("read-user");
    const headers = authHeaders(session.cookies);
    request("GET", "/api/dashboard", null, { headers }, [200], "dashboard read");
    request("GET", "/api/analytics/categories", null, { headers }, [200], "category read");
    request("GET", "/api/analytics/financial-pulse", null, { headers }, [200], "pulse read");
    sleepBriefly();
  });
}

export function budgetUpdatePressure() {
  group("concurrent budget updates", () => {
    const session = registerSession("budget-user");
    const budget = 900 + ((__VU + __ITER) % 800);
    request(
      "PUT",
      "/api/settings/budget",
      JSON.stringify({ monthly_budget: budget }),
      { headers: jsonHeaders(session.cookies) },
      [200],
      "concurrent budget update",
    );
    const settings = request("GET", "/api/settings?month=2026-05", null, { headers: authHeaders(session.cookies) }, [200], "settings after budget update");
    check(dataFrom(settings, {}), {
      "settings include numeric budget": (data) => data && Number(data.monthly_budget) >= 0,
    });
    sleepBriefly();
  });
}

export function invalidAndSecurityInputs() {
  group("invalid inputs and auth guards", () => {
    const session = registerSession("invalid-user");

    createExpense(session.cookies, {
      date: "not-a-date",
      category: "",
      description: "",
      amount: "not-a-number",
      entry_type: "expense",
    }, [400]);

    request("GET", "/api/dashboard", null, {}, [401], "unauthenticated dashboard blocked");
    request(
      "POST",
      "/api/auth/login",
      JSON.stringify({ username: session.user.username, password: "wrong-password" }),
      { headers: jsonHeaders() },
      [401],
      "wrong password rejected",
    );
    request(
      "POST",
      "/api/savings-goals",
      JSON.stringify({ name: "", target_amount: -1, current_amount: -5, target_date: "bad-date" }),
      { headers: jsonHeaders(session.cookies) },
      [400],
      "invalid savings goal rejected",
    );
    request(
      "POST",
      "/api/recurring-items",
      JSON.stringify({
        category: "",
        description: "",
        amount: -10,
        entry_type: "bad",
        frequency: "hourly",
        start_date: "bad-date",
        active: true,
      }),
      { headers: jsonHeaders(session.cookies) },
      [400],
      "invalid recurring item rejected",
    );
  });
}

export function reportsRagAndAgentResilience() {
  group("reports, RAG, and agent resilience", () => {
    const session = registerSession("ai-user");
    const marker = uniqueId("ai");
    createStandardFinanceData(session.cookies, marker);

    request("GET", "/api/reports/monthly", null, { headers: authHeaders(session.cookies), timeout: "60s" }, [200, 503], "monthly report");

    const ragReindex = request(
      "POST",
      "/api/rag/reindex",
      JSON.stringify({ force: false }),
      { headers: jsonHeaders(session.cookies), timeout: "120s" },
      STRICT_AI ? [200] : [200, 400, 503],
      "rag reindex",
    );
    const ragQuery = request(
      "POST",
      "/api/rag/query",
      JSON.stringify({ question: "Which categories should I reduce spending in this month?" }),
      { headers: jsonHeaders(session.cookies), timeout: "120s" },
      STRICT_AI ? [200] : [200, 400, 503],
      "rag query",
    );
    const agent = request(
      "POST",
      "/api/agents/finance-briefing",
      JSON.stringify({ task: "Prepare a short dummy-user load-test finance briefing." }),
      { headers: jsonHeaders(session.cookies), timeout: "120s" },
      STRICT_AI ? [200, 202] : [200, 202, 503],
      "finance briefing agent",
    );
    request(
      "POST",
      "/api/agents/automation/month-end-email",
      null,
      { headers: authHeaders(session.cookies), timeout: "120s" },
      STRICT_AI ? [200] : [200, 400, 503],
      "manual month-end email dispatch",
    );
    request(
      "POST",
      "/api/agents/automation/upcoming-bills-email",
      null,
      { headers: authHeaders(session.cookies), timeout: "120s" },
      [200, 400, 503],
      "manual upcoming-bills email dispatch",
    );

    if (STRICT_AI) {
      check(ragReindex, { "strict rag reindex succeeded": (res) => res.status === 200 });
      check(ragQuery, { "strict rag query succeeded": (res) => res.status === 200 });
      check(agent, { "strict agent start succeeded": (res) => [200, 202].includes(res.status) });
    }
  });
}
