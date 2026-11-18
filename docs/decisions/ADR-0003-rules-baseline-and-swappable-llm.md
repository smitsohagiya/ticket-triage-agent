# ADR-0003: A rules baseline in CI, with LLMs behind the same interface

- Status: accepted
- Date: 2026-11-19

## Context

CI has to be deterministic, free and runnable without secrets. The agent should still work with a real LLM, and switching models should not touch the graph.

## Decision

Both classifiers implement one `Classifier` protocol:

- `RulesClassifier`: weighted keywords for the category and cue phrases for the priority. CI runs the eval suite with it, and the safety gates (no PII leaks, every security and injection ticket reviewed) have to pass.
- `LLMClassifier`: calls any OpenAI-compatible `/chat/completions` endpoint (OpenAI, Ollama, vLLM, a gateway) with a strict JSON schema, then validates the answer with Pydantic and clamps the confidence to the range 0 to 1.

## Consequences

- The baseline was written alongside the 60 sample tickets, so its accuracy on them is optimistic. Its job is to keep CI meaningful and to give LLMs a floor to beat, not to be a good classifier.
- The safety gates hold whichever classifier runs, because they come from the guardrails and the policy, not from the model.
