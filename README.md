# ticket-triage-agent

[![CI](https://github.com/smitsohagiya/ticket-triage-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/smitsohagiya/ticket-triage-agent/actions/workflows/ci.yml)

A support-ticket triage agent built with LangGraph. It redacts personal data, flags prompt-injection attempts, proposes a category and priority, and pauses for a person whenever its review policy says so. Every step is traced with OpenTelemetry, and an eval suite with safety gates runs in CI.

## Why

Most agent demos show the happy path. In production the hard parts are the edges: personal data in the input, customers (or attackers) writing instructions into the text, and knowing when the agent must not act on its own. This repo is a small, complete version of the pattern I use at work on a healthcare AI pipeline: structured outputs, fixed thresholds and a human approval step before anything reaches a person. Here it is applied to support tickets.

## How it works

```mermaid
flowchart LR
    ticket[Ticket] --> screen[screen: redact PII, check for injection]
    screen --> classify[classify: rules or LLM]
    classify --> decide[decide: review policy]
    decide -->|no reasons| act[act: route, tag, draft reply]
    decide -->|any reason| review[human_review: interrupt]
    review --> act
```

- **Guardrails run before the model** ([ADR-0001](docs/decisions/ADR-0001-guardrails-before-the-model.md)). Emails, phone numbers and Luhn-valid card numbers are replaced with placeholders, and injection signals are detected in plain code, so the model, logs and traces only ever see redacted text.
- **The review policy is code, not a prompt.** Security tickets, urgent priority, low confidence, refunds over $500, ownership or deletion requests and suspected injection all go to a person. Ticket text can only make a review more likely.
- **Human review is a LangGraph `interrupt`** ([ADR-0002](docs/decisions/ADR-0002-human-review-with-interrupt.md)). Paused runs are checkpointed in SQLite, so a reviewer can approve, reject or override from the CLI or the API at any time, and the run continues where it stopped.
- **Classifiers are swappable** ([ADR-0003](docs/decisions/ADR-0003-rules-baseline-and-swappable-llm.md)): a deterministic rules baseline for CI, or any OpenAI-compatible LLM endpoint (OpenAI, Ollama, vLLM, a gateway) with a strict JSON schema.
- **Every step is traced** with OpenTelemetry (category, confidence, review reasons, queue), never with ticket text.

More detail in [docs/architecture.md](docs/architecture.md).

## Results

60 labelled tickets for a fictional invoicing app ([data/README.md](data/README.md)), including planted personal data and 4 prompt-injection attempts. `uv run triage eval --gate`:

| Metric | Rules baseline |
| --- | --- |
| Category accuracy | 92% |
| Priority accuracy (within one level) | 93% (100%) |
| Security and injection tickets sent to a person | **100%** (gate) |
| Injection recall / false positives | **100%** (gate) / 0% |
| PII left in redacted text | **0** (gate) |
| Review recall / precision | 100% / 73% |
| Routed without a person | 63% |

The rules baseline was written alongside these tickets, so its accuracy here is optimistic. The safety gates are the point: they come from the guardrails and the policy, so they hold whichever classifier runs, and CI fails if any of them slips.

## Quickstart

```bash
make setup
uv run triage run                                    # triage the 60 sample tickets
uv run triage pending                                # tickets waiting for a person
uv run triage review t046 --approve --priority urgent
uv run triage eval --gate                            # metrics and safety gates, as in CI
uv run triage serve                                  # HTTP API on port 8000
```

API: `POST /tickets`, `GET /tickets/{id}`, `POST /tickets/{id}/review` (`{"approved": true, "priority": "urgent"}`), `GET /health`.

### With an LLM

Any OpenAI-compatible endpoint works. With Ollama:

```bash
ollama pull qwen2.5:3b
TRIAGE_CLASSIFIER=llm TRIAGE_LLM_MODEL=qwen2.5:3b uv run triage eval --gate
```

For OpenAI, set `TRIAGE_LLM_BASE_URL=https://api.openai.com/v1`, `TRIAGE_LLM_API_KEY` and a model name.

### See the traces

```bash
docker compose up -d                                 # Jaeger
TRIAGE_TRACE_EXPORTER=otlp OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 uv run triage run
open http://localhost:16686
```

## Limitations

- 60 tickets is a small set, and one product's support queue. It shows the method rather than settling which model is best.
- The injection checks are heuristics and can be evaded. The policy limits the damage: a missed signal still cannot make the agent skip review for security, urgent or low-confidence tickets.
- The helpdesk is an in-memory stand-in. A real Zendesk or Jira client implements the small `Helpdesk` protocol.

## What I'd do next

- Run the same evals against a few hosted and local models and publish the comparison.
- Turn reviewer overrides into new labelled cases, so the eval set grows from production.
- Add an LLM-written reply draft step, with its own groundedness check.

## License

MIT
