import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostic_agent import run_diagnostic_agent
from agents.models import InvestigationResult
from app.store import InvestigationStore


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(min_length=1, max_length=100)
    alert_message: str = Field(min_length=1, max_length=4000)


class InvestigationRecord(BaseModel):
    id: str
    service: str
    alert_message: str
    status: Literal["queued", "running", "completed", "failed"]
    result: dict[str, Any] | None
    error: str | None
    created_at: str
    updated_at: str


Runner = Callable[[str, str], InvestigationResult]


def _run_job(
    store: InvestigationStore,
    runner: Runner,
    investigation_id: str,
    service: str,
    alert_message: str,
) -> None:
    store.update(investigation_id, status="running")
    try:
        result = runner(service, alert_message)
        store.update(
            investigation_id,
            status="completed",
            result=result.model_dump(mode="json"),
        )
    # Background jobs must persist all provider and connector failures for later inspection.
    except Exception as exc:  # noqa: BLE001
        store.update(
            investigation_id,
            status="failed",
            error=f"{type(exc).__name__}: {str(exc)[:1000]}",
        )


def create_app(
    *,
    store: InvestigationStore | None = None,
    runner: Runner = run_diagnostic_agent,
) -> FastAPI:
    database_path = Path(os.getenv("SENTINEL_DB_PATH", "data/investigations.db"))
    active_store = store or InvestigationStore(database_path)
    application = FastAPI(
        title="Sentinel Ops Agent",
        version="0.2.0",
        description="Read-only, evidence-driven incident investigations.",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "read-only"}

    @application.post(
        "/investigations",
        response_model=InvestigationRecord,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_investigation(
        request: InvestigationRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        record = active_store.create(request.service.strip(), request.alert_message.strip())
        background_tasks.add_task(
            _run_job,
            active_store,
            runner,
            record["id"],
            record["service"],
            record["alert_message"],
        )
        return record

    @application.get("/investigations/{investigation_id}", response_model=InvestigationRecord)
    def get_investigation(investigation_id: str) -> dict[str, Any]:
        record = active_store.get(investigation_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return record

    application.state.investigation_store = active_store
    return application


app = create_app()
