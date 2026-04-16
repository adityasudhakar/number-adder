from fastapi.testclient import TestClient

from number_adder import chat_agent
from number_adder.server import app, get_current_user_id_flexible


def test_rule_based_average_answer(monkeypatch):
    monkeypatch.setattr(chat_agent, "OPENAI_API_KEY", "")
    monkeypatch.setattr(
        chat_agent.db,
        "get_recent_calculations",
        lambda user_id, limit=10, operation=None: [
            {"result": 2.0, "operation": "add", "num_a": 1.0, "num_b": 1.0},
            {"result": 4.0, "operation": "add", "num_a": 2.0, "num_b": 2.0},
        ],
    )

    result = chat_agent.answer_question(123, "What's the average of my last 10 calculations?")

    assert result["source"] == "local"
    assert "average result" in result["answer"]
    assert "3.00" in result["answer"]


def test_chat_endpoint_returns_answer(monkeypatch):
    monkeypatch.setattr(
        "number_adder.server.answer_question",
        lambda user_id, message: {"answer": "The average is 3.00.", "source": "local"},
    )
    monkeypatch.setattr("number_adder.server.track_event", lambda *args, **kwargs: None)
    monkeypatch.setattr("number_adder.server.db.init_db", lambda: None)

    app.dependency_overrides[get_current_user_id_flexible] = lambda: 42
    client = TestClient(app)
    try:
        response = client.post(
            "/chat",
            json={"message": "What's the average of my last 10 calculations?"},
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        assert response.json() == {"answer": "The average is 3.00."}
    finally:
        app.dependency_overrides.clear()
