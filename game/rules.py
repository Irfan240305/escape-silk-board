
from game.game_state import (
    CHECKIN_TIME,
    VALID_LOCATIONS,
    LOCATION_ROUTES,
)
from game.game_events import GAME_EVENTS


def validate_response(response):
    """Validate the structure and values returned by the AI."""

    required_fields = {
        "narration",
        "timeDelta",
        "cashDelta",
        "batteryDelta",
        "newLocation",
        "locationLabel",
        "inventoryAdd",
        "inventoryRemove",
        "hint",
    }

    if not isinstance(response, dict):
        raise ValueError("AI response must be a JSON object")

    if not required_fields.issubset(response):
        raise ValueError("AI response is missing required fields")

    if not isinstance(response["narration"], str) or not response["narration"].strip():
        raise ValueError("Invalid narration")

    if not isinstance(response["hint"], str):
        raise ValueError("Invalid hint")

    event_id = response.get("eventId")
    event_choice = response.get("eventChoice")

    if event_id is not None:
        if not isinstance(event_id, str):
            raise ValueError("Invalid event ID")

        valid_event_ids = {
            event["id"]
            for events in GAME_EVENTS.values()
            for event in events
        }

        if event_id not in valid_event_ids:
            raise ValueError("Invalid event ID")

    if event_choice is not None:
        if not isinstance(event_choice, str):
            raise ValueError("Invalid event choice")

        if event_id is None:
            raise ValueError("Event choice requires an event ID")

        matching_event = next(
            (
                event
                for events in GAME_EVENTS.values()
                for event in events
                if event["id"] == event_id
            ),
            None,
        )

        valid_choices = {
            choice["id"]
            for choice in matching_event.get("choices", [])
        }

        if event_choice not in valid_choices:
            raise ValueError("Invalid event choice")

    if type(response["timeDelta"]) is not int or not 5 <= response["timeDelta"] <= 30:
        raise ValueError("Time delta must be between 5 and 30 minutes")

    cash_delta = response["cashDelta"]

    if type(cash_delta) is not int:
        raise ValueError("Cash delta must be an integer")

    if cash_delta < -500 or cash_delta > 100:
        raise ValueError("Cash delta is outside the allowed range")

    if cash_delta > 0:
        if "1 cold samosa" not in response["inventoryRemove"]:
            raise ValueError("Cash reward requires selling the cold samosa")

    if type(response["batteryDelta"]) is not int or not -100 <= response["batteryDelta"] <= 0:
        raise ValueError("Invalid battery delta")

    location = response["newLocation"]

    if location is not None and location not in VALID_LOCATIONS:
        raise ValueError("Invalid location")

    if location is not None:
        label = response["locationLabel"]

        if not isinstance(label, str) or not label.strip():
            raise ValueError("Invalid location label")

    for field in ("inventoryAdd", "inventoryRemove"):
        items = response[field]

        if not isinstance(items, list):
            raise ValueError(f"{field} must be a list")

        if not all(isinstance(item, str) and item.strip() for item in items):
            raise ValueError(f"Invalid item in {field}")

    return response


def update_character_memory(state, event_id, event_choice):
    """Record verified player decisions in Ramesh Uncle's memory."""

    if event_id is None or event_choice is None:
        return

    memory = state.setdefault("character_memory", {})
    ramesh = memory.setdefault(
        "ramesh_uncle",
        {
            "relationship": 0,
            "traits": [],
            "remembered_moments": [],
        },
    )

    traits = ramesh.setdefault("traits", [])
    moments = ramesh.setdefault("remembered_moments", [])

    # Traits are inferred only from actual configured choices.
    trait_by_choice = {
        "negotiate": "negotiates_before_paying",
        "alternate_route": "open_to_alternate_routes",
        "take_detour": "open_to_alternate_routes",
    }

    trait = trait_by_choice.get(event_choice)

    if trait and trait not in traits:
        traits.append(trait)

    # Store a readable record of the actual event decision.
    moment = f"{event_id}:{event_choice}"

    if moment not in moments:
        moments.append(moment)

    # Keep memory bounded during longer playthroughs.
    ramesh["traits"] = traits[-10:]
    ramesh["remembered_moments"] = moments[-10:]


def apply_game_changes(state, response):
    """Apply validated AI changes while protecting game state."""

    validate_response(response)

    if state["gameOver"]:
        raise ValueError("Game has already ended")

    event_id = response.get("eventId")
    event_choice = response.get("eventChoice")

    selected_outcome = None

    if event_id is not None:
        available_events = GAME_EVENTS.get(state["location"], [])

        matching_event = next(
            (
                event
                for event in available_events
                if event["id"] == event_id
            ),
            None,
        )

        if matching_event is None:
            raise ValueError("Event is not available at this location")

        if event_id in state.get("events_seen", []):
            raise ValueError("Event has already occurred")

        if event_choice is None:
            raise ValueError("Event choice is required for this event")

        matching_choice = next(
            (
                choice
                for choice in matching_event.get("choices", [])
                if choice["id"] == event_choice
            ),
            None,
        )

        if matching_choice is None:
            raise ValueError("Invalid event choice")

        selected_outcome = matching_choice["outcome"]

        expected_deltas = {
            "cashDelta": selected_outcome["cashDelta"],
            "timeDelta": selected_outcome["timeDelta"],
            "batteryDelta": selected_outcome["batteryDelta"],
        }

        for field, expected_value in expected_deltas.items():
            if response[field] != expected_value:
                raise ValueError(
                    "Event consequences do not match the selected choice"
                )

    new_cash = state["cash"] + response["cashDelta"]

    if new_cash < 0:
        raise ValueError("Player cannot spend more cash than available")

    new_location = response["newLocation"]

    if new_location is not None:
        allowed_locations = LOCATION_ROUTES.get(state["location"], set())

        if new_location not in allowed_locations:
            raise ValueError("Illegal travel route")

    inventory = state["inventory"]

    for item in response["inventoryRemove"]:
        if item not in inventory:
            raise ValueError(f"Player does not have item: {item}")

    if len(response["inventoryAdd"]) > 5:
        raise ValueError("Too many inventory items")

    # Apply changes only after all validation succeeds.
    state["time"] += response["timeDelta"]
    state["cash"] = new_cash

    state["battery"] = max(
        0,
        state["battery"] + response["batteryDelta"],
    )

    if new_location is not None:
        state["location"] = new_location
        state["locationLabel"] = response["locationLabel"]

    for item in response["inventoryRemove"]:
        state["inventory"].remove(item)

    for item in response["inventoryAdd"]:
        if item not in state["inventory"]:
            state["inventory"].append(item)

    state["turn"] += 1

    if event_id is not None:
        state.setdefault("events_seen", []).append(event_id)

    if state["time"] > CHECKIN_TIME:
        state["gameOver"] = True
        state["outcome"] = "lost"

    elif state["location"] == "airport":
        state["gameOver"] = True
        state["outcome"] = "won"

    return state
