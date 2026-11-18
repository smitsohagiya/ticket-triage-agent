"""The triage workflow as a LangGraph state machine.

    screen -> classify -> decide -> human_review (only when the policy asks) -> act

``human_review`` pauses the run with ``interrupt``. The checkpointer stores the paused state, so a
person can answer minutes or days later, from another process, and the run continues from there.
State holds plain JSON-compatible values only, so checkpoints never depend on custom pickling.
"""

from typing import Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from triage_agent.classifiers import Classifier
from triage_agent.guardrails import InjectionCheck, check_injection, redact
from triage_agent.helpdesk import Helpdesk, apply_decision
from triage_agent.models import Outcome, ReviewDecision, Ticket, TriageDecision
from triage_agent.policy import review_reasons
from triage_agent.telemetry import tracer


class TriageState(TypedDict, total=False):
    ticket: dict[str, Any]
    redacted_text: str
    pii_found: list[str]
    injection_signals: list[str]
    decision: dict[str, Any]
    review_reasons: list[str]
    review: dict[str, Any]
    outcome: dict[str, Any]


class TriageResult(BaseModel):
    """Where a ticket stands: routed, rejected by a reviewer, or waiting for a review."""

    ticket_id: str
    status: Literal["routed", "rejected", "waiting_for_review"]
    decision: TriageDecision
    review_reasons: list[str]
    redacted_text: str
    pii_found: list[str]
    injection_signals: list[str]
    outcome: Outcome | None = None


def build_graph(
    classifier: Classifier, helpdesk: Helpdesk, threshold: float
) -> StateGraph[TriageState]:
    """Wire the five steps together. Each step records an OpenTelemetry span."""

    def screen(state: TriageState) -> TriageState:
        ticket = Ticket.model_validate(state["ticket"])
        with tracer.start_as_current_span("triage.screen") as span:
            redaction = redact(ticket.text)
            injection = check_injection(ticket.text)
            span.set_attribute("ticket.id", ticket.id)
            span.set_attribute("pii.kinds", list(redaction.found))
            span.set_attribute("injection.signals", list(injection.signals))
        return {
            "redacted_text": redaction.text,
            "pii_found": list(redaction.found),
            "injection_signals": list(injection.signals),
        }

    def classify(state: TriageState) -> TriageState:
        ticket = Ticket.model_validate(state["ticket"])
        with tracer.start_as_current_span("triage.classify") as span:
            decision = classifier.classify(ticket, state["redacted_text"])
            span.set_attribute("classifier", classifier.name)
            span.set_attribute("decision.category", decision.category.value)
            span.set_attribute("decision.priority", decision.priority.value)
            span.set_attribute("decision.confidence", decision.confidence)
        return {"decision": decision.model_dump(mode="json")}

    def decide(state: TriageState) -> TriageState:
        ticket = Ticket.model_validate(state["ticket"])
        signals = tuple(state["injection_signals"])
        with tracer.start_as_current_span("triage.decide") as span:
            reasons = review_reasons(
                ticket,
                TriageDecision.model_validate(state["decision"]),
                InjectionCheck(suspicious=bool(signals), signals=signals),
                threshold,
            )
            span.set_attribute("review.required", bool(reasons))
            span.set_attribute("review.reasons", reasons)
        return {"review_reasons": reasons}

    def route(state: TriageState) -> Literal["human_review", "act"]:
        return "human_review" if state["review_reasons"] else "act"

    def human_review(state: TriageState) -> TriageState:
        # interrupt() pauses here. On resume LangGraph runs this node again and interrupt()
        # returns the reviewer's answer, so the span starts only after the answer arrives.
        answer = interrupt(
            {
                "ticket_id": state["ticket"]["id"],
                "redacted_text": state["redacted_text"],
                "proposal": state["decision"],
                "reasons": state["review_reasons"],
            }
        )
        review = ReviewDecision.model_validate(answer)
        with tracer.start_as_current_span("triage.human_review") as span:
            span.set_attribute("review.approved", review.approved)
        return {"review": review.model_dump(mode="json")}

    def act(state: TriageState) -> TriageState:
        decision = TriageDecision.model_validate(state["decision"])
        review = ReviewDecision.model_validate(state["review"]) if state.get("review") else None
        extra = (["pii-redacted"] if state["pii_found"] else []) + (
            ["injection-flagged"] if state["injection_signals"] else []
        )
        with tracer.start_as_current_span("triage.act") as span:
            if review is not None and not review.approved:
                outcome = Outcome(
                    ticket_id=state["ticket"]["id"],
                    status="rejected",
                    category=decision.category,
                    priority=decision.priority,
                    queue="none",
                    tags=["rejected-by-reviewer", *extra],
                    reviewed_by_human=True,
                    review_reasons=state["review_reasons"],
                )
                helpdesk.tag(outcome.ticket_id, outcome.tags)
            else:
                outcome = apply_decision(
                    helpdesk,
                    ticket_id=state["ticket"]["id"],
                    category=(review.category if review else None) or decision.category,
                    priority=(review.priority if review else None) or decision.priority,
                    review_reasons=state["review_reasons"],
                    reviewed_by_human=review is not None,
                    extra_tags=extra,
                )
            span.set_attribute("outcome.status", outcome.status)
            span.set_attribute("outcome.queue", outcome.queue)
        return {"outcome": outcome.model_dump(mode="json")}

    builder = StateGraph(TriageState)
    builder.add_node("screen", screen)
    builder.add_node("classify", classify)
    builder.add_node("decide", decide)
    builder.add_node("human_review", human_review)
    builder.add_node("act", act)
    builder.add_edge(START, "screen")
    builder.add_edge("screen", "classify")
    builder.add_edge("classify", "decide")
    builder.add_conditional_edges("decide", route, ["human_review", "act"])
    builder.add_edge("human_review", "act")
    builder.add_edge("act", END)
    return builder


