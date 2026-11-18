"""Redact personal data before a ticket reaches a model or a log line."""

import re
from dataclasses import dataclass

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CARD = re.compile(r"(?<![\w-])\d(?:[ -]?\d){12,18}(?![\w-])")
_PHONE = re.compile(r"(?<![\w$])\+?\d[\d ().-]{7,}\d(?![\w-])")


@dataclass(frozen=True)
class Redaction:
    """The redacted text and the kinds of personal data that were removed, in order."""

    text: str
    found: tuple[str, ...]


def luhn_valid(digits: str) -> bool:
    """True when ``digits`` passes the Luhn checksum used by payment cards."""
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def redact(text: str) -> Redaction:
    """Replace card numbers, email addresses and phone numbers with placeholders.

    Card numbers must pass the Luhn check, so order and invoice numbers stay readable. Phone
    numbers need 9 to 15 digits, which keeps years, amounts and short codes untouched.
    """
    found: list[str] = []

    def card(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group())
        if luhn_valid(digits):
            found.append("card")
            return "[CARD]"
        return match.group()

    def email(_: re.Match[str]) -> str:
        found.append("email")
        return "[EMAIL]"

    def phone(match: re.Match[str]) -> str:
        if 9 <= len(re.sub(r"\D", "", match.group())) <= 15:
            found.append("phone")
            return "[PHONE]"
        return match.group()

    text = _CARD.sub(card, text)
    text = _EMAIL.sub(email, text)
    text = _PHONE.sub(phone, text)
    return Redaction(text=text, found=tuple(dict.fromkeys(found)))
