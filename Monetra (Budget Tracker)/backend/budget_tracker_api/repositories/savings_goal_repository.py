from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection

from budget_tracker_api.db import savings_goals_table


class SavingsGoalRepository:
    def __init__(self, connection_factory: Callable[[], Connection], user_id_provider: Callable[[], int] | None = None):
        self._connection_factory = connection_factory
        self._user_id_provider = user_id_provider or (lambda: 1)

    def _db(self) -> Connection:
        return self._connection_factory()

    def _user_id(self) -> int:
        return int(self._user_id_provider() or 1)

    def list_goals(self) -> list[dict]:
        rows = self._db().execute(
            select(savings_goals_table)
            .where(savings_goals_table.c.user_id == self._user_id())
            .order_by(savings_goals_table.c.created_at.desc(), savings_goals_table.c.id.desc())
        ).mappings().all()
        return [self._row_to_dict(row) for row in rows]

    def get_goal(self, goal_id: int) -> dict | None:
        row = self._db().execute(
            select(savings_goals_table).where(
                savings_goals_table.c.id == goal_id,
                savings_goals_table.c.user_id == self._user_id(),
            )
        ).mappings().first()
        return self._row_to_dict(row) if row else None

    def create_goal(self, payload: dict) -> dict:
        db = self._db()
        result = db.execute(
            insert(savings_goals_table).values(**self._coerce_payload(payload), user_id=self._user_id())
        )
        db.commit()
        return self.get_goal(int(result.inserted_primary_key[0]))

    def update_goal(self, goal_id: int, payload: dict) -> dict | None:
        db = self._db()
        result = db.execute(
            update(savings_goals_table)
            .where(savings_goals_table.c.id == goal_id, savings_goals_table.c.user_id == self._user_id())
            .values(**self._coerce_payload(payload, include_created_at=False))
        )
        db.commit()
        if result.rowcount == 0:
            return None
        return self.get_goal(goal_id)

    def delete_goal(self, goal_id: int) -> bool:
        db = self._db()
        result = db.execute(
            delete(savings_goals_table).where(
                savings_goals_table.c.id == goal_id,
                savings_goals_table.c.user_id == self._user_id(),
            )
        )
        db.commit()
        return result.rowcount > 0

    @classmethod
    def _coerce_payload(cls, payload: dict, include_created_at: bool = True) -> dict:
        target_date = payload.get("target_date")
        data = {
            "name": payload["name"],
            "target_amount": round(float(payload["target_amount"]), 2),
            "current_amount": round(float(payload.get("current_amount", 0)), 2),
            "target_date": cls._parse_date(target_date) if target_date else None,
        }
        if include_created_at:
            data["created_at"] = datetime.now().isoformat(timespec="seconds")
        return data

    @staticmethod
    def _parse_date(raw_date: str) -> date:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()

    @staticmethod
    def _row_to_dict(row) -> dict:
        target_date = row["target_date"]
        target_amount = float(row["target_amount"])
        current_amount = float(row["current_amount"])
        progress_percent = (current_amount / target_amount * 100) if target_amount else 0.0
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "target_amount": round(target_amount, 2),
            "current_amount": round(current_amount, 2),
            "remaining_amount": round(max(target_amount - current_amount, 0.0), 2),
            "progress_percent": round(min(max(progress_percent, 0.0), 100.0), 2),
            "target_date": target_date.isoformat() if isinstance(target_date, date) else (str(target_date) if target_date else None),
            "created_at": row["created_at"],
        }
