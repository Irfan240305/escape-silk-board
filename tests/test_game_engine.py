
import pytest

from game.game_engine import GameEngine


def sample_response():
    return {
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


def test_engine_starts_new_game():
    engine = GameEngine()

    state = engine.get_state()

    assert state["cash"] == 500
    assert state["battery"] == 4
    assert state["location"] == "silk_board"
    assert state["turn"] == 0


def test_engine_processes_turn():
    engine = GameEngine()

    result = engine.process_turn(sample_response())

    assert result["state"]["cash"] == 450
    assert result["state"]["battery"] == 3
    assert result["state"]["location"] == "koramangala"
    assert result["state"]["turn"] == 1


def test_engine_rejects_invalid_response():
    engine = GameEngine()
    response = sample_response()
    response["newLocation"] = "moon"

    with pytest.raises(ValueError):
        engine.process_turn(response)


def test_engine_reset():
    engine = GameEngine()
    engine.process_turn(sample_response())

    state = engine.reset()

    assert state["cash"] == 500
    assert state["battery"] == 4
    assert state["location"] == "silk_board"
    assert state["turn"] == 0


def test_engine_rejects_turn_after_game_over():
    engine = GameEngine()
    engine.state["time"] = 20 * 60 + 50

    response = sample_response()

    engine.process_turn(response)

    assert engine.is_game_over()
    assert engine.get_outcome() == "lost"

    with pytest.raises(ValueError):
        engine.process_turn(sample_response())
def test_engine_sells_samosa_correctly():
    engine = GameEngine()

    response = {
        "narration": "Ramesh Uncle sells the cold samosa.",
        "timeDelta": 10,
        "cashDelta": 100,
        "batteryDelta": 0,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": ["1 cold samosa"],
        "hint": "Keep moving towards the airport."
    }

    result = engine.process_turn(response)
    state = result["state"]

    assert state["cash"] == 600
    assert "1 cold samosa" not in state["inventory"]
    assert state["turn"] == 1

def test_engine_completes_airport_journey():
    engine = GameEngine()

    route = [
        "outer_ring_road",
        "hebbal",
        "airport_road",
        "airport",
    ]

    for destination in route:
        response = {
            "narration": f"Ramesh Uncle drives towards {destination}.",
            "timeDelta": 10,
            "cashDelta": -20,
            "batteryDelta": 0,
            "newLocation": destination,
            "locationLabel": destination.replace("_", " ").title(),
            "inventoryAdd": [],
            "inventoryRemove": [],
            "hint": "Keep moving towards the airport."
        }

        result = engine.process_turn(response)

    assert result["state"]["location"] == "airport"
    assert result["gameOver"] is True
    assert result["outcome"] == "won"
    assert engine.is_game_over()

def test_engine_loses_when_checkin_deadline_is_missed():
    engine = GameEngine()

    # Set the game clock to 8:50 PM.
    engine.state["time"] = 20 * 60 + 50

    response = {
        "narration": "Traffic wins. Ramesh Uncle shakes his head.",
        "timeDelta": 10,
        "cashDelta": 0,
        "batteryDelta": 0,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Better luck next flight, guru."
    }

    result = engine.process_turn(response)

    assert result["state"]["time"] == 21 * 60
    assert result["gameOver"] is True
    assert result["outcome"] == "lost"
    assert engine.is_game_over()

def test_engine_rejects_unaffordable_payment():
    engine = GameEngine()
    engine.state["cash"] = 50

    response = sample_response()
    response["cashDelta"] = -100

    with pytest.raises(ValueError, match="cannot spend more cash"):
        engine.process_turn(response)


def test_engine_never_allows_negative_battery():
    engine = GameEngine()
    engine.state["battery"] = 1

    response = sample_response()
    response["batteryDelta"] = -10

    result = engine.process_turn(response)

    assert result["state"]["battery"] == 0


def test_engine_rejects_invalid_inventory_removal():
    engine = GameEngine()

    response = sample_response()
    response["inventoryRemove"] = ["golden ticket"]

    with pytest.raises(ValueError, match="does not have item"):
        engine.process_turn(response)
def test_engine_rejects_duplicate_event():
    engine = GameEngine()

    response = sample_response()
    response["newLocation"] = None
    response["locationLabel"] = ""
    response["eventId"] = "auto_fare"
    response["eventChoice"] = "negotiate"
    response["cashDelta"] = -90
    response["timeDelta"] = 10
    response["batteryDelta"] = -1

    result = engine.process_turn(response)

    assert "auto_fare" in result["state"]["events_seen"]

    with pytest.raises(ValueError, match="already occurred"):
        engine.process_turn(response)

def test_engine_rejects_invalid_event_id():
    engine = GameEngine()

    response = sample_response()
    response["eventId"] = "invented_event"

    with pytest.raises(ValueError, match="Invalid event ID"):
        engine.process_turn(response)

def test_engine_rejects_event_from_wrong_location():
    engine = GameEngine()

    response = sample_response()
    response["eventId"] = "roadblock"

    with pytest.raises(ValueError, match="not available at this location"):
        engine.process_turn(response)

def test_character_memory_remembers_auto_fare_negotiation():
    engine = GameEngine()

    response = {
        "narration": "Ramesh Uncle agrees to the negotiated fare.",
        "timeDelta": 10,
        "cashDelta": -90,
        "batteryDelta": -1,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Keep moving.",
        "eventId": "auto_fare",
        "eventChoice": "negotiate",
    }

    result = engine.process_turn(
        response,
        "I negotiate carefully for a better fare."
    )

    memory = result["state"]["character_memory"]["ramesh_uncle"]

    assert "The player negotiated the auto fare." in memory["remembered_moments"]
    assert "resourceful" in memory["traits"]
    assert "cautious" in memory["traits"]
    assert memory["relationship"] == 0


def test_character_memory_updates_relationship_when_accepting_help():
    engine = GameEngine()
    engine.state["location"] = "hebbal"

    response = {
        "narration": "A local offers useful airport directions.",
        "timeDelta": 5,
        "cashDelta": 0,
        "batteryDelta": 0,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Follow the directions.",
        "eventId": "local_help",
        "eventChoice": "accept_directions",
    }

    result = engine.process_turn(response, "I accept the local's help.")

    memory = result["state"]["character_memory"]["ramesh_uncle"]

    assert memory["relationship"] == 1
    assert "cooperative" in memory["traits"]
    assert "The player accepted local directions at Hebbal." in memory["remembered_moments"]


def test_character_memory_resets_with_new_game():
    engine = GameEngine()

    response = {
        "narration": "Ramesh Uncle agrees to the negotiated fare.",
        "timeDelta": 10,
        "cashDelta": -90,
        "batteryDelta": -1,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Keep moving.",
        "eventId": "auto_fare",
        "eventChoice": "negotiate",
    }

    engine.process_turn(response, "I negotiate the fare.")

    state = engine.reset()
    memory = state["character_memory"]["ramesh_uncle"]

    assert memory["relationship"] == 0
    assert memory["traits"] == []
    assert memory["remembered_moments"] == []


def test_invalid_event_does_not_update_character_memory():
    engine = GameEngine()

    response = {
        "narration": "An invalid event occurs.",
        "timeDelta": 10,
        "cashDelta": 0,
        "batteryDelta": 0,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Try again.",
        "eventId": "invented_event",
        "eventChoice": "invented_choice",
    }

    with pytest.raises(ValueError):
        engine.process_turn(response, "I negotiate carefully.")

    memory = engine.get_state()["character_memory"]["ramesh_uncle"]

    assert memory["traits"] == []
    assert memory["remembered_moments"] == []
    assert memory["relationship"] == 0
