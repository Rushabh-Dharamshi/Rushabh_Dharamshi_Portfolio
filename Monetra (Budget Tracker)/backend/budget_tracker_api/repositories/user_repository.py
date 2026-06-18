import hashlib
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.engine import Connection

from budget_tracker_api.db import (
    agent_runs_table,
    expenses_table,
    monthly_income_records_table,
    password_reset_tokens_table,
    recurring_items_table,
    recurring_occurrence_status_table,
    savings_goals_table,
    settings_table,
    users_table,
)


class UserRepository:
    def __init__(self, connection_factory: Callable[[], Connection]):
        self._connection_factory = connection_factory

    def _db(self) -> Connection:
        return self._connection_factory()

    def create_user(self, username: str, email: str, password_hash: str, password_fingerprint: str | None = None) -> dict:
        created_at = self._utc_now()
        db = self._db()
        result = db.execute(
            insert(users_table).values(
                username=username,
                email=email,
                password_hash=password_hash,
                password_fingerprint=password_fingerprint,
                created_at=created_at,
            )
        )
        db.commit()
        return self.get_user_by_id(int(result.inserted_primary_key[0]))

    def get_user_by_id(self, user_id: int) -> dict | None:
        row = self._db().execute(
            select(users_table).where(users_table.c.id == user_id)
        ).mappings().first()
        return self._user_to_dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict | None:
        row = self._db().execute(
            select(users_table).where(users_table.c.username == username)
        ).mappings().first()
        return self._user_to_dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict | None:
        row = self._db().execute(
            select(users_table).where(users_table.c.email == email)
        ).mappings().first()
        return self._user_to_dict(row) if row else None

    def get_user_by_username_or_email(self, identifier: str) -> dict | None:
        normalized = identifier.strip()
        if "@" in normalized:
            return self.get_user_by_email(normalized.lower())
        return self.get_user_by_username(normalized)

    def list_users(self) -> list[dict]:
        rows = self._db().execute(
            select(users_table).order_by(users_table.c.id.asc())
        ).mappings().all()
        return [self._user_to_dict(row) for row in rows]

    def count_users(self) -> int:
        value = self._db().execute(select(func.count()).select_from(users_table)).scalar_one()
        return int(value)

    def update_password_hash(self, user_id: int, password_hash: str, password_fingerprint: str | None = None) -> None:
        db = self._db()
        db.execute(
            update(users_table)
            .where(users_table.c.id == user_id)
            .values(password_hash=password_hash, password_fingerprint=password_fingerprint)
        )
        db.commit()

    def delete_user(self, user_id: int) -> bool:
        db = self._db()
        for table in (
            password_reset_tokens_table,
            expenses_table,
            settings_table,
            monthly_income_records_table,
            recurring_occurrence_status_table,
            recurring_items_table,
            savings_goals_table,
            agent_runs_table,
        ):
            db.execute(delete(table).where(table.c.user_id == user_id))
        result = db.execute(delete(users_table).where(users_table.c.id == user_id))
        db.commit()
        return bool(result.rowcount)

    def create_reset_token(self, user_id: int, token: str, expires_at: str) -> None:
        now = self._utc_now()
        db = self._db()
        db.execute(
            insert(password_reset_tokens_table).values(
                user_id=user_id,
                token_hash=self.hash_token(token),
                expires_at=expires_at,
                used_at=None,
                created_at=now,
            )
        )
        db.commit()

    def get_reset_token(self, token: str) -> dict | None:
        row = self._db().execute(
            select(password_reset_tokens_table).where(
                password_reset_tokens_table.c.token_hash == self.hash_token(token)
            )
        ).mappings().first()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "user_id": int(row["user_id"]),
            "token_hash": row["token_hash"],
            "expires_at": row["expires_at"],
            "used_at": row["used_at"],
            "created_at": row["created_at"],
        }

    def mark_reset_token_used(self, token_id: int) -> None:
        db = self._db()
        db.execute(
            update(password_reset_tokens_table)
            .where(password_reset_tokens_table.c.id == token_id)
            .values(used_at=self._utc_now())
        )
        db.commit()

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _user_to_dict(row) -> dict:
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "password_hash": row["password_hash"],
            "password_fingerprint": row.get("password_fingerprint") if hasattr(row, "get") else row["password_fingerprint"],
            "created_at": row["created_at"],
        }