class TriageAgent:
    """Runs tickets through the graph, one thread per ticket id."""

    def __init__(
        self,
        classifier: Classifier,
        helpdesk: Helpdesk,
        checkpointer: BaseCheckpointSaver[Any],
        threshold: float = 0.7,
    ) -> None:
        self.classifier = classifier
        self._graph = build_graph(classifier, helpdesk, threshold).compile(
            checkpointer=checkpointer
        )

    def submit(self, ticket: Ticket) -> TriageResult:
        """Triage a new ticket. It either finishes or pauses for a review."""
        config = _config(ticket.id)
        self._graph.invoke({"ticket": ticket.model_dump(mode="json")}, config)
        return self.status(ticket.id)

    def resume(self, ticket_id: str, review: ReviewDecision) -> TriageResult:
        """Give a paused ticket the reviewer's answer and let the run finish."""
        if self.status(ticket_id).status != "waiting_for_review":
            raise ValueError(f"ticket {ticket_id} is not waiting for a review")
        self._graph.invoke(Command(resume=review.model_dump(mode="json")), _config(ticket_id))
        return self.status(ticket_id)

    def status(self, ticket_id: str) -> TriageResult:
        """The current state of a ticket's run."""
        snapshot = self._graph.get_state(_config(ticket_id))
        values: dict[str, Any] = dict(snapshot.values)
        if "decision" not in values:
            raise KeyError(f"no run for ticket {ticket_id}")
        outcome = Outcome.model_validate(values["outcome"]) if values.get("outcome") else None
        if snapshot.next:
            status: Literal["routed", "rejected", "waiting_for_review"] = "waiting_for_review"
        else:
            status = "rejected" if outcome and outcome.status == "rejected" else "routed"
        return TriageResult(
            ticket_id=ticket_id,
            status=status,
            decision=TriageDecision.model_validate(values["decision"]),
            review_reasons=values.get("review_reasons", []),
            redacted_text=values["redacted_text"],
            pii_found=values["pii_found"],
            injection_signals=values["injection_signals"],
            outcome=outcome,
        )


def _config(ticket_id: str) -> Any:
    return {"configurable": {"thread_id": ticket_id}}
