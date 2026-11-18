"""Security signals that force a human review, whatever category the classifier proposes.

A smaller model can label "Request for your SOC 2 report" as billing with full confidence. The
review policy should not depend on the model getting that right, so these checks run in plain
code next to the model and can only add reviews, never remove them.
"""

import re

_SIGNALS: dict[str, re.Pattern[str]] = {
    "account_compromise": re.compile(
        r"someone (is|was) in my account|taken over|takeover|hacked|"
        r"changed my password and email|unauthori[sz]ed (access|login|charges?)",
        re.IGNORECASE,
    ),
    "unknown_access": re.compile(
        r"login from (a|an|another)\b[^.\n]{0,30}\b(country|location|device)|"
        r"unknown (device|location)|unrecognized (login|device)",
        re.IGNORECASE,
    ),
    "credential_exposure": re.compile(
        r"(api key|secret|token|password)[^.\n]{0,60}\b(leak|leaked|public|exposed|pushed)|"
        r"\b(leak|leaked|exposed|pushed)[^.\n]{0,60}(api key|secret|token)",
        re.IGNORECASE,
    ),
    "phishing": re.compile(r"phishing|re-enter (card|password|credentials)", re.IGNORECASE),
    "vulnerability": re.compile(
        r"vulnerab|\bxss\b|script tag|sql injection|\bexploit", re.IGNORECASE
    ),
    "data_exposure": re.compile(
        r"another (company|customer)'s|data leak|someone else's (data|invoices)", re.IGNORECASE
    ),
    "compliance_request": re.compile(
        r"\bsoc ?2\b|iso ?27001|penetration test report|security questionnaire", re.IGNORECASE
    ),
}


def security_signals(text: str) -> tuple[str, ...]:
    """Names of the security signals found in ``text``, in a fixed order."""
    return tuple(name for name, pattern in _SIGNALS.items() if pattern.search(text))
