"""HTTP API: submit tickets, check their status and answer reviews."""

from fastapi import FastAPI, HTTPException

from triage_agent.graph import TriageAgent, TriageResult
from triage_agent.models import ReviewDecision, Ticket


def create_app(agent: TriageAgent) -> FastAPI:
    """Build the API around an agent, so tests can pass in their own."""
    app = FastAPI(title="ticket-triage-agent", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "classifier": agent.classifier.name}

    @app.post("/tickets")
    def submit(ticket: Ticket) -> TriageResult:
        return agent.submit(ticket)

    @app.get("/tickets/{ticket_id}")
    def status(ticket_id: str) -> TriageResult:
        try:
            return agent.status(ticket_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/tickets/{ticket_id}/review")
    def review(ticket_id: str, decision: ReviewDecision) -> TriageResult:
        try:
            return agent.resume(ticket_id, decision)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return app
