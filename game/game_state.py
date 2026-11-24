
from copy import deepcopy

INITIAL_STATE = {
    "time": 19 * 60,  # 7:00 PM
    "battery": 4,
    "cash": 500,
    "inventory": ["1 cold samosa"],
    "location": "silk_board",
    "locationLabel": "Silk Board junction",
    "turn": 0,
    "history": [],
    "events_seen": [],
    "character_memory": {
        "ramesh_uncle": {
            "relationship": 0,
            "traits": [],
            "remembered_moments": []
        }
    },
    "gameOver": False
}

CHECKIN_TIME = 20 * 60 + 55  # 8:55 PM

VALID_LOCATIONS = {
    "silk_board",
    "koramangala",
    "hsr_layout",
    "btm_layout",
    "outer_ring_road",
    "hebbal",
    "airport_road",
    "airport",
    "random_gully"
}

# Legal travel connections between locations.
# The AI may only move the player along these connections.

LOCATION_ROUTES = {
    "silk_board": {
        "koramangala",
        "hsr_layout",
        "btm_layout",
        "outer_ring_road",
        "random_gully"
    },
    "koramangala": {
        "silk_board",
        "hsr_layout",
        "btm_layout",
        "outer_ring_road",
        "random_gully"
    },
    "hsr_layout": {
        "silk_board",
        "koramangala",
        "btm_layout",
        "outer_ring_road",
        "random_gully"
    },
    "btm_layout": {
        "silk_board",
        "koramangala",
        "hsr_layout",
        "outer_ring_road",
        "random_gully"
    },
    "outer_ring_road": {
        "silk_board",
        "koramangala",
        "hsr_layout",
        "btm_layout",
        "hebbal",
        "random_gully"
    },
    "hebbal": {
        "outer_ring_road",
        "airport_road"
    },
    "airport_road": {
        "hebbal",
        "airport"
    },
    "airport": {
        "airport_road"
    },
    "random_gully": {
        "silk_board",
        "koramangala",
        "hsr_layout",
        "btm_layout",
        "outer_ring_road"
    }
}


def create_game_state():
    """Return a fresh, independent game state for a new playthrough."""
    return deepcopy(INITIAL_STATE)
