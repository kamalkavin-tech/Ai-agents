# Sentinel Ops Agent

Sentinel is a read-only, evidence-driven incident diagnostic agent. It correlates
deployments, metrics, logs, traces, Kubernetes events, configuration, health checks,
dependencies, runbooks, and past incidents, then returns a strictly validated JSON
diagnosis with an auditable tool trace.

## Current scope

The repository currently uses JSON-backed mock connectors and twelve incident
scenarios. The agent cannot make production changes. This is intentional: read-only
investigation should be reliable and measurable before remediation is introduced.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
```

Configure `GEMINI_API_KEY` in `.env`. Optional settings are:

```text
GEMINI_MODEL=gemini-3.6-flash
AGENT_MAX_TURNS=10
AGENT_MAX_TOOL_CALLS=25
AGENT_REQUEST_TIMEOUT_MS=60000
```

## Run an investigation

```powershell
.\venv\Scripts\python.exe main.py inventory-service "Error rate exceeded 5% threshold at 2026-08-19T19:06:00Z"
```

## Run the local API

```powershell
.\venv\Scripts\uvicorn.exe app.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation. Create a
job with:

```powershell
$body = @{
  service = "inventory-service"
  alert_message = "Error rate exceeded 5% at 2026-08-19T19:06:00Z"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/investigations `
  -ContentType application/json `
  -Body $body
```

Use the returned id with `GET /investigations/{id}`. Job state and validated results
are persisted to `data/investigations.db`, which is excluded from Git.

The local API has no authentication and must remain bound to `127.0.0.1`. Add an
identity-aware gateway and authorization before exposing it to a network.

## Container

```powershell
docker build -t sentinel-ops-agent .
docker run --rm -p 127.0.0.1:8000:8000 `
  -e GEMINI_API_KEY="your-development-key" `
  sentinel-ops-agent
```

Prefer an injected secret or mounted secret file over command-line environment values
outside local development.

## Verify locally

The unit suite does not call the model or require network access:

```powershell
.\venv\Scripts\python.exe -m unittest discover -v
```

Run the live model regression suite only when API usage is intended:

```powershell
.\venv\Scripts\python.exe -m evaluation.evaluator
.\venv\Scripts\python.exe -m evaluation.evaluator --case inventory-rate-limit
```

The live suite covers twelve failure modes and exits non-zero if required tools,
facts, citations, confidence, status, or safety properties are missing. Provider
errors are recorded per case so one outage does not discard completed evaluations.

## Adding an evaluation case

1. Add sanitized telemetry fixtures under `data/`.
2. Add a case to `evaluation/cases.json`.
3. Record only facts confirmed in the real postmortem.
4. Include evidence that distinguishes the root cause from plausible distractors.
5. Run the unit and live regression suites before accepting prompt or model changes.

See [docs/training_and_production.md](docs/training_and_production.md) for the
data required from operators and the path from evaluation to production.
