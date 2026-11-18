"""A deterministic keyword baseline.

It keeps CI repeatable without a model or an API key, and it gives LLM classifiers a floor to
beat. It was written alongside the sample tickets, so its scores on them are optimistic.
"""

from triage_agent.models import Category, Priority, Ticket, TriageDecision

_TERMS: dict[Category, dict[str, float]] = {
    Category.SECURITY: {
        "phishing": 3,
        "data leak": 3,
        "leak": 2,
        "vulnerab": 3,
        "xss": 3,
        "taken over": 3,
        "someone is in my account": 3,
        "changed my password and email": 3,
        "unknown device": 2,
        "login from a country": 3,
        "soc 2": 3,
        "security": 2,
        "public github": 3,
        "revoke": 2,
        "another company": 3,
        "re-enter card": 3,
        "script tag": 3,
    },
    Category.ACCOUNT_ACCESS: {
        "password": 2,
        "2fa": 3,
        "locked": 2,
        "log in": 2,
        "login": 1,
        "sso": 3,
        "invite": 2,
        "account owner": 3,
        "verification": 2,
        "suspended": 2,
        "gdpr": 3,
        "deletion": 2,
        "session expired": 3,
        "get back into": 3,
        "can't get in": 2,
    },
    Category.BILLING: {
        "charged": 2,
        "refund": 2,
        "vat": 3,
        "billing": 2,
        "billed": 2,
        "payment": 2,
        "declined": 2,
        "receipt": 3,
        "subscription": 2,
        "plan": 1,
        "prorat": 3,
        "currency": 2,
        "discount": 2,
        "renewal": 1,
        "cancel": 1,
        "invoices to": 1,
        "pay yearly": 3,
    },
    Category.BUG: {
        "error": 2,
        "500": 2,
        "crash": 3,
        "blank": 2,
        "white page": 3,
        "not syncing": 3,
        "slow": 2,
        "stopped": 2,
        "fails": 2,
        "429": 3,
        "webhook": 2,
        "rounding": 3,
        "off by": 2,
        "one day earlier": 3,
        "does nothing": 3,
        "same number": 3,
        "invalid header": 3,
        "nothing arrives": 2,
    },
    Category.FEATURE_REQUEST: {
        "would love": 3,
        "could you add": 3,
        "would help": 2,
        "would be great": 3,
        "do you plan": 3,
        "would save": 3,
        "we need a": 1,
        "could you post": 3,
        "dark mode": 2,
        "pagination": 2,
    },
    Category.HOW_TO: {
        "how do i": 2,
        "how can i": 2,
        "where can i": 2,
        "where do i": 2,
        "can ledgerline": 3,
        "is there a way": 2,
    },
}

_URGENT = (
    "data leak",
    "another company",
    "taken over",
    "changed my password and email",
    "revoke it immediately",
    "tax compliance",
    "same number",
    "someone is in my account",
)
_HIGH = (
    "nobody",
    "whole team",
    "locked",
    "declined",
    "charged twice",
    "not syncing",
    "internal server error",
    "2fa",
    "lost my phone",
    "dispute",
    "read-only",
    "unknown device",
    "phishing",
    "vulnerab",
    "script tag",
    "loop",
    "can't log in",
    "admin mode",
    "payment fails",
)
_LOW_CATEGORIES = (Category.FEATURE_REQUEST, Category.HOW_TO)


class RulesClassifier:
    """Scores each category by weighted keyword matches and sets priority from cue phrases."""

    name = "rules"

    def classify(self, ticket: Ticket, text: str) -> TriageDecision:
        lowered = text.lower()
        scores = {
            category: sum(weight for term, weight in terms.items() if term in lowered)
            for category, terms in _TERMS.items()
        }
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        (category, top), (_, second) = ranked[0], ranked[1]
        if top == 0:
            return TriageDecision(
                category=Category.HOW_TO,
                priority=Priority.NORMAL,
                confidence=0.3,
                summary="No category keywords matched.",
            )
        confidence = round(0.5 + 0.5 * (top - second) / top, 2)
        return TriageDecision(
            category=category,
            priority=self._priority(category, lowered),
            confidence=confidence,
            summary=f"Matched {category.value} keywords (score {top:g} vs {second:g}).",
        )

    def _priority(self, category: Category, lowered: str) -> Priority:
        if any(cue in lowered for cue in _URGENT):
            return Priority.URGENT
        if any(cue in lowered for cue in _HIGH):
            return Priority.HIGH
        if category in _LOW_CATEGORIES or "discount" in lowered:
            return Priority.LOW
        return Priority.NORMAL
