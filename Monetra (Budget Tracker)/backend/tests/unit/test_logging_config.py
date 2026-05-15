import logging

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
