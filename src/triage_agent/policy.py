"""When a ticket must wait for a person instead of being routed automatically.

The policy runs after the classifier and only reads the proposal, the guardrail results and the
ticket itself. Ticket text can make a review more likely, never less likely.
"""

import re

from triage_agent.guardrails import InjectionCheck, security_signals
from triage_agent.models import Category, Priority, Ticket, TriageDecision

REFUND_LIMIT = 500
_AMOUNT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
_IDENTITY_OR_DATA = re.compile(
    r"\baccount owner\b|\bdelet(e|ion)\b[^.\n]{0,40}\b(account|data)\b|\bgdpr\b", re.IGNORECASE
)


def largest_amount(text: str) -> float:
    """The largest dollar amount mentioned in ``text``, or 0."""
    amounts = [float(value.replace(",", "")) for value in _AMOUNT.findall(text)]
    return max(amounts, default=0.0)


def review_reasons(
    ticket: Ticket, decision: TriageDecision, injection: InjectionCheck, threshold: float
) -> list[str]:
    """Every reason this ticket needs a person. An empty list means route it automatically."""
    reasons: list[str] = []
    if injection.suspicious:
        reasons.append("possible prompt injection: " + ", ".join(injection.signals))
    if decision.category is Category.SECURITY:
        reasons.append("security ticket")
    elif signals := security_signals(ticket.text):
        reasons.append("security signals: " + ", ".join(signals))
    if decision.priority is Priority.URGENT:
        reasons.append("urgent priority")
    if decision.confidence < threshold:
        reasons.append(f"low confidence ({decision.confidence:.2f})")
    if "refund" in ticket.text.lower() and largest_amount(ticket.text) > REFUND_LIMIT:
        reasons.append(f"refund over ${REFUND_LIMIT}")
    if _IDENTITY_OR_DATA.search(ticket.text):
        reasons.append("account ownership or data deletion request")
    return reasons
