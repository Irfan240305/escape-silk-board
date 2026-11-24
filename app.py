
import json
import os
import re
import uuid

from flask import Flask, jsonify, request, send_from_directory, session
from dotenv import load_dotenv
from groq import Groq
from google import genai

from game.game_engine import GameEngine
from game.game_state import LOCATION_ROUTES
from collections import deque

load_dotenv()

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-before-deployment")

# One GameEngine per browser session (in-memory for this prototype).
game_sessions = {}


SYSTEM_PROMPT = """You are the narrator of "Escape Silk Board", a text adventure set in Bengaluru, India.

PERSONALITY:
You are Ramesh Uncle, a veteran Bengaluru auto driver.
Use dry wit, Bengaluru slang and occasional Kannada/Hindi words.
Narrate in third person.
Be entertaining, natural and concise.

SETTING:
- Starting location: Silk Board, Bengaluru.
- Starting time: 7:00 PM.
- Flight departure: 9:40 PM.
- Check-in closes: 8:55 PM.
- Destination: Kempegowda International Airport.

GAME RULES:
- The player must reach the airport before 8:55 PM.
- Battery at 0 means the phone is dead.
- Battery above 0 means the phone is still usable.
- Cash at 0 means the player cannot make cash payments.
- Never invent cash, battery, inventory or locations.
- Never teleport the player.
- Only move to a legal connected destination.
- Prefer the recommended shortest route.
- Time must advance by 5 to 30 minutes per turn.
- Keep the game fair, challenging, funny and winnable.
- Consider the player's actual resources before suggesting an action.
- Never promise an unaffordable journey.

ECONOMY RULES:
- cashDelta represents the exact change in the player's cash.
- Expenses must use a negative cashDelta.
- No payment means cashDelta must be 0.
- A positive cashDelta is permitted only when selling the cold samosa.
- Selling the cold samosa may reward at most Rs.100.
- A samosa sale must remove the exact inventory item "1 cold samosa".
- Never claim a payment occurred unless cashDelta is negative.
- Never claim a reward unless cashDelta is positive.
- Never invent a fare or claim that a payment was made.
- The game state's cash value is authoritative.

INVENTORY RULES:
- Use exact inventory item names supplied in the current game state.
- Never invent or rename inventory items.
- If an item is consumed, traded or surrendered, include its exact name in inventoryRemove.
- If no item is used, inventoryRemove must be [].
- Never claim an item was consumed or traded unless it is removed.
- Never mention a specific fare amount in narration unless it exactly equals the absolute value of cashDelta.
- Never name a destination in narration that differs from newLocation and locationLabel.
- Describe only events that are represented by the JSON state changes.
- If uncertain about a fare or destination, do not invent details.
BATTERY RULES:
- batteryDelta must be zero or negative.
- Never say the phone is dead when battery is above 0.
- Never claim UPI or phone apps are unavailable unless battery is 0.

NARRATION RULES:
- Write 2 to 4 vivid, witty sentences.
- Narration must describe the actual proposed state changes.
- Do not exaggerate fares, rewards, travel time or battery consumption.
- Avoid mentioning numerical fares or payments in narration.
- The application's displayed game state is the source of truth.
- Keep Ramesh Uncle's personality consistent.

RESPONSE FORMAT:
Return exactly one valid JSON object with these fields:
{
  "narration": "2-4 vivid, witty sentences",
  "timeDelta": 10,
  "cashDelta": -50,
  "batteryDelta": -1,
  "newLocation": "koramangala",
  "locationLabel": "Koramangala",
  "inventoryAdd": [],
  "inventoryRemove": [],
  "hint": "One-line hint in Ramesh Uncle's voice",
  "eventId": null,
  "eventChoice": null
}
EVENT CHOICE RULES:
- Only use event IDs and choices supplied in POSSIBLE EVENTS AT THIS LOCATION.
- When the player clearly selects an event choice, return its exact eventId and eventChoice.
- If eventId is provided, eventChoice is mandatory.
- The cashDelta, timeDelta and batteryDelta MUST exactly match the selected choice's outcome.
- Never modify, invent, or add to the configured consequences.
- If the player has not selected an event choice, return null for both eventId and eventChoice.
- Never mark an event as completed merely because you narrated or introduced it.
- Never repeat an event already encountered.
- Never invent events or choices.

EVENT TRACKING:
- eventId must match an ID from the supplied possible events.
- Use null if no event occurs during this turn.
- Only report an event when it actually occurs in the narration.
- Never repeat an event already encountered.
VALIDATION REQUIREMENTS:
- timeDelta must be an integer from 5 to 30.
- cashDelta must be an integer from -500 to 100.
- Positive cashDelta is allowed only for a valid cold samosa sale.
- batteryDelta must be an integer from -100 to 0.
- newLocation must be a legal connected location or null.
- inventoryAdd and inventoryRemove must be arrays of strings.
- Return JSON only, without Markdown or additional text.
- Never claim that more time has passed than the timeDelta in your JSON response.
- If the player repeatedly refuses to move, narrate the consequences accurately using the current game time.
- Encourage progress toward the airport; do not repeatedly reward waiting or inaction.
"""

