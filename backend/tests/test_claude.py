from fastapi.testclient import TestClient

from app import claude
from app.main import app

client = TestClient(app)


def test_hello_claude(monkeypatch):
    monkeypatch.setattr(claude, "ask", lambda system, prompt: "Hello from Claude!")
    response = client.get("/api/hello-claude")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Claude!", "model": claude.MODEL}


def test_hello_claude_unavailable(monkeypatch):
    def unavailable(system, prompt):
        raise claude.ClaudeUnavailable("Claude declined to answer that.")

    monkeypatch.setattr(claude, "ask", unavailable)
    response = client.get("/api/hello-claude")
    assert response.status_code == 503
    assert response.json() == {"detail": "Claude declined to answer that."}
