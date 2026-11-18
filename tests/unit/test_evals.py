from pathlib import Path

from triage_agent.evals import EvalReport, Prediction, evaluate, gate_failures, load_cases
from triage_agent.models import Category, Priority, Ticket

DATASET = Path(__file__).resolve().parents[2] / "data" / "tickets.jsonl"


def perfect(cases_by_id: dict[str, object]) -> object:
    def predict(ticket: Ticket) -> Prediction:
        case = cases_by_id[ticket.id]
        expected = case.expected  # type: ignore[attr-defined]
        return Prediction(
            category=expected.category,
            priority=expected.priority,
            confidence=0.9,
            review_reasons=["needs a person"] if expected.needs_human else [],
            injection_signals=["x"] if case.injection else [],  # type: ignore[attr-defined]
            redacted_text="clean text",
        )

    return predict


def test_a_perfect_agent_scores_full_marks_and_passes_the_gates() -> None:
    cases = load_cases(DATASET)
    report = evaluate(cases, perfect({c.id: c for c in cases}), "perfect")  # type: ignore[arg-type]
    assert report.cases == 60
    assert report.metrics["category_accuracy"] == 1.0
    assert report.metrics["review_recall"] == 1.0
    assert report.metrics["injection_false_positive_rate"] == 0.0
    assert gate_failures(report) == []


def test_a_pii_leak_fails_the_gate() -> None:
    cases = load_cases(DATASET)[:1]

    def leaky(ticket: Ticket) -> Prediction:
        return Prediction(
            category=Category.BILLING,
            priority=Priority.HIGH,
            confidence=0.9,
            review_reasons=[],
            injection_signals=[],
            redacted_text="mail me at a@example.com",
        )

    report: EvalReport = evaluate(cases, leaky, "leaky")
    assert report.metrics["pii_leaks"] == 1.0
    assert any(f.startswith("pii_leaks") for f in gate_failures(report))
