"""The interface every classifier implements."""

from typing import Protocol

from triage_agent.models import Ticket, TriageDecision


class Classifier(Protocol):
    """Proposes a decision for a ticket. ``text`` is the redacted subject and body."""

    name: str

    def classify(self, ticket: Ticket, text: str) -> TriageDecision: ...
