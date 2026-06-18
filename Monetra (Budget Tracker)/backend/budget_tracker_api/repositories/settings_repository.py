from collections.abc import Callable
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Connection

from budget_tracker_api.db import monthly_budget_records_table, monthly_income_records_table, settings_table


class SettingsRepository:
    def __init__(self, connection_factory: Callable[[], Connection], user_id_provider: Callable[[], int] | None = None):
        self._connection_factory = connection_factory
        self._user_id_provider = user_id_provider or (lambda: 1)

    def _db(self) -> Connection:
        return self._connection_factory()

    def _user_id(self) -> int:
        return int(self._user_id_provider() or 1)

    @staticmethod
    def _resolve_month_key(month_key: str | None = None) -> str:
        return month_key or datetime.now().strftime("%Y-%m")

    def get_settings(self, month_key: str | None = None) -> dict:
        self._ensure_settings_row()
        settings_row = self._db().execute(
            select(
                settings_table.c.monthly_budget,
                settings_table.c.monthly_income,
            ).where(settings_table.c.user_id == self._user_id())
        ).first()
        resolved_month = self._resolve_month_key(month_key)
        income_row = self._db().execute(
            select(monthly_income_records_table.c.monthly_income).where(
                monthly_income_records_table.c.user_id == self._user_id(),
                monthly_income_records_table.c.month_key == resolved_month
            )
        ).first()
        budget_row = self._db().execute(
            select(monthly_budget_records_table.c.monthly_budget).where(
                monthly_budget_records_table.c.user_id == self._user_id(),
                monthly_budget_records_table.c.month_key == resolved_month
            )
        ).first()
        monthly_budget = float(budget_row[0]) if budget_row else float(settings_row[0])
        monthly_income = float(income_row[0]) if income_row else float(settings_row[1])
        return {
            "monthly_budget": monthly_budget,
            "budget_month": resolved_month,
            "monthly_income": monthly_income,
            "income_month": resolved_month,
        }

    def get_monthly_budget(self, month_key: str | None = None) -> float:
        return self.get_settings(month_key)["monthly_budget"]

    def get_monthly_income(self, month_key: str | None = None) -> float:
        return self.get_settings(month_key)["monthly_income"]

    def list_monthly_income_records(self, before_month_key: str | None = None) -> list[dict]:
        query = select(
            monthly_income_records_table.c.month_key,
            monthly_income_records_table.c.monthly_income,
        ).where(monthly_income_records_table.c.user_id == self._user_id())
        if before_month_key:
            query = query.where(monthly_income_records_table.c.month_key < before_month_key)
        rows = self._db().execute(query.order_by(monthly_income_records_table.c.month_key.asc())).all()
        return [
            {
                "month_key": row[0],
                "monthly_income": float(row[1]),
            }
            for row in rows
        ]

    def update_monthly_budget(self, monthly_budget: float, month_key: str | None = None) -> dict:
        resolved_month = self._resolve_month_key(month_key)
        rounded_budget = round(float(monthly_budget), 2)
        db = self._db()
        existing_row = db.execute(
            select(monthly_budget_records_table.c.id).where(
                monthly_budget_records_table.c.user_id == self._user_id(),
                monthly_budget_records_table.c.month_key == resolved_month
            )
        ).first()
        if existing_row:
            db.execute(
                update(monthly_budget_records_table)
                .where(monthly_budget_records_table.c.id == existing_row[0])
                .values(monthly_budget=rounded_budget)
            )
        else:
            db.execute(
                insert(monthly_budget_records_table).values(
                    user_id=self._user_id(),
                    month_key=resolved_month,
                    monthly_budget=rounded_budget,
                )
            )
        db.commit()
        return {
            "monthly_budget": self.get_monthly_budget(resolved_month),
            "budget_month": resolved_month,
        }

    def update_monthly_income(self, monthly_income: float, month_key: str | None = None) -> dict:
        resolved_month = self._resolve_month_key(month_key)
        rounded_income = round(float(monthly_income), 2)
        db = self._db()
        existing_row = db.execute(
            select(monthly_income_records_table.c.id).where(
                monthly_income_records_table.c.user_id == self._user_id(),
                monthly_income_records_table.c.month_key == resolved_month
            )
        ).first()
        if existing_row:
            db.execute(
                update(monthly_income_records_table)
                .where(monthly_income_records_table.c.id == existing_row[0])
                .values(monthly_income=rounded_income)
            )
        else:
            db.execute(
                insert(monthly_income_records_table).values(
                    user_id=self._user_id(),
                    month_key=resolved_month,
                    monthly_income=rounded_income,
                )
            )
        db.commit()
        return {
            "monthly_income": self.get_monthly_income(resolved_month),
            "income_month": resolved_month,
        }

    def _ensure_settings_row(self) -> None:
        db = self._db()
        existing = db.execute(
            select(settings_table.c.id).where(settings_table.c.user_id == self._user_id())
        ).first()
        if existing:
            return
        defaults = db.execute(
            select(settings_table.c.monthly_budget, settings_table.c.monthly_income)
            .where(settings_table.c.user_id == 1)
        ).first()
        default_budget = float(defaults[0]) if defaults else 0.0
        default_income = float(defaults[1]) if defaults else 0.0
        try:
            db.execute(
                insert(settings_table).values(
                    user_id=self._user_id(),
                    monthly_budget=default_budget,
                    monthly_income=default_income,
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
