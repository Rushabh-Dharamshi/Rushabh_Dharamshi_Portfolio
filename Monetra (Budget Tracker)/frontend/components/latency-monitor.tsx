import { LatencyReportResponse } from "@/lib/types";

interface LatencyMonitorProps {
  report: LatencyReportResponse | null;
  onRefresh: () => Promise<void> | void;
}

function formatMs(value: number | undefined) {
  return `${Number(value ?? 0).toFixed(1)} ms`;
}

export function endpointPurpose(method: string, path: string) {
  if (method === "CLIENT" || path.startsWith("/api/client-operations/")) {
    const operation = path.replace("/api/client-operations/", "").replaceAll("-", " ");
    return `User-visible operation failure recorded by the app: ${operation || "client operation"}. Status 599 means the operation failed from the user's point of view, not necessarily that Flask returned HTTP 500.`;
  }
  if (path === "/api/observability/latency") {
    return "Refreshes this latency monitor. High call counts here usually come from automatic monitor polling.";
  }
  if (/^\/api\/agents\/finance-briefing\/[^/]+$/.test(path)) {
    return "Polls an Ollama operations-agent job until the finance briefing or command finishes.";
  }
  if (path === "/api/agents/finance-briefing") {
    return "Starts an Ollama operations-agent briefing or command job.";
  }
  if (/^\/api\/agents\/workflow-jobs\/[^/]+$/.test(path)) {
    return "Polls an Automation Center workflow job until it completes or fails.";
  }
  if (path === "/api/agents/workflows") {
    return "Loads the Automation Center workflow definitions.";
  }
  if (path === "/api/agents/runs") {
    return "Loads saved automation history and latest workflow outputs.";
  }
  if (path.startsWith("/api/rag/")) {
    return "Runs or monitors the RAG assistant knowledge-base query/reindex flow.";
  }
  if (path === "/api/dashboard") {
    return "Loads Budget Overview KPI totals such as income, expenses, cash flow, and remaining budget.";
  }
  if (path.startsWith("/api/analytics/")) {
    return "Loads dashboard analytics such as category insights, word cloud data, or financial pulse metrics.";
  }
  if (path.startsWith("/api/expenses")) {
    return "Reads or changes transaction records, including CSV import/export.";
  }
  if (path.startsWith("/api/recurring-items")) {
    return "Reads or changes recurring reminders, paid occurrence links, and upcoming/late reminder schedules.";
  }
  if (path.startsWith("/api/reports/monthly")) {
    return "Generates or downloads the monthly PDF finance report.";
  }
  if (path.startsWith("/api/settings")) {
    return "Reads or saves monthly budget and monthly income settings.";
  }
  if (path.startsWith("/api/auth")) {
    return "Handles sign in, sign out, registration, account deletion, password reset, or mock inbox access.";
  }
  return "Backend API call used by the current Monetra screen or workflow.";
}

export function shortStatusMeaning(record: { method: string; status_code: number; ok: boolean }) {
  if (record.method === "CLIENT" && record.status_code === 599) {
    return "Client-visible operation failure";
  }
  if (record.ok) {
    return "Successful backend response";
  }
  if (record.status_code >= 500) {
    return "Backend/server-side failure";
  }
  if (record.status_code >= 400) {
    return "Request was rejected or invalid";
  }
  return "Failed request";
}

