# ADR-0002: Human review with LangGraph interrupt and checkpoints

- Status: accepted
- Date: 2026-11-19

## Context

Some tickets must wait for a person, and that person may answer hours later from another process (the CLI, the API or a helpdesk UI). The run has to stop cleanly and continue exactly where it left off.

## Decision

The `human_review` node calls LangGraph's `interrupt()` with the redacted ticket, the proposal and the reasons. A checkpointer stores the paused run under the ticket id as the thread id: SQLite for the CLI and API, in memory for tests and evals. The reviewer's answer is passed back with `Command(resume=...)` and validated as a `ReviewDecision`, which can approve, reject or override the category and priority.

## Options considered

- A status column plus a second "finish" function: simple, but the workflow's state would live in two places.
- LangGraph interrupt with a checkpointer (chosen): the paused state, the history and the resume are part of the graph itself.

## Consequences

- The graph state holds plain JSON values only, so checkpoints don't depend on pickling custom classes.
- On resume LangGraph re-runs the paused node from the start, so the node opens its tracing span only after `interrupt()` returns. Otherwise every pause would show up as an error in the traces.
