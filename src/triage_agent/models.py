"""The data that flows through the agent."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    BILLING = "billing"
    BUG = "bug"
    ACCOUNT_ACCESS = "account_access"
    FEATURE_REQUEST = "feature_request"
    SECURITY = "security"
    HOW_TO = "how_to"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Tier(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Ticket(BaseModel):
    """An incoming support ticket."""

    id: str
    subject: str
    body: str
    tier: Tier = Tier.PRO

    @property
    def text(self) -> str:
        return f"{self.subject}\n\n{self.body}"


class TriageDecision(BaseModel):
    """What a classifier proposes for a ticket. ``confidence`` runs from 0 to 1."""

    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(max_length=300)


class ReviewDecision(BaseModel):
    """A reviewer's answer to a paused ticket. Leave a field empty to keep the proposal."""

    approved: bool
    category: Category | None = None
    priority: Priority | None = None
    note: str = ""


class Outcome(BaseModel):
    """What happened to a ticket once it left the agent."""

    ticket_id: str
    status: str
    category: Category
    priority: Priority
    queue: str
    tags: list[str]
    reviewed_by_human: bool
    review_reasons: list[str]
    reply_draft: str | None = None
