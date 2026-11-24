
from copy import deepcopy

from game.game_state import create_game_state
from game.rules import validate_response, apply_game_changes


class GameEngine:
    """Controls the authoritative state of one game session."""

    def __init__(self):
        self.state = create_game_state()
        self._ensure_character_memory()

    def _ensure_character_memory(self):
        """Initialize persistent character memory safely."""
        self.state.setdefault("character_memory", {})
        self.state["character_memory"].setdefault(
            "ramesh_uncle",
            {
                "relationship": 0,
                "traits": [],
                "remembered_moments": [],
            },
        )

    def get_state(self):
        """Return a copy so external code cannot modify the state."""
        return deepcopy(self.state)

    def _update_character_memory(self, player_action, ai_response):
        """Update Ramesh Uncle's memory using validated player decisions."""
        self._ensure_character_memory()

        memory = self.state["character_memory"]["ramesh_uncle"]
        action = (player_action or "").lower()

        event_id = ai_response.get("eventId")
        choice = ai_response.get("eventChoice")

        # Only record meaningful, observable behaviour.
        trait_signals = {
            "resourceful": [
                "negotiate", "bargain", "alternative", "shortcut",
                "detour", "figure out",
            ],
            "cautious": [
                "wait", "careful", "check", "conserve", "save battery",
            ],
            "decisive": [
                "quickly", "hurry", "go now", "let's go", "move",
            ],
            "cooperative": [
                "thank", "please", "help", "accept directions",
            ],
            "independent": [
                "ignore help", "do it myself", "on my own",
            ],
        }

        for trait, signals in trait_signals.items():
            if any(signal in action for signal in signals):
                if trait not in memory["traits"]:
                    memory["traits"].append(trait)

        # Record important event choices, not every ordinary turn.
        moment_map = {
            ("auto_fare", "negotiate"):
                "The player negotiated the auto fare.",
            ("auto_fare", "accept"):
                "The player accepted the auto driver's fare.",
            ("auto_fare", "refuse"):
                "The player refused the initial auto fare.",
            ("traffic_jam", "wait"):
                "The player waited through the traffic jam.",
            ("traffic_jam", "alternate_route"):
                "The player chose an alternate route through traffic.",
            ("roadblock", "wait_clearance"):
                "The player waited for the roadblock to clear.",
            ("roadblock", "take_detour"):
                "The player chose a detour around the roadblock.",
            ("local_help", "accept_directions"):
                "The player accepted local directions at Hebbal.",
            ("local_help", "ignore_help"):
                "The player ignored the local offer of help.",
            ("last_mile", "airport_shuttle"):
                "The player took the airport shuttle.",
            ("last_mile", "walk"):
                "The player chose to walk the last stretch.",
        }

        moment = moment_map.get((event_id, choice))

        if moment and moment not in memory["remembered_moments"]:
            memory["remembered_moments"].append(moment)

            # Keep only the five most recent meaningful moments.
            memory["remembered_moments"] = (
                memory["remembered_moments"][-5:]
            )

        # Relationship changes only for explicit, meaningful choices.
        relationship_changes = {
            ("local_help", "accept_directions"): 1,
            ("local_help", "ignore_help"): -1,
        }

        change = relationship_changes.get((event_id, choice), 0)

        memory["relationship"] = max(
            -5,
            min(5, memory["relationship"] + change),
        )

        
    def process_turn(self, ai_response, player_action=""):
        """Validate and apply one AI-generated turn."""

        if self.state["gameOver"]:
            raise ValueError("This game has already ended.")

        validate_response(ai_response)

        # Apply the turn exactly once.
        apply_game_changes(self.state, ai_response)

        # Make final narration agree with the authoritative outcome.
        if self.state["gameOver"]:
            if self.state["outcome"] == "lost":
                ai_response["narration"] = (
                    "The clock strikes past the check-in deadline. "
                    "Ramesh Uncle looks at the airport road and sighs. "
                    "The flight is gone, guru. Better luck next time."
                )
            else:
                ai_response["narration"] = (
                    "You made it to Kempegowda International Airport "
                    "before check-in closed! Ramesh Uncle grins. "
                    "Mission accomplished, guru!"
                )

        # Update memory after successful validation and application.
        self._update_character_memory(player_action, ai_response)

        self.state["history"].append({
            "turn": self.state["turn"],
            "player": player_action,
            "narration": ai_response["narration"],
        })

        return {
            "state": self.get_state(),
            "narration": ai_response["narration"],
            "hint": ai_response["hint"],
            "eventId": ai_response.get("eventId"),
            "gameOver": self.state["gameOver"],
            "outcome": self.state.get("outcome"),
        }


    def reset(self):
        """Start a fresh game with fresh character memory."""
        self.state = create_game_state()
        self._ensure_character_memory()
        return self.get_state()

    def is_game_over(self):
        return self.state["gameOver"]

    def get_outcome(self):
        return self.state.get("outcome")
