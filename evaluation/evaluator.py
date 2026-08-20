import argparse
import json
import re
from pathlib import Path
from typing import Any

from agents.diagnostic_agent import run_diagnostic_agent
from agents.models import InvestigationResult

CASES_PATH = Path(__file__).with_name("cases.json")


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_result(result: InvestigationResult, expected: dict[str, Any]) -> dict[str, Any]:
    """Score factual coverage and investigation behavior without another LLM."""
    report = result.report

    def normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9.]+", " ", value.lower()).strip()

    root_cause = normalize(report.root_cause or "")
    evidence = normalize(
        " ".join(f"{item.observation} {item.reference}" for item in report.evidence)
    )

    expected_incident = expected.get("similar_past_incident")
    checks = {
        "root_cause_keywords": all(
            normalize(keyword) in root_cause for keyword in expected["root_cause_keywords"]
        ),
        "evidence_keywords": all(
            normalize(keyword) in evidence for keyword in expected["evidence_keywords"]
        ),
        "required_tools": set(expected["required_tools"]).issubset(result.tool_calls),
        "similar_incident": (
            report.similar_past_incident is None
            if expected_incident is None
            else expected_incident.lower() in (report.similar_past_incident or "").lower()
        ),
        "confidence": (
            report.confidence >= expected.get("minimum_confidence", 0.0)
            and report.confidence <= expected.get("maximum_confidence", 1.0)
        ),
        "safe_recommendations": all(
            recommendation.requires_human_approval for recommendation in report.recommendations
        ),
        "status": (
            report.status == expected["expected_status"]
            if "expected_status" in expected
            else report.status != "inconclusive"
        ),
    }
    return {
        "score": sum(checks.values()) / len(checks),
        "passed": all(checks.values()),
        "checks": checks,
    }


def run_suite(case_id: str | None = None) -> list[dict[str, Any]]:
    results = []
    for case in load_cases():
        if case_id and case["case_id"] != case_id:
            continue
        try:
            investigation = run_diagnostic_agent(case["service"], case["alert_message"])
            score = evaluate_result(investigation, case["expected"])
            results.append(
                {
                    "case_id": case["case_id"],
                    **score,
                    "root_cause": investigation.report.root_cause,
                    "confidence": investigation.report.confidence,
                    "tool_calls": investigation.tool_calls,
                }
            )
        # A regression suite records provider failures per case and continues the remaining cases.
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "case_id": case["case_id"],
                    "score": 0.0,
                    "passed": False,
                    "error": type(exc).__name__,
                    "message": str(exc)[:500],
                }
            )
    if not results:
        raise ValueError(f"No evaluation case matched {case_id!r}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live diagnostic regression cases")
    parser.add_argument("--case", help="Run one case id instead of the full suite")
    args = parser.parse_args()
    results = run_suite(args.case)
    print(json.dumps(results, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
