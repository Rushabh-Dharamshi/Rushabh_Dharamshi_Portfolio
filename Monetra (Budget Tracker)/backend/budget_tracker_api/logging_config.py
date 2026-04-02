import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter

from flask import Flask, g, request


def configure_logging(app: Flask) -> None:
    log_level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_file = Path(app.config["LOG_FILE_PATH"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
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
        duration_ms = 0.0 if started_at is None else (perf_counter() - started_at) * 1000
        app.logger.info(
            "Request completed | method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response
