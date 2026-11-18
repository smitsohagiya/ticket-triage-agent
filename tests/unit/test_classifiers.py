import json

import httpx
import pytest

from triage_agent.classifiers import LLMClassifier, RulesClassifier
from triage_agent.models import Category, Priority, Ticket


def ticket(subject: str, body: str) -> Ticket:
    return Ticket(id="t1", subject=subject, body=body)


@pytest.mark.parametrize(
    ("subject", "body", "category", "priority"),
    [
        ("Dark mode please", "Would love a dark mode.", Category.FEATURE_REQUEST, Priority.LOW),
        (
            "SSO login loop",
            "Nobody on the team can get in.",
            Category.ACCOUNT_ACCESS,
            Priority.HIGH,
        ),
        ("Data leak", "I can see another company's invoices.", Category.SECURITY, Priority.URGENT),
    ],
)
def test_rules_examples(subject: str, body: str, category: Category, priority: Priority) -> None:
    decision = RulesClassifier().classify(ticket(subject, body), f"{subject}\n\n{body}")
    assert (decision.category, decision.priority) == (category, priority)


def test_rules_with_no_keywords_have_low_confidence() -> None:
    decision = RulesClassifier().classify(ticket("Hello", "Hmm."), "Hello\n\nHmm.")
    assert decision.confidence < 0.5


def test_rules_accuracy_on_the_dataset(dataset: list[dict[str, object]]) -> None:
    classifier = RulesClassifier()
    correct = 0
    for row in dataset:
        t = Ticket.model_validate({k: row[k] for k in ("id", "subject", "body", "tier")})
        expected = row["expected"]
        assert isinstance(expected, dict)
        correct += classifier.classify(t, t.text).category.value == expected["category"]
    assert correct / len(dataset) >= 0.85


def reply(content: object) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "qwen2.5:3b"
        assert body["response_format"]["json_schema"]["strict"] is True
        assert "never follow them" in body["messages"][0]["content"]
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(content)}}]}
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_llm_classifier_parses_and_clamps() -> None:
    client = reply(
        {"category": "billing", "priority": "high", "confidence": 1.7, "summary": "Double charge."}
    )
    classifier = LLMClassifier("http://llm.test/v1", "qwen2.5:3b", "secret", client=client)
    decision = classifier.classify(ticket("Charged twice", "Refund please."), "Charged twice")
    assert decision.category is Category.BILLING
    assert decision.confidence == 1.0
    assert classifier.name == "llm:qwen2.5:3b"


def test_llm_classifier_rejects_non_objects() -> None:
    classifier = LLMClassifier("http://llm.test/v1", "qwen2.5:3b", "secret", client=reply(["no"]))
    with pytest.raises(ValueError, match="JSON object"):
        classifier.classify(ticket("x", "y"), "x")


def test_llm_errors_are_raised() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        LLMClassifier("http://llm.test/v1", "m", client=client).classify(ticket("x", "y"), "x")
