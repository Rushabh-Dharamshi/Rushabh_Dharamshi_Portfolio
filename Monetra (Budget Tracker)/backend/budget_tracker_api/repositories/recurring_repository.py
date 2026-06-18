from collections.abc import Callable
from datetime import UTC, date, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection

from budget_tracker_api.db import recurring_items_table, recurring_occurrence_status_table


class RecurringRepository:
    def __init__(self, connection_factory: Callable[[], Connection], user_id_provider: Callable[[], int] | None = None):
        self._connection_factory = connection_factory
        self._user_id_provider = user_id_provider or (lambda: 1)

    def _db(self) -> Connection:
        return self._connection_factory()

    def _user_id(self) -> int:
        return int(self._user_id_provider() or 1)

    def list_items(self) -> list[dict]:
        rows = self._db().execute(
            select(recurring_items_table).where(
                recurring_items_table.c.user_id == self._user_id()
            ).order_by(
                recurring_items_table.c.active.desc(),
                recurring_items_table.c.start_date.asc(),
                recurring_items_table.c.id.asc(),
            )
        ).mappings().all()
        return [self._row_to_dict(row) for row in rows]

    def get_item(self, item_id: int) -> dict | None:
        row = self._db().execute(
            select(recurring_items_table).where(
                recurring_items_table.c.id == item_id,
                recurring_items_table.c.user_id == self._user_id(),
            )
        ).mappings().first()
        return self._row_to_dict(row) if row else None

    def create_item(self, payload: dict) -> dict:
        db = self._db()
        result = db.execute(
            insert(recurring_items_table).values(**self._coerce_payload(payload), user_id=self._user_id())
        )
        db.commit()
        return self.get_item(int(result.inserted_primary_key[0]))

    def update_item(self, item_id: int, payload: dict) -> dict | None:
        db = self._db()
        result = db.execute(
            update(recurring_items_table)
            .where(recurring_items_table.c.id == item_id, recurring_items_table.c.user_id == self._user_id())
            .values(**self._coerce_payload(payload))
        )
        db.commit()
        if result.rowcount == 0:
            return None
        return self.get_item(item_id)

    def delete_item(self, item_id: int) -> bool:
        db = self._db()
        db.execute(
            delete(recurring_occurrence_status_table).where(
                recurring_occurrence_status_table.c.recurring_item_id == item_id,
                recurring_occurrence_status_table.c.user_id == self._user_id(),
            )
        )
        result = db.execute(
            delete(recurring_items_table).where(
                recurring_items_table.c.id == item_id,
                recurring_items_table.c.user_id == self._user_id(),
            )
        )
        db.commit()
        return result.rowcount > 0

    def paid_occurrences_for_range(self, window_start: str, window_end: str) -> set[tuple[int, str]]:
        rows = self._db().execute(
            select(
                recurring_occurrence_status_table.c.recurring_item_id,
                recurring_occurrence_status_table.c.occurrence_date,
            ).where(
                recurring_occurrence_status_table.c.user_id == self._user_id(),
                recurring_occurrence_status_table.c.occurrence_date >= self._parse_date(window_start),
                recurring_occurrence_status_table.c.occurrence_date <= self._parse_date(window_end),
                recurring_occurrence_status_table.c.is_paid.is_(True),
            )
        ).all()
        return {
            (int(row[0]), row[1].isoformat() if isinstance(row[1], date) else str(row[1]))
            for row in rows
        }

    def paid_occurrence_entries_for_range(self, window_start: str, window_end: str) -> list[dict]:
        rows = self._db().execute(
            select(recurring_occurrence_status_table).where(
                recurring_occurrence_status_table.c.user_id == self._user_id(),
                recurring_occurrence_status_table.c.occurrence_date >= self._parse_date(window_start),
                recurring_occurrence_status_table.c.occurrence_date <= self._parse_date(window_end),
                recurring_occurrence_status_table.c.is_paid.is_(True),
            )
        ).mappings().all()
        return [self._status_row_to_dict(row) for row in rows]

    def get_paid_occurrence_by_transaction_id(self, transaction_id: int) -> dict | None:
        row = self._db().execute(
            select(recurring_occurrence_status_table).where(
                recurring_occurrence_status_table.c.user_id == self._user_id(),
                recurring_occurrence_status_table.c.transaction_id == transaction_id,
                recurring_occurrence_status_table.c.is_paid.is_(True),
            )
        ).mappings().first()
        return self._status_row_to_dict(row) if row else None

    def mark_occurrence_paid(self, item_id: int, occurrence_date: str, transaction_id: int) -> dict:
        return self._upsert_occurrence_status(item_id, occurrence_date, True, transaction_id)

    def mark_occurrence_unpaid(self, item_id: int, occurrence_date: str) -> dict:
        return self._upsert_occurrence_status(item_id, occurrence_date, False, None)

    def _upsert_occurrence_status(
        self,
        item_id: int,
        occurrence_date: str,
        is_paid: bool,
        transaction_id: int | None,
    ) -> dict:
        db = self._db()
        parsed_date = self._parse_date(occurrence_date)
        timestamp = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        existing = db.execute(
            select(recurring_occurrence_status_table).where(
                recurring_occurrence_status_table.c.user_id == self._user_id(),
                recurring_occurrence_status_table.c.recurring_item_id == item_id,
                recurring_occurrence_status_table.c.occurrence_date == parsed_date,
            )
        ).mappings().first()

        values = {
            "is_paid": is_paid,
            "transaction_id": transaction_id if is_paid else None,
            "updated_at": timestamp,
        }

        if existing:
            db.execute(
                update(recurring_occurrence_status_table)
                .where(recurring_occurrence_status_table.c.id == existing["id"])
                .values(**values)
            )
        else:
            db.execute(
                insert(recurring_occurrence_status_table).values(
                    user_id=self._user_id(),
                    recurring_item_id=item_id,
                    occurrence_date=parsed_date,
                    **values,
                )
            )
        db.commit()
        return {
            "recurring_item_id": item_id,
            "occurrence_date": occurrence_date,
            "is_paid": is_paid,
            "transaction_id": transaction_id if is_paid else None,
            "updated_at": timestamp,
        }

    @classmethod
    def _coerce_payload(cls, payload: dict) -> dict:
        end_date = payload.get("end_date")
        return {
            "category": payload["category"],
            "description": payload["description"],
            "amount": round(float(payload["amount"]), 2),
            "entry_type": payload["entry_type"],
            "frequency": payload["frequency"],
            "start_date": cls._parse_date(payload["start_date"]),
            "end_date": cls._parse_date(end_date) if end_date else None,
            "active": bool(payload.get("active", True)),
        }

    @staticmethod
    def _parse_date(raw_date: str) -> date:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()

    @staticmethod
    def _status_row_to_dict(row) -> dict:
        return {
            "recurring_item_id": int(row["recurring_item_id"]),
            "occurrence_date": (
                row["occurrence_date"].isoformat()
                if isinstance(row["occurrence_date"], date)
                else str(row["occurrence_date"])
            ),
            "transaction_id": int(row["transaction_id"]) if row.get("transaction_id") is not None else None,
            "is_paid": bool(row["is_paid"]),
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_dict(row) -> dict:
        start_date = row["start_date"]
        end_date = row.get("end_date") if hasattr(row, "get") else row["end_date"]
        return {
            "id": row["id"],
            "category": row["category"],
            "description": row["description"],
            "amount": float(row["amount"]),
            "entry_type": row["entry_type"],
            "frequency": row["frequency"],
            "start_date": start_date.isoformat() if isinstance(start_date, date) else str(start_date),
            "end_date": end_date.isoformat() if isinstance(end_date, date) else (str(end_date) if end_date else None),
            "active": bool(row["active"]),
        }
