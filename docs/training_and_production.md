# Training and production path

## What has already been prepared

The repository now has a measurable improvement loop rather than an untestable
prompt:

- Strict Pydantic schemas for reports, evidence, and recommendations.
- Bounded turns and tool calls.
- Bounded provider request time and retry attempts.
- Allowlisted tools with validated arguments.
- Instructions that treat telemetry as untrusted data.
- Auditable tool traces.
- Twelve golden evaluation cases and a deterministic scorer, including one case where
  the correct result is inconclusive.
- Offline unit tests and an optional live model regression suite.
- A local FastAPI job API with durable SQLite status and result storage.
- A non-root container definition for repeatable local or staging deployment.

This is evaluation-driven development. It should precede model fine-tuning.

## Synthetic coverage currently included

- Payment timeout regression
- Inventory rate limiting under traffic
- Database connection-pool exhaustion
- Unbounded cache memory growth and OOMKilled pods
- CPU saturation at an autoscaling ceiling
- Upstream client-timeout mismatch
- Backward-incompatible serializer change
- Expired TLS certificate
- Temporary disk exhaustion
- Message-queue backlog after consumer scale-down
- Internal DNS configuration failure
- Insufficient evidence, requiring an inconclusive result

## Inputs the operator must provide

### 1. Sanitized historical incidents

Start with 20 incidents, then expand to at least 50-100. For every case provide:

- Original alert and timestamp.
- Affected and dependent services.
- Relevant metric windows.
- Relevant logs and traces.
- Deployments and configuration changes near the alert.
- Confirmed root cause from the postmortem.
- Resolution and whether rollback was safe.
- Distractor evidence that looked plausible but was not causal.
- Any period where the correct answer was "inconclusive."

Remove secrets, tokens, customer payloads, email addresses, and other personal data.
Do not copy raw production telemetry into the repository.

### 2. Read-only integration details

Choose the first provider in each category and supply read-only credentials through
a secret manager, never committed files:

- Metrics provider and query endpoint.
- Log provider and index/tenant information.
- Deployment source and repository mapping.
- Incident/postmortem store.
- Service catalog, ownership, and dependency map.

Document rate limits, retention windows, and the maximum query range permitted for
each system.

### 3. Operational policy

Define:

- Which services the agent may inspect.
- Data classifications it may read.
- Who may launch an investigation.
- Maximum investigation duration and cost.
- Confidence threshold for paging a human.
- Actions that are permanently forbidden.
- Actions that may later be offered behind human approval.

## Dataset acceptance checklist

A case is acceptable only when:

- The root cause was confirmed by a human postmortem.
- Evidence contains timestamps and stable references.
- The case includes enough pre-incident baseline data.
- Expected tool use is documented.
- Alternative hypotheses are represented.
- The expected answer does not depend on hidden tribal knowledge.

Split cases by incident, not individual log line: 70% development, 15% validation,
and 15% held-out test. Never tune prompts against the held-out set.

## Improvement sequence

1. Run the current prompt/model on all cases and save the baseline scores.
2. Categorize failures: retrieval, tool choice, correlation, hallucination, unsafe
   recommendation, or output formatting.
3. Fix connectors and deterministic correlation logic before changing the prompt.
4. Change one prompt or policy behavior at a time and rerun every case.
5. Add every real production failure as a regression case.
6. Add retrieval over runbooks and postmortems once source citations are available.
7. Consider provider fine-tuning only after a large stable dataset reveals a repeated
   model behavior that tools, retrieval, and prompting cannot fix.

## Production gates

Before connecting to production telemetry, require:

- Unit, integration, and live regression suites passing.
- No secrets or personal data in fixtures or model traces.
- Read-only scoped credentials and service-level authorization.
- Query timeout, pagination, result-size, and rate-limit enforcement.
- Persistent audit records for model, prompt version, tool calls, and sources.
- Monitoring for latency, API failures, token cost, and unsupported claims.
- A documented incident response path for the diagnostic system itself.

Before enabling remediation, additionally require an external approval workflow,
idempotency, dry-run support, rollback behavior, and immutable audit logs. Model text
alone must never authorize a production mutation.
