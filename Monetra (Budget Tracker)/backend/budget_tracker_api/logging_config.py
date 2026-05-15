import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, g, request


class TimezoneFormatter(logging.Formatter):
    def __init__(self, fmt: str, timezone_name: str):
        super().__init__(fmt)
        try:
            self._timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            self._timezone = ZoneInfo("UTC")

    def formatTime(self, record, datefmt=None):  # noqa: N802
        timestamp = datetime.fromtimestamp(record.created, self._timezone)
        if datefmt:
            return timestamp.strftime(datefmt)
        return f"{timestamp:%Y-%m-%d %H:%M:%S},{int(timestamp.microsecond / 1000):03d}"


def configure_logging(app: Flask) -> None:
    log_level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_file = Path(app.config["LOG_FILE_PATH"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = TimezoneFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        str(app.config.get("LOG_TIMEZONE", "Europe/London")),
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(app.config.get("LOG_MAX_BYTES", 1_048_576)),
        backupCount=int(app.config.get("LOG_BACKUP_COUNT", 3)),
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("werkzeug").setLevel(log_level)
    app.logger.setLevel(log_level)
    app.logger.info("Logging configured at %s. Writing to %s", log_level_name, log_file)


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def start_request_timer():
        g.request_started_at = perf_counter()
        app.logger.info(
            "Request started | method=%s path=%s remote=%s",
            request.method,
            request.path,
            request.remote_addr,
        )

    @app.after_request
    def log_request_response(response):
        started_at = getattr(g, "request_started_at", None)
        duration_seconds = 0.0 if started_at is None else perf_counter() - started_at
        duration_ms = duration_seconds * 1000
        app.logger.info(
            "Request completed | method=%s path=%s status=%s duration_seconds=%.3f duration_ms=%.1f",
            request.method,
            request.path,
            response.status_code,
            duration_seconds,
            duration_ms,
        )
        return response
