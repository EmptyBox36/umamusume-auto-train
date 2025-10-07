import Levenshtein
import json
from pathlib import Path

from utils.log import info, warning, error, debug
from main import info
from utils.strings import clean_event_name 
import core.state as state

EVENT_TOTALS = {}
SKILL_HINT_BY_EVENT = {}
CHARACTER_BY_EVENT = {}
CHARACTERS_EVENT_DATABASE = {}
SUPPORT_EVENT_DATABASE = {}

def load_event_databases():
    # hard reset all indices and views
    EVENT_TOTALS.clear()
    SKILL_HINT_BY_EVENT.clear()
    CHARACTER_BY_EVENT.clear()

    # keep object identity for modules holding references
    CHARACTERS_EVENT_DATABASE.clear()
    SUPPORT_EVENT_DATABASE.clear()

    """Load event data for trainee and support cards."""
    info("Loading event databases...")

    CHARACTERS_EVENT_DATABASE.clear()
    CHARACTERS_EVENT_DATABASE.update(index_json("./scraper/data/characters.json"))

    SUPPORT_EVENT_DATABASE.clear()
    SUPPORT_EVENT_DATABASE.update(index_json("./scraper/data/supports.json"))

    chars = sorted({c for c in CHARACTER_BY_EVENT.values() if c})
    info(f"characters indexed: {len(chars)} -> {chars[:5]}{'...' if len(chars)>5 else ''}")
    info(f"character-event entries: {sum(1 for c in CHARACTER_BY_EVENT.values() if c)}")

def index_json(path: str):
    p = Path(path)
    if not p.exists():
        return {}

    trainee = (state.TRAINEE_NAME or "").strip().casefold()
    data = json.loads(p.read_text(encoding="utf-8"))
    result = {}

    for key, val in data.items():
        # support-style: top-level key is an event
        if isinstance(val, dict) and "choices" in val and "stats" in val:
            char_name = None
            events = {key: val}
        else:
            # character-style: top-level key is a character
            char_name = key
            events = val if isinstance(val, dict) else {}
            if trainee and char_name.strip().casefold() != trainee:
                continue  # skip non-trainee characters

        for raw_name, payload in (events or {}).items():
            ev_key = clean_event_name(raw_name)

            # indexes
            CHARACTER_BY_EVENT[ev_key] = char_name  # None for supports
            EVENT_TOTALS[ev_key] = len((payload or {}).get("choices", {}))

            hints = {}
            for k, s in ((payload or {}).get("stats") or {}).items():
                try:
                    idx = int(k)
                except Exception:
                    continue
                hint = (s or {}).get("Skill Hint", "")
                if hint:
                    hints[idx] = hint
            if hints:
                SKILL_HINT_BY_EVENT[ev_key] = hints

            result[ev_key] = payload

    return result

def dump_event(event_name: str):
    """Print choices + stats for a single event name."""
    k = clean_event_name(event_name)
    payload = CHARACTERS_EVENT_DATABASE.get(k) or SUPPORT_EVENT_DATABASE.get(k)
    if not payload:
        warning(f"Event not found: {event_name}")
        return
    info(f"Event: {event_name}  | key='{k}'")
    info(f"Choices: {payload.get('choices', {})}")
    for idx, row in (payload.get('stats') or {}).items():
        info(f"  choice {idx}: {row}")

def find_closest_event(event_name, max_distance=8):
  if not event_name:
    return None
  best_match = None
  best_distance = 99

  all_event_names = (
        list(CUSTOM_EVENT_DATABASE.keys()) +
        list(CHARACTERS_EVENT_DATABASE.keys()) +
        list(SUPPORT_EVENT_DATABASE.keys())
    )

  for db_event_name in all_event_names:
    distance = Levenshtein.distance(
      s1=event_name.lower(),
      s2=db_event_name.lower(),
      weights=(1, 1, 1)  # insertion, deletion, substitution
    )
    if distance < best_distance:
      best_distance = distance
      best_match = db_event_name
  
  if best_distance <= max_distance:
    return best_match  
  else: 
    None

# Fail safe
# "event_name": (total_choices, selected_choice)
CUSTOM_EVENT_DATABASE = {

  # [Common Events]
  "Extra Training": (2, 1),
  "At Summer (Year 2) Camp": (2, 1),
  "Dance Lesson": (2, 1),
  "New Year's Resolutions": (3, 2),
  "New Year's Shrine Visit": (3, 1),
  "Just an Acupuncturist, No Worries!": (5, 3),
  "Get Well Soon!": (2, 1),
  "Don't Overdo It!": (2, 1),

  #######################################################################################

  # [SCENARIOS]
  # URA Finals
  "Exhilarating! What a Scoop!": (2, 1),
  "A Trainer's Knowledge": (2, 1),
  "Best Foot Forward!": (2, 2),

  #######################################################################################

  # [RACE RESULTS]
  "Victory!": (2, 1),       # -15 Energy guaranteed
  "Solid Showing": (2, 1),  # -20 Energy guaranteed
  "Defeat": (2, 1),         # -25 Energy guaranteed
  "Etsuko's Exhaustive Coverage": (2, 2),
}