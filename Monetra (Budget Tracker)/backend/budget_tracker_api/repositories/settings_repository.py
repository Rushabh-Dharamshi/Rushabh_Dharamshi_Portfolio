from collections.abc import Callable
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from budget_tracker_api.db import monthly_income_records_table, settings_table


class SettingsRepository:
    def __init__(self, connection_factory: Callable[[], Connection]):
        self._connection_factory = connection_factory

    def _db(self) -> Connection:
        return self._connection_factory()

    @staticmethod
    def _resolve_month_key(month_key: str | None = None) -> str:
        return month_key or datetime.now().strftime("%Y-%m")

    def get_settings(self, month_key: str | None = None) -> dict:
        settings_row = self._db().execute(
            select(
                settings_table.c.monthly_budget,
                settings_table.c.monthly_income,
            ).where(settings_table.c.id == 1)
        ).first()
        resolved_month = self._resolve_month_key(month_key)
        income_row = self._db().execute(
            select(monthly_income_records_table.c.monthly_income).where(
                monthly_income_records_table.c.month_key == resolved_month
            )
        ).first()
        monthly_income = float(income_row[0]) if income_row else float(settings_row[1])
        return {
            "monthly_budget": float(settings_row[0]),
            "monthly_income": monthly_income,
            "income_month": resolved_month,
        }

    def get_monthly_budget(self) -> float:
        return self.get_settings()["monthly_budget"]

    def get_monthly_income(self, month_key: str | None = None) -> float:
        return self.get_settings(month_key)["monthly_income"]

    def update_monthly_budget(self, monthly_budget: float) -> float:
        db = self._db()
        db.execute(
            update(settings_table)
            .where(settings_table.c.id == 1)
            .values(monthly_budget=round(float(monthly_budget), 2))
        )
        db.commit()
        return self.get_monthly_budget()

    def update_monthly_income(self, monthly_income: float, month_key: str | None = None) -> dict:
        resolved_month = self._resolve_month_key(month_key)
        rounded_income = round(float(monthly_income), 2)
        db = self._db()
        existing_row = db.execute(
            select(monthly_income_records_table.c.id).where(
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
                    month_key=resolved_month,
                    monthly_income=rounded_income,
                )
            )
        db.commit()
        return {
            "monthly_income": self.get_monthly_income(resolved_month),
            "income_month": resolved_month,
        }
