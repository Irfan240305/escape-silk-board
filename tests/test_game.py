import pytest
from game.game_state import create_game_state, CHECKIN_TIME
from game.rules import validate_response, apply_game_changes


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
        "hint": "Try negotiating the fare."
    }


def test_initial_state():
    state = create_game_state()

    assert state["time"] == 1140
    assert state["cash"] == 500
    assert state["battery"] == 4
    assert state["location"] == "silk_board"


def test_valid_response():
    response = sample_response()
    assert validate_response(response) == response


def test_apply_game_changes():
    state = create_game_state()
    apply_game_changes(state, sample_response())

    assert state["time"] == 1150
    assert state["cash"] == 450
    assert state["battery"] == 3
    assert state["location"] == "koramangala"
    assert state["turn"] == 1


def test_invalid_location():
    response = sample_response()
    response["newLocation"] = "moon"

    try:
        validate_response(response)
        assert False, "Invalid location should be rejected"
    except ValueError:
        pass


def test_cannot_generate_cash():
    response = sample_response()
    response["cashDelta"] = 100

    try:
        validate_response(response)
        assert False, "Positive cash delta should be rejected"
    except ValueError:
        pass


def test_missed_checkin():
    state = create_game_state()
    state["time"] = CHECKIN_TIME - 5

    response = sample_response()
    response["timeDelta"] = 10

    apply_game_changes(state, response)

    assert state["gameOver"] is True
    assert state["outcome"] == "lost"


if __name__ == "__main__":
    tests = [
        test_initial_state,
        test_valid_response,
        test_apply_game_changes,
        test_invalid_location,
        test_cannot_generate_cash,
        test_missed_checkin
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print("\nAll tests passed!")

def test_rejects_missing_required_fields():
    from game.rules import validate_response

    response = {
        "narration": "Ramesh Uncle looks at the traffic."
    }

    with pytest.raises(ValueError, match="missing required fields"):
        validate_response(response)


def test_rejects_invalid_time_delta():
    from game.rules import validate_response

    response = {
        "narration": "The auto moves forward.",
        "timeDelta": 100,
        "cashDelta": 0,
        "batteryDelta": 0,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": [],
        "inventoryRemove": [],
        "hint": "Keep moving."
    }

    with pytest.raises(ValueError, match="Time delta"):
        validate_response(response)


def test_rejects_invalid_inventory_type():
    from game.rules import validate_response

    response = {
        "narration": "Ramesh Uncle checks the bag.",
        "timeDelta": 10,
        "cashDelta": 0,
        "batteryDelta": 0,
        "newLocation": None,
        "locationLabel": "",
        "inventoryAdd": "samosa",
        "inventoryRemove": [],
        "hint": "Check your inventory."
    }

    with pytest.raises(ValueError, match="inventoryAdd must be a list"):
        validate_response(response)
