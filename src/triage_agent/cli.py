"""Command-line entry point: triage tickets, answer reviews, run the evals and serve the API."""

import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from triage_agent import __version__
from triage_agent.api import create_app
from triage_agent.config import get_settings
from triage_agent.evals import EvalReport, Prediction, evaluate, gate_failures, load_cases
from triage_agent.factory import build_agent
from triage_agent.graph import TriageResult
from triage_agent.helpdesk import InMemoryHelpdesk
from triage_agent.log import configure_logging
from triage_agent.models import Category, Priority, ReviewDecision, Ticket
from triage_agent.telemetry import configure_tracing

app = typer.Typer(
    help="Triage support tickets with guardrails, human review and evals.", no_args_is_help=True
)


@app.callback()
def main() -> None:
    """Set up logging and tracing before any command runs."""
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings.trace_exporter)


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@contextmanager
def sqlite_saver(path: Path) -> Iterator[SqliteSaver]:
    """A checkpointer that keeps paused runs on disk between commands."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    try:
        yield SqliteSaver(conn)
    finally:
        conn.close()


def load_tickets(path: Path) -> list[Ticket]:
    """Read tickets from JSON lines. Extra fields such as labels are ignored."""
    tickets = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            tickets.append(
                Ticket.model_validate(
                    {k: row[k] for k in ("id", "subject", "body", "tier") if k in row}
                )
            )
    return tickets


def _line(result: TriageResult) -> str:
    text = (
        f"{result.ticket_id}  {result.status:18}  {result.decision.category.value:15}  "
        f"{result.decision.priority.value:6}  conf {result.decision.confidence:.2f}"
    )
    if result.review_reasons:
        text += "  review: " + "; ".join(result.review_reasons)
    return text


@app.command()
def run(
    file: Annotated[Path | None, typer.Argument(help="JSON lines file of tickets.")] = None,
) -> None:
    """Triage every ticket in FILE. Tickets that need a person wait for `triage review`."""
    settings = get_settings()
    tickets = load_tickets(file or settings.tickets_file)
    with sqlite_saver(settings.checkpoint_db) as saver:
        agent = build_agent(settings, InMemoryHelpdesk(), saver)
        for ticket in tickets:
            typer.echo(_line(agent.submit(ticket)))


@app.command()
def pending() -> None:
    """List tickets that are waiting for a review."""
    settings = get_settings()
    with sqlite_saver(settings.checkpoint_db) as saver:
        agent = build_agent(settings, InMemoryHelpdesk(), saver)
        threads = sorted({c.config["configurable"]["thread_id"] for c in saver.list(None)})
        waiting = [r for r in map(agent.status, threads) if r.status == "waiting_for_review"]
    for result in waiting:
        typer.echo(_line(result))
    if not waiting:
        typer.echo("No tickets are waiting for a review.")


@app.command()
def review(
    ticket_id: Annotated[str, typer.Argument(help="The paused ticket.")],
    approve: Annotated[
        bool, typer.Option("--approve/--reject", help="Route it, or close it.")
    ] = True,
    category: Annotated[Category | None, typer.Option(help="Override the category.")] = None,
    priority: Annotated[Priority | None, typer.Option(help="Override the priority.")] = None,
    note: Annotated[str, typer.Option(help="A note for the audit trail.")] = "",
) -> None:
    """Answer a paused ticket so its run can finish."""
    settings = get_settings()
    decision = ReviewDecision(approved=approve, category=category, priority=priority, note=note)
    with sqlite_saver(settings.checkpoint_db) as saver:
        result = build_agent(settings, InMemoryHelpdesk(), saver).resume(ticket_id, decision)
    queue = result.outcome.queue if result.outcome else "none"
    typer.echo(f"{ticket_id}: {result.status}, queue {queue}")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _print_report(report: EvalReport) -> None:
    typer.echo(f"classifier: {report.classifier}   tickets: {report.cases}")
    for metric, value in report.metrics.items():
        shown = f"{value:g}" if metric == "pii_leaks" else f"{value:.0%}"
        typer.echo(f"  {metric:30} {shown}")


@app.command("eval")
def eval_command(
    gate: Annotated[bool, typer.Option(help="Fail when a safety gate is not met.")] = False,
) -> None:
    """Score the agent on the labelled tickets and save the report."""
    settings = get_settings()
    agent = build_agent(settings, InMemoryHelpdesk(), InMemorySaver())

    def predict(ticket: Ticket) -> Prediction:
        result = agent.submit(ticket)
        return Prediction(
            category=result.decision.category,
            priority=result.decision.priority,
            confidence=result.decision.confidence,
            review_reasons=result.review_reasons,
            injection_signals=result.injection_signals,
            redacted_text=result.redacted_text,
        )

    report = evaluate(load_cases(settings.tickets_file), predict, agent.classifier.name)
    settings.results_dir.mkdir(parents=True, exist_ok=True)
    path = settings.results_dir / f"eval-{_slug(report.classifier)}.json"
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    _print_report(report)
    typer.echo(f"report: {path}")
    failures = gate_failures(report)
    for failure in failures:
        typer.echo(f"GATE FAILED: {failure}")
    if gate and failures:
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Interface to bind.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to listen on.")] = 8000,
) -> None:
    """Run the HTTP API."""
    import uvicorn

    settings = get_settings()
    with sqlite_saver(settings.checkpoint_db) as saver:
        uvicorn.run(
            create_app(build_agent(settings, InMemoryHelpdesk(), saver)), host=host, port=port
        )
