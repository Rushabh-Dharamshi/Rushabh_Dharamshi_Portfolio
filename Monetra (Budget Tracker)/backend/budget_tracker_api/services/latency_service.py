from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from statistics import mean
from threading import Lock


class LatencyService:
    def __init__(self, repository=None, max_records: int = 500):
        self._repository = repository
        self._records: deque[dict] = deque(maxlen=max(50, int(max_records)))
        self._lock = Lock()

    def record(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: int | None,
        username: str | None,
    ) -> None:
        if not path.startswith("/api/"):
            return
        record = {
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "method": method,
            "path": path,
            "status_code": int(status_code),
            "duration_ms": round(float(duration_ms), 2),
            "user_id": int(user_id) if user_id is not None else None,
            "username": username,
            "ok": 200 <= int(status_code) < 400,
        }
        if self._repository is not None:
            self._repository.create_record(
                {
                    "request_id": record["request_id"],
                    "created_at": record["timestamp"],
                    "method": record["method"],
                    "path": record["path"],
                    "status_code": record["status_code"],
                    "duration_ms": record["duration_ms"],
                    "user_id": record["user_id"],
                    "username_snapshot": record["username"],
                    "ok": record["ok"],
                }
            )
            return
        with self._lock:
            self._records.append(record)

    def report_for_user(self, user_id: int | None, limit: int = 50) -> dict:
        try:
            safe_limit = max(1, min(int(limit), 100))
        except (TypeError, ValueError):
            safe_limit = 50
        if self._repository is not None:
            latest = self._repository.list_records_for_user(user_id, safe_limit)
            latest_failures = self._repository.list_failures_for_user(user_id, min(safe_limit, 20))
            durations = self._repository.list_durations_for_user(user_id)
            return {
                "scope": "current_user" if user_id is not None else "anonymous",
                "record_count": self._repository.count_records_for_user(user_id),
                "failed_count": self._repository.count_failures_for_user(user_id),
                "summary": self._summary(durations),
                "by_endpoint": self._repository.endpoint_summary_for_user(user_id),
                "latest_failures": latest_failures,
                "latest": latest,
            }
        with self._lock:
            if user_id is None:
                records = [record for record in self._records if record.get("user_id") is None]
            else:
                records = [record for record in self._records if record.get("user_id") == int(user_id)]
        latest = list(reversed(records[-safe_limit:]))
        latest_failures = list(reversed([record for record in records if not record.get("ok")][-min(safe_limit, 20):]))
        successful_durations = [float(record["duration_ms"]) for record in records if record.get("ok")]
        failed_count = len([record for record in records if not record.get("ok")])
        return {
            "scope": "current_user" if user_id is not None else "anonymous",
            "record_count": len(records),
            "failed_count": failed_count,
            "summary": self._summary(successful_durations),
            "by_endpoint": self._endpoint_summary(records),
            "latest_failures": latest_failures,
            "latest": latest,
        }

    @staticmethod
    def _summary(durations: list[float]) -> dict:
        if not durations:
            return {
                "average_ms": 0.0,
                "minimum_ms": 0.0,
                "maximum_ms": 0.0,
                "p95_ms": 0.0,
            }
        sorted_values = sorted(durations)
        return {
            "average_ms": round(mean(sorted_values), 2),
            "minimum_ms": round(sorted_values[0], 2),
            "maximum_ms": round(sorted_values[-1], 2),
            "p95_ms": round(LatencyService._percentile(sorted_values, 95), 2),
        }

    @staticmethod
    def _percentile(sorted_values: list[float], percentile: int) -> float:
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]
        rank = (len(sorted_values) - 1) * (percentile / 100)
        lower = int(rank)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = rank - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    @staticmethod
    def _endpoint_summary(records: list[dict], limit: int = 12) -> list[dict]:
        grouped: dict[tuple[str, str], list[dict]] = {}
        for record in records:
            key = (record["method"], record["path"])
            grouped.setdefault(key, []).append(record)
        summaries = []
        for (method, path), endpoint_records in grouped.items():
            durations = [float(record["duration_ms"]) for record in endpoint_records if record.get("ok")]
            summaries.append(
                {
                    "method": method,
                    "path": path,
                    "request_count": len(endpoint_records),
                    "failed_count": len([record for record in endpoint_records if not record.get("ok")]),
                    "average_ms": round(mean(durations), 2) if durations else 0.0,
                    "maximum_ms": round(max(durations), 2) if durations else 0.0,
                }
            )
        return sorted(summaries, key=lambda item: (-item["request_count"], -item["maximum_ms"]))[:limit]
