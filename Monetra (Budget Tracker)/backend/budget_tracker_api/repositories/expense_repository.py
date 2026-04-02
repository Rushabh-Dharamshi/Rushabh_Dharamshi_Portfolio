from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.engine import Connection

from budget_tracker_api.db import expenses_table
from budget_tracker_api.schemas import Expense


class ExpenseRepository:
    def __init__(self, connection_factory: Callable[[], Connection]):
        self._connection_factory = connection_factory

    def _db(self) -> Connection:
        return self._connection_factory()

    def list_expenses(
        self,
        sort_direction: str = "desc",
        entry_type: str | None = None,
    ) -> list[Expense]:
        order_column = (
            expenses_table.c.date.asc()
            if sort_direction.lower() == "asc"
            else expenses_table.c.date.desc()
        )
        order_id = (
            expenses_table.c.id.asc()
            if sort_direction.lower() == "asc"
            else expenses_table.c.id.desc()
        )
        query = select(expenses_table).order_by(order_column, order_id)
        query = self._apply_entry_type_filter(query, entry_type)
        rows = self._db().execute(query).mappings().all()
        return [Expense.from_row(row) for row in rows]

    def get_expense(self, expense_id: int) -> Expense | None:
        row = self._db().execute(
            select(expenses_table).where(expenses_table.c.id == expense_id)
        ).mappings().first()
        return Expense.from_row(row) if row else None

    def create_expense(self, payload: dict) -> Expense:
        db = self._db()
        result = db.execute(insert(expenses_table).values(**self._coerce_payload(payload)))
        db.commit()
        return self.get_expense(int(result.inserted_primary_key[0]))

    def update_expense(self, expense_id: int, payload: dict) -> Expense | None:
        db = self._db()
        result = db.execute(
            update(expenses_table)
            .where(expenses_table.c.id == expense_id)
            .values(**self._coerce_payload(payload))
        )
        db.commit()
        if result.rowcount == 0:
            return None
        return self.get_expense(expense_id)

    def delete_expense(self, expense_id: int) -> bool:
        db = self._db()
        result = db.execute(delete(expenses_table).where(expenses_table.c.id == expense_id))
        db.commit()
        return result.rowcount > 0

    def bulk_insert(self, rows: list[dict]) -> int:
        if not rows:
            return 0

        db = self._db()
        db.execute(insert(expenses_table), [self._coerce_payload(row) for row in rows])
        db.commit()
        return len(rows)

    def monthly_spending(self, entry_type: str | None = "expense") -> list[tuple[str, float]]:
        rows = self._list_rows(entry_type=entry_type)
        totals: dict[str, float] = defaultdict(float)
        for row in rows:
            totals[self._month_key(row["date"])] += self._to_float(row["amount"])
        return sorted((month, round(total, 2)) for month, total in totals.items())

    def monthly_cash_flow(self) -> list[dict]:
        rows = self._list_rows()
        totals: dict[str, dict[str, float]] = defaultdict(
            lambda: {"income": 0.0, "expense": 0.0}
        )
        for row in rows:
            month_key = self._month_key(row["date"])
            entry_type = str(row.get("entry_type") or "expense")
            totals[month_key][entry_type] += self._to_float(row["amount"])

        return [
            {
                "month": month,
                "income": round(values["income"], 2),
                "expense": round(values["expense"], 2),
                "net": round(values["income"] - values["expense"], 2),
            }
            for month, values in sorted(totals.items())
        ]

    def monthly_total(self, month_key: str, entry_type: str | None = "expense") -> float:
        start_date, end_date = self._month_bounds(month_key)
        query = select(func.sum(expenses_table.c.amount).label("total")).where(
            expenses_table.c.date >= start_date,
            expenses_table.c.date < end_date,
        )
        query = self._apply_entry_type_filter(query, entry_type)
        row = self._db().execute(query).mappings().one()
        return self._to_float(row["total"])

    def cash_flow_totals(self, month_key: str) -> dict[str, float]:
        return {
            "income": self.monthly_total(month_key, "income"),
            "expense": self.monthly_total(month_key, "expense"),
            "net": round(
                self.monthly_total(month_key, "income")
                - self.monthly_total(month_key, "expense"),
                2,
            ),
        }

    def weekly_total(
        self,
        start_date: str,
        end_date: str,
        entry_type: str | None = "expense",
    ) -> float:
        query = select(func.sum(expenses_table.c.amount).label("total")).where(
            expenses_table.c.date >= self._parse_date(start_date),
            expenses_table.c.date <= self._parse_date(end_date),
        )
        query = self._apply_entry_type_filter(query, entry_type)
        row = self._db().execute(query).mappings().one()
        return self._to_float(row["total"])

    def category_totals(
        self,
        month_key: str,
        entry_type: str | None = "expense",
    ) -> list[tuple[str, float]]:
        expenses = self.expenses_for_month(month_key, entry_type=entry_type)
        totals: dict[str, float] = defaultdict(float)
        for expense in expenses:
            totals[expense.category] += expense.amount
        return sorted(
            ((category, round(amount, 2)) for category, amount in totals.items()),
            key=lambda item: (-item[1], item[0]),
        )

    def count_expenses_for_month(
        self,
        month_key: str,
        entry_type: str | None = None,
    ) -> int:
        start_date, end_date = self._month_bounds(month_key)
        query = select(func.count()).select_from(expenses_table).where(
            expenses_table.c.date >= start_date,
            expenses_table.c.date < end_date,
        )
        query = self._apply_entry_type_filter(query, entry_type)
        row = self._db().execute(query).one()
        return int(row[0] or 0)

    def recent_expenses(
        self,
        limit: int = 5,
        entry_type: str | None = None,
    ) -> list[Expense]:
        query = (
            select(expenses_table)
            .order_by(expenses_table.c.date.desc(), expenses_table.c.id.desc())
            .limit(limit)
        )
        query = self._apply_entry_type_filter(query, entry_type)
        rows = self._db().execute(query).mappings().all()
        return [Expense.from_row(row) for row in rows]

    def description_totals_for_category(
        self,
        month_key: str,
        category: str,
        entry_type: str | None = "expense",
    ) -> list[tuple[str, float]]:
        expenses = [
            expense
            for expense in self.expenses_for_month(month_key, entry_type=entry_type)
            if expense.category == category
        ]
        totals: dict[str, float] = defaultdict(float)
        for expense in expenses:
            totals[expense.description] += expense.amount
        return sorted(
            ((description, round(amount, 2)) for description, amount in totals.items()),
            key=lambda item: (-item[1], item[0]),
        )

    def expenses_for_month(
        self,
        month_key: str,
        entry_type: str | None = "expense",
    ) -> list[Expense]:
        start_date, end_date = self._month_bounds(month_key)
        query = (
            select(expenses_table)
            .where(expenses_table.c.date >= start_date, expenses_table.c.date < end_date)
            .order_by(expenses_table.c.date.asc(), expenses_table.c.id.asc())
        )
        query = self._apply_entry_type_filter(query, entry_type)
        rows = self._db().execute(query).mappings().all()
        return [Expense.from_row(row) for row in rows]

    def daily_totals(
        self,
        month_key: str,
        entry_type: str | None = "expense",
    ) -> list[tuple[str, float]]:
        totals: dict[str, float] = defaultdict(float)
        for expense in self.expenses_for_month(month_key, entry_type=entry_type):
            totals[expense.date] += expense.amount
        return sorted((day, round(total, 2)) for day, total in totals.items())

    def largest_expenses(
        self,
        month_key: str,
        limit: int = 10,
        entry_type: str | None = "expense",
    ) -> list[Expense]:
        start_date, end_date = self._month_bounds(month_key)
        query = (
            select(expenses_table)
            .where(expenses_table.c.date >= start_date, expenses_table.c.date < end_date)
            .order_by(
                expenses_table.c.amount.desc(),
                expenses_table.c.date.desc(),
                expenses_table.c.id.desc(),
            )
            .limit(limit)
        )
        query = self._apply_entry_type_filter(query, entry_type)
        rows = self._db().execute(query).mappings().all()
        return [Expense.from_row(row) for row in rows]

    def _list_rows(self, entry_type: str | None = None) -> list[dict]:
        query = select(expenses_table.c.date, expenses_table.c.amount, expenses_table.c.entry_type).order_by(
            expenses_table.c.date.asc()
        )
        query = self._apply_entry_type_filter(query, entry_type)
        return self._db().execute(query).mappings().all()

    @staticmethod
    def _apply_entry_type_filter(query, entry_type: str | None):
        if entry_type is None:
            return query
        return query.where(expenses_table.c.entry_type == entry_type)

    @staticmethod
    def _to_float(value: Decimal | float | int | None) -> float:
        return float(value or 0.0)

    @staticmethod
    def _parse_date(raw_date: str) -> date:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()

    @classmethod
    def _month_bounds(cls, month_key: str) -> tuple[date, date]:
        start_date = datetime.strptime(f"{month_key}-01", "%Y-%m-%d").date()
        if start_date.month == 12:
            end_date = date(start_date.year + 1, 1, 1)
        else:
            end_date = date(start_date.year, start_date.month + 1, 1)
        return start_date, end_date

    @classmethod
    def _month_key(cls, row_date: date | str) -> str:
        if isinstance(row_date, str):
            return row_date[:7]
        return row_date.strftime("%Y-%m")

    @classmethod
    def _coerce_payload(cls, payload: dict) -> dict:
        return {
            "date": cls._parse_date(payload["date"]),
            "category": payload["category"],
            "description": payload["description"],
            "amount": round(float(payload["amount"]), 2),
            "entry_type": payload.get("entry_type", "expense"),
        }