def get_shortest_path(start, destination="airport"):
    """Find the shortest legal route using the game route map."""

    queue = deque([[start]])
    visited = {start}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == destination:
            return path

        for neighbor in LOCATION_ROUTES.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return []

def extract_json(text):
    """Extract a JSON object from the model response."""
    match = re.search(r"\{[\s\S]*\}", text)

    if not match:
        raise ValueError("AI returned no JSON object")

    return json.loads(match.group(0))



def build_state_description(state, player_action):
    """Build an AI prompt with navigation, conversation and character memory."""

    hours, minutes = divmod(state["time"], 60)
    time_label = (
        f"{hours % 12 or 12}:{minutes:02d} "
        f"{'AM' if hours < 12 else 'PM'}"
    )

    allowed_destinations = sorted(
        LOCATION_ROUTES.get(state["location"], set())
    )

    shortest_path = get_shortest_path(
        state["location"],
        "airport"
    )

    recommended_next = (
        shortest_path[1] if len(shortest_path) > 1 else None
    )

    from game.game_events import get_events_for_location

    events_seen = state.get("events_seen", [])

    available_events = [
        event
        for event in get_events_for_location(state["location"])
        if event["id"] not in events_seen
    ]

    # Recent conversation memory.
    recent_history = state.get("history", [])[-6:]

    conversation_memory = "\n".join(
        f"Turn {item['turn']}: Player: {item['player']} "
        f"Ramesh Uncle: {item['narration']}"
        for item in recent_history
    ) or "No previous conversations."

    # Persistent character memory.
    character_memory = state.get("character_memory", {})
    ramesh_memory = character_memory.get("ramesh_uncle", {})

    remembered_traits = ramesh_memory.get("traits", [])
    remembered_moments = ramesh_memory.get("remembered_moments", [])
    relationship = ramesh_memory.get("relationship", 0)

    character_memory_description = f"""
RAMESH UNCLE'S MEMORY:
Relationship score: {relationship}
Remembered player traits: {remembered_traits or "No established traits yet."}
Remembered moments: {remembered_moments or "No memorable interactions yet."}

CHARACTER MEMORY RULES:
- Treat these memories as established facts from previous interactions.
- Let Ramesh Uncle naturally recognise the player's established behaviour.
- Occasionally refer to a relevant remembered moment in dialogue.
- Adapt his tone subtly based on the player's established traits.
- Do not invent memories, traits, promises or past interactions.
- Do not claim to remember something that is not listed here.
- Do not repeat the same memory reference in every response.
- Never change the memory or relationship score yourself.
"""

    return f"""
CURRENT GAME STATE:
Time: {time_label}
Minutes until check-in closes: {max(0, 20 * 60 + 55 - state['time'])}
Location: {state['locationLabel']} ({state['location']})
Battery: {state['battery']}%
Cash: Rs.{state['cash']}
PHONE STATUS: {
    "Dead. No phone apps or UPI." if state["battery"] == 0
    else "Critically low. Conserve battery." if state["battery"] <= 5
    else "Low battery. Use phone carefully." if state["battery"] <= 20
    else "Phone is usable."
}
CASH STATUS: Rs.{state["cash"]} is available for cash payments. Never describe the player as broke when cash is available.
Inventory: {', '.join(state['inventory']) if state['inventory'] else 'empty'}
Turn: {state['turn']}

RECENT CONVERSATION:
{conversation_memory}

CONVERSATION MEMORY RULES:
- Remember previous player decisions and conversations.
- Maintain continuity with earlier events.
- Never contradict established facts.
- Do not repeat information unnecessarily.
- Use conversation history as context, not as a replacement for current game state.

{character_memory_description}

POSSIBLE EVENTS AT THIS LOCATION:
{available_events}

EVENT RULES:
- Only use events supplied under POSSIBLE EVENTS AT THIS LOCATION.
- Present meaningful choices from the supplied event choices.
- Only set eventId and eventChoice when the player actually selects a choice.
- If no choice is selected, return null for both eventId and eventChoice.
- Never mark an event as completed merely by introducing or narrating it.
- When a choice is selected, its cashDelta, timeDelta and batteryDelta MUST exactly match its configured outcome.
- Never modify or invent event consequences.
- Never repeat events listed in events_seen.
- Respect the player's current time, cash, battery and inventory.

LEGAL DESTINATIONS:
{allowed_destinations}

SHORTEST LEGAL PATH TO AIRPORT:
{shortest_path}

RECOMMENDED NEXT DESTINATION:
{recommended_next}

NAVIGATION RULES:
- Never choose an illegal destination.
- Prefer the recommended next destination.
- Do not move backwards or create unnecessary detours.
- Consider the player's action and available resources.
- Never invent routes, cash or battery.
- If no movement is appropriate, use null for newLocation.


CONVERSATIONAL PLAYER ACTIONS:
- The player may ask questions, discuss previous events, or test Ramesh Uncle's memory.
- These are valid gameplay turns, not invalid actions.
- Answer the player's question naturally in narration.
- For a conversation-only turn, use these exact values:
  - timeDelta: 5
  - cashDelta: 0
  - batteryDelta: 0
  - newLocation: null
  - locationLabel: null
  - inventoryAdd: []
  - inventoryRemove: []
  - eventId: null
  - eventChoice: null
- narration must always be a non-empty string.
- hint must always be a non-empty string.
- Never return null for narration, hint, timeDelta, cashDelta or batteryDelta.
- Use established character memory when answering questions about previous interactions.

PLAYER ACTION:
{player_action}

Return valid JSON only using the required response schema.
"""


