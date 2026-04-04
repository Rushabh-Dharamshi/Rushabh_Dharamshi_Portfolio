from sqlalchemy import create_engine

from budget_tracker_api.db import agent_runs_table, metadata
from budget_tracker_api.repositories.agent_run_repository import AgentRunRepository


def make_repository():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    metadata.create_all(engine, tables=[agent_runs_table])
    connection = engine.connect()
    repository = AgentRunRepository(lambda: connection)
    return repository, connection


def sample_payload(**overrides):
    payload = {
        "workflow_name": "month_end_close",
        "workflow_label": "Month-end close",
        "status": "completed",
        "headline": "Done",
        "summary": "Completed.",
        "risk_level": "low",
        "recommended_actions": ["Review"],
        "automated_actions": ["Generated report"],
        "email_subject": "Subject",
        "email_draft": "Body",
        "task": "Run it",
        "model": "mistral",
        "tools_used": ["generate_monthly_report"],
        "report_download_url": "/api/reports/monthly",
        "generated_at": "2026-04-03T12:00:00",
    }
    payload.update(overrides)
    return payload


def test_agent_run_repository_crud_and_deserialization():
    repository, connection = make_repository()

    created = repository.create_run(sample_payload())
    later = repository.create_run(
        sample_payload(
            workflow_name="upcoming_bills_email_dispatch",
            workflow_label="Upcoming bills email dispatch",
            generated_at="2026-04-03T13:00:00",
            recommended_actions=[],
            automated_actions=[],
            tools_used=[],
            report_download_url=None,
        )
    )

    assert created["id"] == 1
    assert repository.get_run(1)["recommended_actions"] == ["Review"]
    assert repository.get_run(999) is None
    assert repository.list_runs(1)[0]["id"] == 2
    assert repository.latest_run("month_end_close")["id"] == 1
    assert repository.latest_run("missing") is None
    assert repository.latest_run_for_day("upcoming_bills_email_dispatch", "2026-04-03")["id"] == 2
    assert repository.latest_run_for_day("upcoming_bills_email_dispatch", "2026-04-02") is None
    assert later["tools_used"] == []
    assert later["automated_actions"] == []

    connection.close()
