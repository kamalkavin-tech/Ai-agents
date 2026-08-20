import json
import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class InvestigationStore:
    """Small durable SQLite job store suitable for local and staging use."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = threading.Lock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                    CREATE TABLE IF NOT EXISTS investigations (
                        id TEXT PRIMARY KEY,
                        service TEXT NOT NULL,
                        alert_message TEXT NOT NULL,
                        status TEXT NOT NULL,
                        result_json TEXT,
                        error TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
            )

    def create(self, service: str, alert_message: str) -> dict[str, Any]:
        investigation_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """
                    INSERT INTO investigations
                    (id, service, alert_message, status, created_at, updated_at)
                    VALUES (?, ?, ?, 'queued', ?, ?)
                    """,
                (investigation_id, service, alert_message, now, now),
            )
        return self.get(investigation_id)

    def get(self, investigation_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM investigations WHERE id = ?", (investigation_id,)
            ).fetchone()
        if row is None:
            return None
        record = dict(row)
        result_json = record.pop("result_json")
        record["result"] = json.loads(result_json) if result_json else None
        return record

    def update(
        self,
        investigation_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        result_json = json.dumps(result) if result is not None else None
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """
                    UPDATE investigations
                    SET status = ?, result_json = ?, error = ?, updated_at = ?
                    WHERE id = ?
                    """,
                (status, result_json, error, now, investigation_id),
            )
