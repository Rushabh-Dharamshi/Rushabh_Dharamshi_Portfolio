import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, insert, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from budget_tracker_api.db import expenses_table, metadata


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate expense data from the legacy SQLite database into PostgreSQL."
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(Path(__file__).resolve().parents[2] / "budget_tracker.db"),
        help="Path to the source SQLite database.",
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="Target PostgreSQL SQLAlchemy URL.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Clear the target expenses table before importing.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    source = sqlite3.connect(args.sqlite_path)
    source.row_factory = sqlite3.Row
    rows = source.execute(
        "SELECT id, date, category, description, amount FROM expenses ORDER BY id ASC"
    ).fetchall()

    engine = create_engine(args.database_url, future=True)
    metadata.create_all(engine)

    with engine.begin() as connection:
        if args.truncate:
            if engine.dialect.name == "postgresql":
                connection.execute(text("TRUNCATE TABLE expenses RESTART IDENTITY"))
            else:
                connection.execute(expenses_table.delete())

        payload = [
            {
                "id": row["id"],
                "date": datetime.strptime(row["date"], "%Y-%m-%d").date(),
                "category": row["category"],
                "description": row["description"],
                "amount": row["amount"],
            }
            for row in rows
        ]
        if payload:
            connection.execute(insert(expenses_table), payload)

        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('expenses', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM expenses), 1), true)"
                )
            )

    source.close()
    print(f"Migrated {len(rows)} expense rows into {args.database_url}.")


if __name__ == "__main__":
    main()
