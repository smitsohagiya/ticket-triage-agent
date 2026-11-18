"""Flag ticket text that tries to give the agent new instructions.

These are deterministic heuristics, not a model, so they are fast, explainable and easy to test.
They do not have to catch everything: a flagged ticket simply goes to a person, and the policy
never lets ticket text change what the agent is allowed to do.
"""

import re
from dataclasses import dataclass

_SIGNALS: dict[str, re.Pattern[str]] = {
    "ignore_instructions": re.compile(
        r"\b(ignore|disregard|forget)\b[^.\n]{0,40}\b(instructions?|rules|prompts?|guidelines)\b",
        re.IGNORECASE,
    ),
    "mode_switch": re.compile(
        r"\byou are now\b[^.\n]{0,30}\bmode\b|\b(admin|developer|god|debug) mode\b",
        re.IGNORECASE,
    ),
    "prompt_extraction": re.compile(
        r"\b(reveal|show|print|repeat)\b[^.\n]{0,20}\b(system prompt|your (instructions|prompt))",
        re.IGNORECASE,
    ),
    "new_instructions": re.compile(
        r"#{2,}\s*new instructions|\bnew instructions\s*:", re.IGNORECASE
    ),
    "hidden_markup": re.compile(r"<!--.*?-->", re.DOTALL),
    "role_tag": re.compile(r"(^|\n)\s*(system|assistant)\s*:", re.IGNORECASE),
    "exfiltration": re.compile(
        r"\b(forward|send|post|upload)\b[^.\n]{0,60}https?://", re.IGNORECASE
    ),
}


@dataclass(frozen=True)
class InjectionCheck:
    """Whether the text looks like an injection attempt, and which signals matched."""

    suspicious: bool
    signals: tuple[str, ...]


def check_injection(text: str) -> InjectionCheck:
    """Run every signal over ``text``."""
    signals = tuple(name for name, pattern in _SIGNALS.items() if pattern.search(text))
    return InjectionCheck(suspicious=bool(signals), signals=signals)
