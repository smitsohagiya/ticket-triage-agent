# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- LangGraph workflow: screen, classify, decide, human review (interrupt with SQLite checkpoints) and act.
- Guardrails: PII redaction (emails, phone numbers, Luhn-valid cards) and prompt-injection signals.
- Review policy for security, urgent, low-confidence, large-refund, ownership or deletion, and injection tickets.
- Rules baseline and an OpenAI-compatible LLM classifier with a strict JSON schema.
- Eval suite with safety gates (`triage eval --gate`), run in CI.
- CLI (`run`, `pending`, `review`, `eval`, `serve`), HTTP API and OpenTelemetry tracing.
