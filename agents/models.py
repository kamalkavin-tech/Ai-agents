from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    """A verifiable observation returned by an investigation tool."""

    model_config = ConfigDict(extra="forbid")

    source_tool: Literal[
        "get_recent_deploys",
        "get_git_diff",
        "search_logs",
        "get_metrics",
        "list_available_metrics",
        "get_past_incidents",
        "search_traces",
        "get_kubernetes_events",
        "get_config_changes",
        "get_health_checks",
        "get_service_dependencies",
        "search_runbooks",
    ]
    observation: str = Field(min_length=1)
    reference: str = Field(
        min_length=1,
        description="Commit id, incident id, log timestamp, metric timestamp, or query window.",
    )


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1)
    priority: Literal["immediate", "follow-up"]
    requires_human_approval: bool = True


class DiagnosticReport(BaseModel):
    """Strict contract returned by the diagnostic agent."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["confirmed", "probable", "inconclusive"]
    root_cause: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    alternative_hypotheses: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    similar_past_incident: str | None = None


class InvestigationResult(BaseModel):
    """Report plus an auditable summary of the agent's tool activity."""

    report: DiagnosticReport
    tool_calls: list[str]
    turns: int = Field(ge=1)
