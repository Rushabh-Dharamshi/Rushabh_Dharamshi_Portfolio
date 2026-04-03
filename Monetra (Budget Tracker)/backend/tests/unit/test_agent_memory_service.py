import json

from budget_tracker_api.services.agent_memory_service import AgentMemoryService


def test_agent_memory_service_ephemeral_and_limit():
    service = AgentMemoryService(max_entries=2)
    service.remember(kind="briefing", task="t1", summary="s1")
    service.remember(kind="briefing", task="t2", summary="s2", tools_used=["tool-a"], metadata={"a": 1})
    service.remember(kind="briefing", task="t3", summary="s3")

    recalled = service.recall(limit=5)
    assert [entry["task"] for entry in recalled] == ["t2", "t3"]
    assert recalled[0]["tools_used"] == ["tool-a"]
    assert recalled[0]["metadata"] == {"a": 1}


def test_agent_memory_service_file_backed_and_invalid_payload(tmp_path):
    memory_path = tmp_path / "memory.json"
    service = AgentMemoryService(memory_path=memory_path, max_entries=3)
    service.remember(kind="workflow", task="month-end", summary="ready")

    payload = json.loads(memory_path.read_text(encoding="utf-8"))
    assert payload[0]["task"] == "month-end"
    assert service.recall(limit=1)[0]["kind"] == "workflow"

    memory_path.write_text("not-json", encoding="utf-8")
    assert service.recall(limit=3) == []
