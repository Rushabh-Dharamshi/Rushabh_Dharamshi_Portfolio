from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Mapping


@dataclass(slots=True)
class Expense:
    id: int
    date: str
    category: str
    description: str
    amount: float
    entry_type: str = "expense"

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Expense":
        row_date = row["date"]
        return cls(
            id=row["id"],
            date=row_date.isoformat() if isinstance(row_date, date) else str(row_date),
            category=row["category"],
            description=row["description"],
            amount=float(row["amount"]),
            entry_type=str(row.get("entry_type") or "expense"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
