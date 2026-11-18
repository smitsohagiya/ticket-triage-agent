import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from triage_agent import __version__
from triage_agent.cli import app

runner = CliRunner()


def test_version() -> None:
    assert __version__ in runner.invoke(app, ["version"]).output


def test_run_pending_and_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tickets = tmp_path / "tickets.jsonl"
    rows = [
        {"id": "c1", "subject": "Logo", "body": "How do I add our logo to invoices?"},
        {"id": "c2", "subject": "XSS", "body": "Found a script tag vulnerability."},
    ]
    tickets.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setenv("TRIAGE_CHECKPOINT_DB", str(tmp_path / "cp.sqlite"))

    ran = runner.invoke(app, ["run", str(tickets)])
    assert ran.exit_code == 0, ran.output
    assert "c1  routed" in ran.output
    assert "c2  waiting_for_review" in ran.output

    waiting = runner.invoke(app, ["pending"])
    assert "c2" in waiting.output and "c1" not in waiting.output

    reviewed = runner.invoke(app, ["review", "c2", "--approve", "--priority", "urgent"])
    assert reviewed.exit_code == 0, reviewed.output
    assert "c2: routed, queue on-call" in reviewed.output
    assert "No tickets are waiting" in runner.invoke(app, ["pending"]).output


def test_eval_with_the_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGE_RESULTS_DIR", str(tmp_path))
    result = runner.invoke(app, ["eval", "--gate"])
    assert result.exit_code == 0, result.output
    assert "must_review_recall" in result.output
    assert (tmp_path / "eval-rules.json").exists()
