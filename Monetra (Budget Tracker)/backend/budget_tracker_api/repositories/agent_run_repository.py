import json
from collections.abc import Callable

from sqlalchemy import insert, select
from sqlalchemy.engine import Connection

from budget_tracker_api.db import agent_runs_table


class AgentRunRepository:
    def __init__(self, connection_factory: Callable[[], Connection], user_id_provider: Callable[[], int] | None = None):
        self._connection_factory = connection_factory
        self._user_id_provider = user_id_provider or (lambda: 1)

    def _db(self) -> Connection:
        return self._connection_factory()

    def _user_id(self) -> int:
        return int(self._user_id_provider() or 1)

    def create_run(self, payload: dict) -> dict:
        record = {
            "user_id": self._user_id(),
            "workflow_name": payload["workflow_name"],
            "workflow_label": payload["workflow_label"],
            "status": payload["status"],
            "headline": payload["headline"],
            "summary": payload["summary"],
            "risk_level": payload["risk_level"],
            "recommended_actions": json.dumps(payload["recommended_actions"]),
            "automated_actions": json.dumps(payload["automated_actions"]),
            "email_subject": payload["email_subject"],
            "email_draft": payload["email_draft"],
            "task": payload["task"],
            "model": payload["model"],
            "tools_used": json.dumps(payload["tools_used"]),
            "report_download_url": payload["report_download_url"],
            "generated_at": payload["generated_at"],
        }
        db = self._db()
        result = db.execute(insert(agent_runs_table).values(**record))
        db.commit()
        return self.get_run(int(result.inserted_primary_key[0]))

    def get_run(self, run_id: int) -> dict | None:
        row = self._db().execute(
            select(agent_runs_table).where(
                agent_runs_table.c.id == run_id,
                agent_runs_table.c.user_id == self._user_id(),
            )
        ).mappings().first()
        if row is None:
            return None
        return self._deserialize(row)

    def list_runs(self, limit: int = 8) -> list[dict]:
        rows = self._db().execute(
            select(agent_runs_table)
            .where(agent_runs_table.c.user_id == self._user_id())
            .order_by(agent_runs_table.c.generated_at.desc(), agent_runs_table.c.id.desc())
            .limit(limit)
        ).mappings().all()
        return [self._deserialize(row) for row in rows]

    def latest_run(self, workflow_name: str) -> dict | None:
        row = self._db().execute(
            select(agent_runs_table)
            .where(
                agent_runs_table.c.user_id == self._user_id(),
                agent_runs_table.c.workflow_name == workflow_name,
            )
            .order_by(agent_runs_table.c.generated_at.desc(), agent_runs_table.c.id.desc())
            .limit(1)
        ).mappings().first()
        if row is None:
            return None
        return self._deserialize(row)

    def latest_run_for_day(self, workflow_name: str, date_prefix: str) -> dict | None:
        row = self._db().execute(
            select(agent_runs_table)
            .where(
                agent_runs_table.c.user_id == self._user_id(),
                agent_runs_table.c.workflow_name == workflow_name,
                agent_runs_table.c.generated_at.like(f"{date_prefix}%"),
            )
            .order_by(agent_runs_table.c.generated_at.desc(), agent_runs_table.c.id.desc())
            .limit(1)
        ).mappings().first()
        if row is None:
            return None
        return self._deserialize(row)

    @staticmethod
    def _deserialize(row) -> dict:
        return {
            "id": int(row["id"]),
            "workflow_name": row["workflow_name"],
            "workflow_label": row["workflow_label"],
            "status": row["status"],
            "headline": row["headline"],
            "summary": row["summary"],
            "risk_level": row["risk_level"],
            "recommended_actions": json.loads(row["recommended_actions"] or "[]"),
            "automated_actions": json.loads(row["automated_actions"] or "[]"),
            "email_subject": row["email_subject"],
            "email_draft": row["email_draft"],
            "task": row["task"],
            "model": row["model"],
            "tools_used": json.loads(row["tools_used"] or "[]"),
            "report_download_url": row["report_download_url"],
            "generated_at": row["generated_at"],
        }
