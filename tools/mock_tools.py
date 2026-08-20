import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


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


def search_logs(service: str, level: str = None, start_time: str = None, end_time: str = None) -> list:
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


def get_metrics(service: str, metric: str = "error_rate_pct", start_time: str = None, end_time: str = None) -> list:
    """Return metric time series for a service, optionally filtered by time range."""
    metrics = _load("metrics.json")
    results = [m for m in metrics if m["service"] == service and m["metric"] == metric]

    if start_time:
        results = [m for m in results if m["timestamp"] >= start_time]
    if end_time:
        results = [m for m in results if m["timestamp"] <= end_time]

    return results


def get_past_incidents(keyword: str = None) -> list:
    """Search past incident history, optionally filtered by keyword in summary."""
    incidents = _load("incidents.json")
    if keyword:
        keyword_lower = keyword.lower()
        incidents = [
            i for i in incidents
            if keyword_lower in i["summary"].lower() or keyword_lower in i["root_cause"].lower()
        ]
    return incidents