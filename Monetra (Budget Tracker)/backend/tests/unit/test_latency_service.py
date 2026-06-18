from budget_tracker_api.services.latency_service import LatencyService


def test_latency_service_reports_user_scoped_summary():
    service = LatencyService(max_records=10)
    service.record(
        request_id="req-1",
        method="GET",
        path="/api/dashboard",
        status_code=200,
        duration_ms=20.0,
        user_id=7,
        username="Demo",
    )
    service.record(
        request_id="req-2",
        method="POST",
        path="/api/expenses",
        status_code=201,
        duration_ms=40.0,
        user_id=7,
        username="Demo",
    )
    service.record(
        request_id="req-3",
        method="GET",
        path="/api/dashboard",
        status_code=500,
        duration_ms=80.0,
        user_id=8,
        username="Other",
    )

    report = service.report_for_user(7)

    assert report["scope"] == "current_user"
    assert report["record_count"] == 2
    assert report["failed_count"] == 0
    assert report["summary"]["average_ms"] == 30.0
    assert report["summary"]["minimum_ms"] == 20.0
    assert report["summary"]["maximum_ms"] == 40.0
    assert report["by_endpoint"] == [
        {
            "method": "POST",
            "path": "/api/expenses",
            "request_count": 1,
            "failed_count": 0,
            "average_ms": 40.0,
            "maximum_ms": 40.0,
        },
        {
            "method": "GET",
            "path": "/api/dashboard",
            "request_count": 1,
            "failed_count": 0,
            "average_ms": 20.0,
            "maximum_ms": 20.0,
        },
    ]
    assert report["latest_failures"] == []
    assert report["latest"][0]["request_id"] == "req-2"
    assert report["latest"][1]["request_id"] == "req-1"


def test_latency_service_reports_recent_failures_separately():
    service = LatencyService(max_records=10)
    service.record(
        request_id="ok-1",
        method="GET",
        path="/api/observability/latency",
        status_code=200,
        duration_ms=25.0,
        user_id=7,
        username="Demo",
    )
    service.record(
        request_id="fail-1",
        method="CLIENT",
        path="/api/client-operations/ai-agent-request",
        status_code=599,
        duration_ms=27410.4,
        user_id=7,
        username="Demo",
    )
    service.record(
        request_id="ok-2",
        method="GET",
        path="/api/agents/finance-briefing/job-1",
        status_code=200,
        duration_ms=1.0,
        user_id=7,
        username="Demo",
    )

    report = service.report_for_user(7)

    assert report["record_count"] == 3
    assert report["failed_count"] == 1
    assert report["latest"][0]["request_id"] == "ok-2"
    assert report["latest_failures"] == [
        {
            "request_id": "fail-1",
            "timestamp": report["latest_failures"][0]["timestamp"],
            "method": "CLIENT",
            "path": "/api/client-operations/ai-agent-request",
            "status_code": 599,
            "duration_ms": 27410.4,
            "user_id": 7,
            "username": "Demo",
            "ok": False,
        }
    ]


def test_latency_service_ignores_non_api_paths():
    service = LatencyService()
    service.record(
        request_id="asset",
        method="GET",
        path="/favicon.ico",
        status_code=200,
        duration_ms=5.0,
        user_id=None,
        username=None,
    )

    assert service.report_for_user(None)["record_count"] == 0
