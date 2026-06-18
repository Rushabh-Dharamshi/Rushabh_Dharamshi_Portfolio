import logging

from flask import Flask

from budget_tracker_api.logging_config import register_request_logging
from budget_tracker_api.logging_config import TimezoneFormatter


def test_timezone_formatter_uses_configured_timezone():
    formatter = TimezoneFormatter("%(asctime)s", "Europe/London")
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "message",
        (),
        None,
    )
    record.created = 1778054700.0

    assert formatter.formatTime(record).startswith("2026-05-06 09:05:00")


def test_timezone_formatter_falls_back_to_utc_for_invalid_timezone():
    formatter = TimezoneFormatter("%(asctime)s", "Invalid/Timezone")
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "message",
        (),
        None,
    )
    record.created = 1778054700.0

    assert formatter.formatTime(record).startswith("2026-05-06 08:05:00")


def test_timezone_formatter_honors_explicit_date_format():
    formatter = TimezoneFormatter("%(asctime)s", "Europe/London")
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "message",
        (),
        None,
    )
    record.created = 1778054700.0

    assert formatter.formatTime(record, "%Y/%m/%d %H:%M") == "2026/05/06 09:05"


def test_request_logging_continues_when_latency_recording_fails(caplog):
    class BrokenLatencyService:
        def record(self, **payload):
            raise RuntimeError("database unavailable")

    app = Flask(__name__)
    app.extensions = {"services": {"latency_service": BrokenLatencyService()}}
    app.logger.setLevel(logging.INFO)
    register_request_logging(app)

    @app.get("/api/example")
    def example():
        return {"ok": True}

    with caplog.at_level(logging.ERROR):
        response = app.test_client().get("/api/example")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "Latency record persistence failed" in caplog.text
