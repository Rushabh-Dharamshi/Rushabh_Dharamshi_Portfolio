from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import case, func, insert, select
from sqlalchemy.engine import Connection

from budget_tracker_api.db import api_latency_records_table


class LatencyRepository:
    def __init__(self, connection_factory: Callable[[], Connection]):
        self._connection_factory = connection_factory

    def _db(self) -> Connection:
        return self._connection_factory()

    def create_record(self, payload: dict) -> None:
        db = self._db()
        db.execute(insert(api_latency_records_table).values(**payload))
        db.commit()

    def list_records_for_user(self, user_id: int | None, limit: int = 50) -> list[dict]:
        safe_limit = self._safe_limit(limit)
        query = select(api_latency_records_table)
        if user_id is None:
            query = query.where(api_latency_records_table.c.user_id.is_(None))
        else:
            query = query.where(api_latency_records_table.c.user_id == int(user_id))
        rows = (
            self._db()
            .execute(
                query.order_by(
                    api_latency_records_table.c.created_at.desc(),
                    api_latency_records_table.c.id.desc(),
                ).limit(safe_limit)
            )
            .mappings()
            .all()
        )
        return [self._deserialize(row) for row in rows]

    def list_failures_for_user(self, user_id: int | None, limit: int = 10) -> list[dict]:
        safe_limit = self._safe_limit(limit)
        query = select(api_latency_records_table).where(api_latency_records_table.c.ok.is_(False))
        if user_id is None:
            query = query.where(api_latency_records_table.c.user_id.is_(None))
        else:
            query = query.where(api_latency_records_table.c.user_id == int(user_id))
        rows = (
            self._db()
            .execute(
                query.order_by(
                    api_latency_records_table.c.created_at.desc(),
                    api_latency_records_table.c.id.desc(),
                ).limit(safe_limit)
            )
            .mappings()
            .all()
        )
        return [self._deserialize(row) for row in rows]

    def list_durations_for_user(self, user_id: int | None) -> list[float]:
        query = select(api_latency_records_table.c.duration_ms).where(api_latency_records_table.c.ok.is_(True))
        if user_id is None:
            query = query.where(api_latency_records_table.c.user_id.is_(None))
        else:
            query = query.where(api_latency_records_table.c.user_id == int(user_id))
        return [float(row[0] or 0.0) for row in self._db().execute(query).all()]

    def count_records_for_user(self, user_id: int | None) -> int:
        query = select(func.count()).select_from(api_latency_records_table)
        if user_id is None:
            query = query.where(api_latency_records_table.c.user_id.is_(None))
        else:
            query = query.where(api_latency_records_table.c.user_id == int(user_id))
        return int(self._db().execute(query).scalar_one() or 0)

    def count_failures_for_user(self, user_id: int | None) -> int:
        query = select(func.count()).select_from(api_latency_records_table).where(api_latency_records_table.c.ok.is_(False))
        if user_id is None:
            query = query.where(api_latency_records_table.c.user_id.is_(None))
        else:
            query = query.where(api_latency_records_table.c.user_id == int(user_id))
        return int(self._db().execute(query).scalar_one() or 0)

    def endpoint_summary_for_user(self, user_id: int | None, limit: int = 12) -> list[dict]:
        safe_limit = self._safe_limit(limit)
        failed_count = func.sum(case((api_latency_records_table.c.ok.is_(False), 1), else_=0))
        query = select(
            api_latency_records_table.c.method,
            api_latency_records_table.c.path,
            func.count().label("request_count"),
            failed_count.label("failed_count"),
            func.avg(api_latency_records_table.c.duration_ms).label("average_ms"),
            func.max(api_latency_records_table.c.duration_ms).label("maximum_ms"),
        )
        if user_id is None:
            query = query.where(api_latency_records_table.c.user_id.is_(None))
        else:
            query = query.where(api_latency_records_table.c.user_id == int(user_id))
        rows = (
            self._db()
            .execute(
                query.group_by(api_latency_records_table.c.method, api_latency_records_table.c.path)
                .order_by(func.count().desc(), func.max(api_latency_records_table.c.duration_ms).desc())
                .limit(safe_limit)
            )
            .mappings()
            .all()
        )
        return [
            {
                "method": row["method"],
                "path": row["path"],
                "request_count": int(row["request_count"] or 0),
                "failed_count": int(row["failed_count"] or 0),
                "average_ms": round(float(row["average_ms"] or 0.0), 2),
                "maximum_ms": round(float(row["maximum_ms"] or 0.0), 2),
            }
            for row in rows
        ]

    @staticmethod
    def _safe_limit(limit: int) -> int:
        try:
            return max(1, min(int(limit), 100))
        except (TypeError, ValueError):
            return 50

    @staticmethod
    def _deserialize(row) -> dict:
        return {
            "request_id": row["request_id"],
            "timestamp": row["created_at"],
            "method": row["method"],
            "path": row["path"],
            "status_code": int(row["status_code"]),
            "duration_ms": round(float(row["duration_ms"]), 2),
            "user_id": int(row["user_id"]) if row["user_id"] is not None else None,
            "username": row["username_snapshot"],
            "ok": bool(row["ok"]),
        }
