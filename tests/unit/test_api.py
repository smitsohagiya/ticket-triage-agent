from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from triage_agent.api import create_app
from triage_agent.classifiers import RulesClassifier
from triage_agent.graph import TriageAgent
from triage_agent.helpdesk import InMemoryHelpdesk

client = TestClient(create_app(TriageAgent(RulesClassifier(), InMemoryHelpdesk(), InMemorySaver())))


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok", "classifier": "rules"}


def test_submit_review_and_status() -> None:
    ticket = {
        "id": "a1",
        "subject": "Account taken over",
        "body": "Someone changed my password and email.",
    }
    submitted = client.post("/tickets", json=ticket).json()
    assert submitted["status"] == "waiting_for_review"

    reviewed = client.post("/tickets/a1/review", json={"approved": True})
    assert reviewed.status_code == 200
    assert reviewed.json()["outcome"]["queue"] == "on-call"
    assert client.get("/tickets/a1").json()["status"] == "routed"


def test_errors() -> None:
    assert client.get("/tickets/missing").status_code == 404
    client.post("/tickets", json={"id": "a2", "subject": "Logo", "body": "How do I add our logo?"})
    assert client.post("/tickets/a2/review", json={"approved": True}).status_code == 409
    assert client.post("/tickets/missing/review", json={"approved": True}).status_code == 404
