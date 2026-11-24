
GAME_EVENTS = {
    "silk_board": [
        {
            "id": "auto_fare",
            "title": "The Auto Driver",
            "description": "An auto driver offers to take you towards the airport.",
            "choices": [
                {
                    "id": "negotiate",
                    "label": "Negotiate a lower fare",
                    "outcome": {
                        "cashDelta": -90,
                        "timeDelta": 10,
                        "batteryDelta": -1
                    }
                },
                {
                    "id": "accept",
                    "label": "Accept the quoted fare",
                    "outcome": {
                        "cashDelta": -120,
                        "timeDelta": 5,
                        "batteryDelta": -1
                    }
                },
                {
                    "id": "refuse",
                    "label": "Refuse and look for another ride",
                    "outcome": {
                        "cashDelta": 0,
                        "timeDelta": 15,
                        "batteryDelta": -1
                    }
                }
            ]
        },
        {
            "id": "traffic_jam",
            "title": "Silk Board Traffic",
            "description": "Traffic is barely moving.",
            "choices": [
                {
                    "id": "wait",
                    "label": "Wait for traffic to clear",
                    "outcome": {
                        "cashDelta": 0,
                        "timeDelta": 15,
                        "batteryDelta": 0
                    }
                },
                {
                    "id": "alternate_route",
                    "label": "Take an alternative route",
                    "outcome": {
                        "cashDelta": -40,
                        "timeDelta": 10,
                        "batteryDelta": -1
                    }
                }
            ]
        }
    ],

    "outer_ring_road": [
        {
            "id": "roadblock",
            "title": "Unexpected Roadblock",
            "description": "A roadblock slows your journey.",
            "choices": [
                {
                    "id": "wait_clearance",
                    "label": "Wait for the roadblock to clear",
                    "outcome": {
                        "cashDelta": 0,
                        "timeDelta": 15,
                        "batteryDelta": 0
                    }
                },
                {
                    "id": "take_detour",
                    "label": "Pay for an alternative detour",
                    "outcome": {
                        "cashDelta": -40,
                        "timeDelta": 10,
                        "batteryDelta": -1
                    }
                }
            ]
        }
    ],

    "hebbal": [
        {
            "id": "local_help",
            "title": "A Helpful Local",
            "description": "A local offers information that could help you reach the airport.",
            "choices": [
                {
                    "id": "accept_directions",
                    "label": "Accept the local's directions",
                    "outcome": {
                        "cashDelta": 0,
                        "timeDelta": 5,
                        "batteryDelta": 0
                    }
                },
                {
                    "id": "ignore_help",
                    "label": "Ignore the offer and continue",
                    "outcome": {
                        "cashDelta": 0,
                        "timeDelta": 10,
                        "batteryDelta": -1
                    }
                }
            ]
        }
    ],

    "airport_road": [
        {
            "id": "last_mile",
            "title": "The Final Stretch",
            "description": "You are close to the airport, but the final stretch needs careful planning.",
            "choices": [
                {
                    "id": "airport_shuttle",
                    "label": "Take the airport shuttle",
                    "outcome": {
                        "cashDelta": -50,
                        "timeDelta": 10,
                        "batteryDelta": 0
                    }
                },
                {
                    "id": "walk",
                    "label": "Walk towards the terminal",
                    "outcome": {
                        "cashDelta": 0,
                        "timeDelta": 15,
                        "batteryDelta": 0
                    }
                }
            ]
        }
    ]
}


def get_events_for_location(location):
    """Return possible gameplay events at the current location."""
    return GAME_EVENTS.get(location, [])
