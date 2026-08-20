import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools.mock_tools import (
    get_recent_deploys,
    get_git_diff,
    search_logs,
    get_metrics,
    get_past_incidents,
)

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TOOLS = [
    {
        "name": "get_recent_deploys",
        "description": "Get the most recent deploys for a service, most recent first.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "limit": {"type": "integer"}
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_git_diff",
        "description": "Get details of a specific commit by its commit_id, including files changed and commit message.",
        "parameters": {
            "type": "object",
            "properties": {
                "commit_id": {"type": "string"}
            },
            "required": ["commit_id"]
        }
    },
    {
        "name": "search_logs",
        "description": "Search logs for a service, optionally filtered by level (INFO/WARN/ERROR) and time range.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "level": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"}
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_metrics",
        "description": "Get a metric time series (e.g. error_rate_pct) for a service, optionally filtered by time range.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "metric": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"}
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_past_incidents",
        "description": "Search past incident history by keyword to find similar previous issues.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"}
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "get_recent_deploys": get_recent_deploys,
    "get_git_diff": get_git_diff,
    "search_logs": search_logs,
    "get_metrics": get_metrics,
    "get_past_incidents": get_past_incidents,
}

SYSTEM_PROMPT = """You are an on-call diagnostic agent for software services.
An alert has fired indicating an elevated error rate. Your job is to investigate autonomously:

1. Check recent deploys for the affected service.
2. Check the error metrics to understand the timing and severity of the issue.
3. Search error logs to see what's actually failing.
4. If a deploy looks suspicious, inspect its diff for details.
5. Check past incidents for similar patterns.

Use the tools available to you to gather evidence BEFORE concluding anything.
Once you have enough evidence, produce a final report in this exact format:

ROOT CAUSE: <one sentence>
EVIDENCE: <bullet points of what you found>
CONFIDENCE: <High/Medium/Low>
RECOMMENDATION: <specific action to take>
SIMILAR PAST INCIDENT: <if any, mention the incident_id and summary, else say "None found">
"""

gemini_tool = types.Tool(function_declarations=TOOLS)
config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[gemini_tool]
)


def run_diagnostic_agent(service: str, alert_message: str):
    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=f"Alert fired for service '{service}': {alert_message}\n\nPlease investigate and produce a root cause report.")]
        )
    ]

    print(f"\n🔍 Starting investigation for: {service}")
    print(f"Alert: {alert_message}\n")

    max_turns = 10
    for _ in range(max_turns):
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=config
        )

        candidate = response.candidates[0]
        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        for part in candidate.content.parts:
            if part.text:
                print(f"🧠 Agent reasoning: {part.text}\n")

        if not function_calls:
            final_text = "\n".join(p.text for p in candidate.content.parts if p.text)
            return final_text

        contents.append(candidate.content)

        tool_response_parts = []
        for fc in function_calls:
            tool_name = fc.name
            tool_input = dict(fc.args)
            print(f"🔧 Calling tool: {tool_name}({tool_input})")

            func = TOOL_FUNCTIONS.get(tool_name)
            result = func(**tool_input) if func else {"error": "Unknown tool"}

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": result}
                )
            )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "Investigation exceeded max turns without conclusion."


if __name__ == "__main__":
    report = run_diagnostic_agent(
        service="checkout-service",
        alert_message="Error rate exceeded 5% threshold at 2026-08-19T22:25:00Z"
    )
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(report)