def narrate_groq(state_description):
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": state_description},
        ],
        temperature=0.4,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    return extract_json(response.choices[0].message.content)


def narrate_gemini(state_description):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=state_description,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "temperature": 0.9,
            "max_output_tokens": 500,
        },
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return extract_json(response.text)


def generate_narration(state, player_action):
    state_description = build_state_description(state, player_action)

    try:
        result = narrate_groq(state_description)
        print("Narration provider: Groq")
        return result

    except Exception as groq_error:
        print(f"Groq failed: {groq_error}")

    try:
        result = narrate_gemini(state_description)
        print("Narration provider: Gemini")
        return result

    except Exception as gemini_error:
        print(f"Gemini failed: {gemini_error}")
        raise RuntimeError("Both AI providers failed") from gemini_error


def get_game_engine():
    """Get or create the engine for this browser session."""
    if "game_id" not in session:
        session["game_id"] = str(uuid.uuid4())

    game_id = session["game_id"]

    if game_id not in game_sessions:
        game_sessions[game_id] = GameEngine()

    return game_sessions[game_id]


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/start")
def start_game():
    engine = get_game_engine()
    state = engine.reset()
    return jsonify({"state": state})


@app.get("/api/state")
def get_state():
    engine = get_game_engine()
    return jsonify({"state": engine.get_state()})


@app.post("/api/narrate")
def api_narrate():
    data = request.get_json(silent=True) or {}
    player_action = data.get("playerAction")

    if not isinstance(player_action, str) or not player_action.strip():
        return jsonify({"error": "A player action is required"}), 400

    if len(player_action) > 500:
        return jsonify({"error": "Player action is too long"}), 400

    engine = get_game_engine()

    if engine.is_game_over():
        return jsonify({"error": "This game has already ended"}), 409

    try:
        # Always use the server-owned state, never the browser's gameState.
        current_state = engine.get_state()

        ai_response = generate_narration(
            current_state,
            player_action.strip(),
        )

        # Validate and apply the AI response through the game engine.
        print("RAW AI RESPONSE:", json.dumps(ai_response, indent=2))
        result = engine.process_turn(ai_response, player_action.strip())
        

        # Preserve the existing response fields for the current frontend.
        return jsonify({
            **ai_response,
            **result,
        })

    except ValueError as error:
        print(f"Rejected game response: {error}")
        return jsonify({"error": str(error)}), 422

    except Exception as error:
        print(f"Turn failed: {error}")
        return jsonify({
            "error": "The narrator is temporarily unavailable. Please try again."
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
