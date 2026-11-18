# ADR-0004: A deterministic security backstop in the review policy

- Status: accepted
- Date: 2026-11-19

## Context

Running the eval with a local `qwen2.5:3b` classifier failed the safety gate (`must_review_recall = 0.75`). Three security tickets were labelled billing or account access with confidence 0.9 to 1.0, so the policy routed them without a person. One of them was "Request for your SOC 2 report", labelled billing at confidence 1.0. Confidence scores from a model are not a safety mechanism.

## Decision

Add plain-code security signals next to the model: account compromise, unknown logins, leaked credentials, phishing, vulnerabilities, data exposure and compliance requests. When any of them match, the ticket goes to a person whatever category the classifier proposed. The signals can only add reviews, never remove them.

## Consequences

- With the backstop, the gate passes for both the rules baseline and `qwen2.5:3b`.
- The signals were written with this dataset in view. They are generic security phrases, and a dataset test checks both directions: every security ticket matches, and no other ticket does. A real deployment would grow the list from reviewed tickets.
- The model still chooses the category and priority, so a better model still improves routing. The backstop only guarantees that a weaker one can't skip review.
