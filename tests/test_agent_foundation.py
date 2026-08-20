import unittest

from pydantic import ValidationError

from agents.diagnostic_agent import TOOL_FUNCTIONS, TOOLS, _execute_tool, _gemini_schema
from agents.models import DiagnosticReport, Evidence, InvestigationResult, Recommendation
from evaluation.evaluator import evaluate_result, load_cases
from tools.mock_tools import (
    get_config_changes,
    get_kubernetes_events,
    get_metrics,
    get_recent_deploys,
    get_service_dependencies,
    list_available_metrics,
    search_logs,
    search_runbooks,
    search_traces,
)


class ToolTests(unittest.TestCase):
    def test_deploys_are_filtered_sorted_and_limited(self):
        deploys = get_recent_deploys("inventory-service", limit=2)
        self.assertEqual([item["commit_id"] for item in deploys], ["h8q4r99", "g5n2p77"])

    def test_metric_time_window_is_inclusive(self):
        metrics = get_metrics(
            "inventory-service",
            start_time="2026-08-19T19:03:00Z",
            end_time="2026-08-19T19:06:00Z",
        )
        self.assertEqual([item["value"] for item in metrics], [4.1, 9.3])

    def test_error_log_filter(self):
        logs = search_logs("checkout-service", level="ERROR")
        self.assertTrue(logs)
        self.assertTrue(all(item["level"] == "ERROR" for item in logs))

    def test_tool_arguments_are_bounded(self):
        result = _execute_tool("get_recent_deploys", {"service": "x", "limit": 1000})
        self.assertEqual(result["error"], "Invalid tool arguments")

    def test_unknown_tool_is_rejected(self):
        result = _execute_tool("delete_production", {})
        self.assertIn("not allowed", result["error"])

    def test_extended_observability_tools(self):
        self.assertEqual(search_traces("auth-service")[0]["trace_id"], "tr-auth-001")
        self.assertEqual(get_kubernetes_events("recommendation-service")[0]["reason"], "OOMKilled")
        self.assertEqual(get_config_changes("order-service")[0]["new_value"], "500")
        self.assertIn(
            "shipping-service", get_service_dependencies("order-service")[0]["dependencies"]
        )
        self.assertEqual(search_runbooks(service="media-service")[0]["runbook_id"], "RB-DISK")


class SchemaTests(unittest.TestCase):
    def test_provider_schemas_do_not_include_unsupported_keyword(self):
        schema_text = str(_gemini_schema(DiagnosticReport.model_json_schema()))
        self.assertNotIn("additionalProperties", schema_text)
        self.assertTrue(all("additionalProperties" not in str(tool) for tool in TOOLS))

    def test_invalid_confidence_is_rejected(self):
        with self.assertRaises(ValidationError):
            DiagnosticReport(
                status="confirmed",
                root_cause="example",
                confidence=1.5,
            )

    def test_extra_report_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            DiagnosticReport.model_validate(
                {
                    "status": "inconclusive",
                    "root_cause": None,
                    "confidence": 0.2,
                    "invented": True,
                }
            )


class EvaluationTests(unittest.TestCase):
    def test_corpus_has_twelve_distinct_scenarios(self):
        cases = load_cases()
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["case_id"] for case in cases}), 12)
        for case in cases:
            self.assertTrue(
                set(case["expected"]["required_tools"]).issubset(TOOL_FUNCTIONS),
                case["case_id"],
            )
            self.assertTrue(list_available_metrics(case["service"]), case["case_id"])
            self.assertTrue(search_logs(case["service"]), case["case_id"])

    def test_golden_checkout_report_passes(self):
        expected = load_cases()[0]["expected"]
        report = DiagnosticReport(
            status="confirmed",
            root_cause="Payment timeout was lowered to 3 seconds for the payment gateway.",
            confidence=0.92,
            evidence=[
                Evidence(
                    source_tool="get_git_diff",
                    observation="Payment timeout configuration changed",
                    reference="d9a3b45",
                ),
                Evidence(
                    source_tool="search_logs",
                    observation="Payment calls repeatedly exceeded 3000ms",
                    reference="2026-08-19T22:14:07Z",
                ),
                Evidence(
                    source_tool="get_metrics",
                    observation="Error rate peaked at 8.1 percent",
                    reference="2026-08-19T22:25:00Z",
                ),
            ],
            recommendations=[
                Recommendation(
                    action="Restore the previous timeout",
                    priority="immediate",
                    requires_human_approval=True,
                )
            ],
            similar_past_incident="INC-0091",
        )
        result = InvestigationResult(
            report=report,
            tool_calls=expected["required_tools"],
            turns=5,
        )
        self.assertTrue(evaluate_result(result, expected)["passed"])

    def test_inconclusive_report_is_rewarded_when_evidence_is_insufficient(self):
        case = next(
            item for item in load_cases() if item["case_id"] == "pricing-insufficient-evidence"
        )
        report = DiagnosticReport(
            status="inconclusive",
            root_cause=None,
            confidence=0.35,
            evidence=[
                Evidence(
                    source_tool="get_metrics",
                    observation="Latency reached 310ms",
                    reference="2026-08-19T11:05:00Z",
                ),
                Evidence(
                    source_tool="get_health_checks",
                    observation="Dependencies were healthy",
                    reference="2026-08-19T11:05:00Z",
                ),
            ],
            recommendations=[
                Recommendation(
                    action="Collect a longer trace window",
                    priority="follow-up",
                    requires_human_approval=True,
                )
            ],
        )
        result = InvestigationResult(
            report=report,
            tool_calls=case["expected"]["required_tools"],
            turns=4,
        )
        self.assertTrue(evaluate_result(result, case["expected"])["passed"])


if __name__ == "__main__":
    unittest.main()
