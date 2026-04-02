from __future__ import annotations

import logging
from datetime import datetime, timedelta
from threading import Event, Thread

logger = logging.getLogger(__name__)


class AutomationScheduler:
    def __init__(self, app, poll_seconds: int = 900):
        self._app = app
        self._poll_seconds = max(60, int(poll_seconds))
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._next_realtime_run_at: datetime | None = None
        self._last_month_end_minute_key: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run_loop, name="monetra-automation-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        self._next_realtime_run_at = datetime.now()
        while not self._stop_event.is_set():
            now = datetime.now()
            try:
                with self._app.app_context():
                    automation_service = self._app.extensions["services"].get("automation_service")
                    if automation_service is not None:
                        if self._should_run_realtime(now):
                            automation_service.run_upcoming_bills_email_if_due()
                            self._next_realtime_run_at = now + timedelta(seconds=self._poll_seconds)
                        if self._should_run_month_end_minute(now):
                            automation_service.run_month_end_email_if_due()
            except Exception:
                logger.exception("Automation scheduler loop failed.")

            if self._stop_event.wait(self._seconds_until_next_wake(datetime.now())):
                break

    def _should_run_realtime(self, now: datetime) -> bool:
        if self._next_realtime_run_at is None:
            return True
        return now >= self._next_realtime_run_at

    def _should_run_month_end_minute(self, now: datetime) -> bool:
        minute_key = now.strftime("%Y-%m-%dT%H:%M")
        if minute_key == self._last_month_end_minute_key:
            return False
        self._last_month_end_minute_key = minute_key
        return True

    def _seconds_until_next_wake(self, now: datetime) -> float:
        next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1) - now).total_seconds()
        if self._next_realtime_run_at is None:
            return max(1.0, next_minute)
        realtime_wait = max(0.0, (self._next_realtime_run_at - now).total_seconds())
        return max(1.0, min(next_minute, realtime_wait))
