from triage_agent.guardrails import InjectionCheck
from triage_agent.models import Category, Priority, Ticket, TriageDecision
from triage_agent.policy import largest_amount, review_reasons

CLEAN = InjectionCheck(suspicious=False, signals=())


def decision(
    category: Category = Category.HOW_TO, priority: Priority = Priority.LOW, confidence: float = 0.9
) -> TriageDecision:
    return TriageDecision(category=category, priority=priority, confidence=confidence, summary="s")


def ticket(body: str) -> Ticket:
    return Ticket(id="t1", subject="Subject", body=body)


def test_a_clean_confident_ticket_needs_no_review() -> None:
    assert review_reasons(ticket("How do I add a logo?"), decision(), CLEAN, 0.7) == []


def test_every_reason_is_reported() -> None:
    reasons = review_reasons(
        ticket("Refund $1,200 and delete my account data under GDPR."),
        decision(Category.SECURITY, Priority.URGENT, 0.4),
        InjectionCheck(suspicious=True, signals=("ignore_instructions",)),
        0.7,
    )
    assert reasons == [
        "possible prompt injection: ignore_instructions",
        "security ticket",
        "urgent priority",
        "low confidence (0.40)",
        "refund over $500",
        "account ownership or data deletion request",
    ]


def test_small_refunds_are_routed_automatically() -> None:
    assert (
        review_reasons(
            ticket("Please refund the $29."),
            decision(Category.BILLING, Priority.NORMAL),
            CLEAN,
            0.7,
        )
        == []
    )


def test_largest_amount() -> None:
    assert largest_amount("paid $49 twice, then $1,200.50") == 1200.5
    assert largest_amount("no money here") == 0.0