export function LatencyMonitor({ report, onRefresh }: LatencyMonitorProps) {
  const latest = report?.latest ?? [];
  const latestFailures = report?.latest_failures ?? [];
  const endpoints = report?.by_endpoint ?? [];

  return (
    <section className="panel latency-monitor-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">API latency monitor</p>
          <h2>Live request timings</h2>
          <p className="section-copy">
            Recent API calls and user-visible operation failures for this signed-in user. Backend requests are logged automatically; failed agent, workflow, and email operations are also counted so the failure total matches what you see in the app.
          </p>
        </div>
        <button className="button button-ghost" type="button" onClick={() => void onRefresh()}>
          Refresh
        </button>
      </div>

      <div className="latency-summary-grid">
        <article>
          <span>Average</span>
          <strong>{formatMs(report?.summary.average_ms)}</strong>
        </article>
        <article>
          <span>P95</span>
          <strong>{formatMs(report?.summary.p95_ms)}</strong>
        </article>
        <article>
          <span>Max</span>
          <strong>{formatMs(report?.summary.maximum_ms)}</strong>
        </article>
        <article>
          <span>Failures</span>
          <strong>{report?.failed_count ?? 0}</strong>
        </article>
      </div>

      <div className="latency-record-list">
        {latestFailures.length ? (
          <section className="latency-failure-section" aria-label="Recent latency failures">
            <div className="latency-subheading">
              <strong>Recent failures</strong>
              <span>Newest failed operations first, even if successful polling calls happened later.</span>
            </div>
            {latestFailures.map((record) => (
              <article className="latency-record latency-record-failed" key={`failure-${record.request_id}`}>
                <div>
                  <strong>{record.method} {record.path}</strong>
                  <span>{endpointPurpose(record.method, record.path)}</span>
                  <span>{new Date(record.timestamp).toLocaleString()} | {record.request_id.slice(0, 8)} | {shortStatusMeaning(record)}</span>
                </div>
                <div className="latency-record-metrics">
                  <span className="status-over">{record.status_code}</span>
                  <strong>{formatMs(record.duration_ms)}</strong>
                </div>
              </article>
            ))}
          </section>
        ) : report?.failed_count ? (
          <section className="latency-failure-section" aria-label="Recent latency failures">
            <div className="latency-subheading">
              <strong>Recent failures</strong>
              <span>Failures exist in this user scope, but none were returned in the current failure window. Refresh or increase the report limit.</span>
            </div>
          </section>
        ) : null}

        {endpoints.length ? (
          <section className="latency-endpoint-summary" aria-label="Latency by API endpoint">
            <div className="latency-subheading">
              <strong>Endpoint summary</strong>
              <span>Grouped by API route. Polling endpoints can have high call counts because they check job status repeatedly.</span>
            </div>
            {endpoints.slice(0, 6).map((endpoint) => (
              <article className="latency-endpoint-card" key={`${endpoint.method}:${endpoint.path}`}>
                <div>
                  <strong>{endpoint.method} {endpoint.path}</strong>
                  <span>{endpointPurpose(endpoint.method, endpoint.path)}</span>
                  <span>{endpoint.request_count} calls | {endpoint.failed_count} failures</span>
                </div>
                <div className="latency-record-metrics">
                  <span>avg {formatMs(endpoint.average_ms)}</span>
                  <strong>max {formatMs(endpoint.maximum_ms)}</strong>
                </div>
              </article>
            ))}
          </section>
        ) : null}

        {latest.length ? (
          <section className="latency-latest-section" aria-label="Latest latency records">
            <div className="latency-subheading">
              <strong>Latest requests</strong>
              <span>Most recent records, including successful polling calls.</span>
            </div>
            {latest.slice(0, 10).map((record) => (
              <article className="latency-record" key={record.request_id}>
                <div>
                  <strong>{record.method} {record.path}</strong>
                  <span>{endpointPurpose(record.method, record.path)}</span>
                  <span>{new Date(record.timestamp).toLocaleString()} | {record.request_id.slice(0, 8)} | {shortStatusMeaning(record)}</span>
                </div>
                <div className="latency-record-metrics">
                  <span className={record.ok ? "status-within" : "status-over"}>{record.status_code}</span>
                  <strong>{formatMs(record.duration_ms)}</strong>
                </div>
              </article>
            ))}
          </section>
        ) : (
          <p className="muted">Use the app and recent API timings will appear here.</p>
        )}
      </div>
    </section>
  );
}
