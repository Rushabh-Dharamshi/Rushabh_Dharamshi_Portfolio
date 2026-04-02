import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock


class AgentMemoryService:
    def __init__(self, memory_path: Path | str | None = None, max_entries: int = 80):
        self._memory_path = Path(memory_path) if memory_path else None
        self._max_entries = max_entries
        self._lock = Lock()
        self._ephemeral_entries: list[dict] = []
        if self._memory_path is not None:
            self._memory_path.parent.mkdir(parents=True, exist_ok=True)

    def recall(self, limit: int = 6) -> list[dict]:
        with self._lock:
            entries = self._load_entries()
        return entries[-max(1, limit):]

    def remember(
        self,
        *,
        kind: str,
        task: str,
        summary: str,
        tools_used: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        entry = {
            "kind": kind,
            "task": task,
            "summary": summary,
            "tools_used": tools_used or [],
            "metadata": metadata or {},
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        with self._lock:
            entries = self._load_entries()
            entries.append(entry)
            entries = entries[-self._max_entries :]
            self._save_entries(entries)

    def _load_entries(self) -> list[dict]:
        if self._memory_path is None:
            return list(self._ephemeral_entries)
        if not self._memory_path.exists():
            return []
        try:
            payload = json.loads(self._memory_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return payload if isinstance(payload, list) else []

    def _save_entries(self, entries: list[dict]) -> None:
        if self._memory_path is None:
            self._ephemeral_entries = list(entries)
            return
        self._memory_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
