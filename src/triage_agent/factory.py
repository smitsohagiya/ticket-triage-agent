"""Build the classifier and the agent from settings."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from triage_agent.classifiers import Classifier, LLMClassifier, RulesClassifier
from triage_agent.config import Settings
from triage_agent.graph import TriageAgent
from triage_agent.helpdesk import Helpdesk


def build_classifier(settings: Settings) -> Classifier:
    """The rules baseline, or an LLM behind an OpenAI-compatible endpoint."""
    if settings.classifier == "llm":
        return LLMClassifier(settings.llm_base_url, settings.llm_model, settings.llm_api_key)
    return RulesClassifier()


def build_agent(
    settings: Settings, helpdesk: Helpdesk, checkpointer: BaseCheckpointSaver[Any]
) -> TriageAgent:
    return TriageAgent(
        build_classifier(settings), helpdesk, checkpointer, threshold=settings.review_threshold
    )
