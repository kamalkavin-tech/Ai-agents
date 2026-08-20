import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        records = json.load(f)

    synthetic_path = os.path.join(DATA_DIR, f"synthetic_{filename}")
    if os.path.exists(synthetic_path):
        with open(synthetic_path, "r") as f:
            records.extend(json.load(f))
    return records


def get_recent_deploys(service: str, limit: int = 5) -> list:
    """Return the most recent deploys for a given service."""
    deploys = _load("deploys.json")
    filtered = [d for d in deploys if d["service"] == service]
    filtered.sort(key=lambda d: d["timestamp"], reverse=True)
    return filtered[:limit]


def get_git_diff(commit_id: str) -> dict:
    """Return details of a specific commit (files changed, message, author)."""
    deploys = _load("deploys.json")
    for d in deploys:
        if d["commit_id"] == commit_id:
            return d
    return {"error": f"No commit found with id {commit_id}"}


def search_logs(
    service: str,
    level: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list:
    """Search logs for a service, optionally filtered by level and time range."""
    logs = _load("logs.json")
    results = [l for l in logs if l["service"] == service]

    if level:
        results = [l for l in results if l["level"] == level]
    if start_time:
        results = [l for l in results if l["timestamp"] >= start_time]
    if end_time:
        results = [l for l in results if l["timestamp"] <= end_time]

    return results


def get_metrics(
    service: str,
    metric: str = "error_rate_pct",
    start_time: str | None = None,
    end_time: str | None = None,
) -> list:
    """Return metric time series for a service, optionally filtered by time range."""
    metrics = _load("metrics.json")
    results = [m for m in metrics if m["service"] == service and m["metric"] == metric]

    if start_time:
        results = [m for m in results if m["timestamp"] >= start_time]
    if end_time:
        results = [m for m in results if m["timestamp"] <= end_time]

    return results


def get_past_incidents(keyword: str | None = None) -> list:
    """Search past incident history, optionally filtered by keyword in summary."""
    incidents = _load("incidents.json")
    if keyword:
        keyword_lower = keyword.lower()
        incidents = [
            i
            for i in incidents
            if keyword_lower in i["summary"].lower() or keyword_lower in i["root_cause"].lower()
        ]
    return incidents


def search_traces(
    service: str,
    status: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list:
    """Search distributed traces for a service and time window."""
    traces = _load("traces.json")
    results = [trace for trace in traces if trace["service"] == service]
    if status:
        results = [trace for trace in results if trace["status"] == status]
    if start_time:
        results = [trace for trace in results if trace["timestamp"] >= start_time]
    if end_time:
        results = [trace for trace in results if trace["timestamp"] <= end_time]
    return results


def list_available_metrics(service: str) -> list:
    """Return metric names available for a service."""
    metrics = _load("metrics.json")
    return sorted({item["metric"] for item in metrics if item["service"] == service})


def get_kubernetes_events(
    service: str,
    event_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list:
    """Return Kubernetes events associated with a service."""
    events = _load("kubernetes_events.json")
    results = [event for event in events if event["service"] == service]
    if event_type:
        results = [event for event in results if event["type"] == event_type]
    if start_time:
        results = [event for event in results if event["timestamp"] >= start_time]
    if end_time:
        results = [event for event in results if event["timestamp"] <= end_time]
    return results


def get_config_changes(
    service: str,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list:
    """Return configuration changes for a service."""
    changes = _load("config_changes.json")
    results = [change for change in changes if change["service"] == service]
    if start_time:
        results = [change for change in results if change["timestamp"] >= start_time]
    if end_time:
        results = [change for change in results if change["timestamp"] <= end_time]
    return results


def get_health_checks(
    service: str,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list:
    """Return dependency and service health-check observations."""
    checks = _load("health_checks.json")
    results = [check for check in checks if check["service"] == service]
    if start_time:
        results = [check for check in results if check["timestamp"] >= start_time]
    if end_time:
        results = [check for check in results if check["timestamp"] <= end_time]
    return results


def get_service_dependencies(service: str) -> list:
    """Return direct upstream dependencies recorded in the service catalog."""
    catalog = _load("service_dependencies.json")
    return [item for item in catalog if item["service"] == service]


def search_runbooks(service: str | None = None, keyword: str | None = None) -> list:
    """Search read-only operational runbooks by service or keyword."""
    runbooks = _load("runbooks.json")
    results = runbooks
    if service:
        results = [runbook for runbook in results if runbook["service"] == service]
    if keyword:
        needle = keyword.lower()
        results = [
            runbook
            for runbook in results
            if needle in runbook["title"].lower() or needle in runbook["content"].lower()
        ]
    return results
