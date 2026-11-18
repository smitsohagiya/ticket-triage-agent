"""Actions the agent takes on the helpdesk once a decision is final.

``InMemoryHelpdesk`` stands in for a real system such as Zendesk or Jira Service Management. The
agent only depends on the ``Helpdesk`` protocol, so swapping in a real client is one class.
"""

from dataclasses import dataclass, field
from typing import Protocol

from triage_agent.models import Category, Outcome, Priority

QUEUES: dict[Category, str] = {
    Category.BILLING: "billing",
    Category.BUG: "engineering",
    Category.ACCOUNT_ACCESS: "support",
    Category.FEATURE_REQUEST: "product",
    Category.SECURITY: "security",
    Category.HOW_TO: "support",
}

REPLY_TEMPLATES: dict[Category, str] = {
    Category.HOW_TO: (
        "Thanks for reaching out. Here is the help article that covers this. "
        "Reply to this email if anything is unclear."
    ),
    Category.FEATURE_REQUEST: (
        "Thanks for the suggestion. We've shared it with the product team, and we'll let you "
        "know if it makes it onto the roadmap."
    ),
}


class Helpdesk(Protocol):
    """The helpdesk operations the agent needs."""

    def assign(self, ticket_id: str, queue: str, priority: Priority) -> None: ...

    def tag(self, ticket_id: str, tags: list[str]) -> None: ...

    def save_reply_draft(self, ticket_id: str, text: str) -> None: ...


@dataclass
class InMemoryHelpdesk:
    """Records every action so tests and demos can inspect them."""

    assignments: dict[str, tuple[str, Priority]] = field(default_factory=dict)
    tags: dict[str, list[str]] = field(default_factory=dict)
    drafts: dict[str, str] = field(default_factory=dict)

    def assign(self, ticket_id: str, queue: str, priority: Priority) -> None:
        self.assignments[ticket_id] = (queue, priority)

    def tag(self, ticket_id: str, tags: list[str]) -> None:
        existing = self.tags.setdefault(ticket_id, [])
        existing.extend(tag for tag in tags if tag not in existing)

    def save_reply_draft(self, ticket_id: str, text: str) -> None:
        self.drafts[ticket_id] = text


def apply_decision(
    helpdesk: Helpdesk,
    *,
    ticket_id: str,
    category: Category,
    priority: Priority,
    review_reasons: list[str],
    reviewed_by_human: bool,
    extra_tags: list[str],
) -> Outcome:
    """Route the ticket and tag it. Reply drafts are only written for tickets nobody reviewed."""
    queue = "on-call" if priority is Priority.URGENT else QUEUES[category]
    tags = [category.value, f"priority:{priority.value}", *extra_tags]
    if reviewed_by_human:
        tags.append("human-reviewed")
    helpdesk.assign(ticket_id, queue, priority)
    helpdesk.tag(ticket_id, tags)
    draft = None if reviewed_by_human else REPLY_TEMPLATES.get(category)
    if draft:
        helpdesk.save_reply_draft(ticket_id, draft)
    return Outcome(
        ticket_id=ticket_id,
        status="routed",
        category=category,
        priority=priority,
        queue=queue,
        tags=tags,
        reviewed_by_human=reviewed_by_human,
        review_reasons=review_reasons,
        reply_draft=draft,
    )
