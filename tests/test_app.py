
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.game_sessions.clear()
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as test_client:
        yield test_client


def test_api_start_game(client):
    response = client.post("/api/start")

    assert response.status_code == 200
    data = response.get_json()

    assert data["state"]["cash"] == 500
    assert data["state"]["battery"] == 4
    assert data["state"]["location"] == "silk_board"


def test_api_get_state(client):
    client.post("/api/start")

    response = client.get("/api/state")

    assert response.status_code == 200
    assert response.get_json()["state"]["turn"] == 0


def test_api_rejects_empty_player_action(client):
    response = client.post(
        "/api/narrate",
        json={"playerAction": ""}
    )

    assert response.status_code == 400


def test_api_processes_valid_ai_response(client, monkeypatch):
    client.post("/api/start")

    ai_response = {
        "narration": "Ramesh Uncle finds an auto.",
        "timeDelta": 10,
        "cashDelta": -50,
        "batteryDelta": -1,
        "newLocation": "koramangala",
        "locationLabel": "Koramangala",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Negotiate the fare."
    }

    monkeypatch.setattr(
        app_module,
        "generate_narration",
        lambda state, action: ai_response
    )

    response = client.post(
        "/api/narrate",
        json={"playerAction": "Take me towards Koramangala."}
    )

    assert response.status_code == 200

    state = response.get_json()["state"]

    assert state["cash"] == 450
    assert state["battery"] == 3
    assert state["location"] == "koramangala"
    assert state["turn"] == 1


def test_api_rejects_malformed_ai_response(client, monkeypatch):
    client.post("/api/start")

    monkeypatch.setattr(
        app_module,
        "generate_narration",
        lambda state, action: {"narration": "Incomplete response"}
    )

    response = client.post(
        "/api/narrate",
        json={"playerAction": "Take me to the airport."}
    )

    assert response.status_code == 422

    state_response = client.get("/api/state")
    assert state_response.get_json()["state"]["turn"] == 0

def test_gemini_fallback_when_groq_fails(monkeypatch):
    expected = {"narration": "Ramesh Uncle finds a shortcut."}

    def fail_groq(description):
        raise RuntimeError("Groq unavailable")

    def succeed_gemini(description):
        return expected

    monkeypatch.setattr(app_module, "narrate_groq", fail_groq)
    monkeypatch.setattr(app_module, "narrate_gemini", succeed_gemini)

    result = app_module.generate_narration(
        app_module.GameEngine().get_state(),
        "Find a route to the airport."
    )

    assert result == expected


def test_error_when_both_ai_providers_fail(monkeypatch):
    def fail_provider(description):
        raise RuntimeError("Provider unavailable")

    monkeypatch.setattr(app_module, "narrate_groq", fail_provider)
    monkeypatch.setattr(app_module, "narrate_gemini", fail_provider)

    with pytest.raises(RuntimeError, match="Both AI providers failed"):
        app_module.generate_narration(
            app_module.GameEngine().get_state(),
            "Find a route to the airport."
        )
