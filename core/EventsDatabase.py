import json
from pathlib import Path
from rapidfuzz import fuzz

from utils.log import info, warning, error, debug
from utils.strings import clean_event_name 
import core.state as state

EVENT_TOTALS = {}
SKILL_HINT_BY_EVENT = {}
CHARACTER_BY_EVENT = {}
CHARACTERS_EVENT_DATABASE = {}
SUPPORT_EVENT_DATABASE = {}
SCENARIOS_EVENT_DATABASE = {}
EVENT_CHOICES_MAP = {}

def load_event_databases():
    global EVENT_CHOICES_MAP
    # hard reset all indices and views
    EVENT_TOTALS.clear()
    SKILL_HINT_BY_EVENT.clear()
    CHARACTER_BY_EVENT.clear()

    # keep object identity for modules holding references
    CHARACTERS_EVENT_DATABASE.clear()
    SUPPORT_EVENT_DATABASE.clear()

    """Load event data for trainee and support cards."""
    info("Loading event databases...")

    try:
        EVENT_CHOICES_MAP = {
            clean_event_name(e.get("event_name", "")): int(e.get("chosen", 1))
            for e in (state.EVENT_CHOICES or [])
            if e.get("event_name")
        }
    except Exception:
        EVENT_CHOICES_MAP = {}

    trainee = (state.TRAINEE_NAME or "").strip()
    scenario = (state.SCENARIO_NAME or "").strip()

    CHARACTERS_EVENT_DATABASE.clear()
    CHARACTERS_EVENT_DATABASE.update(index_json("./scraper/data/characters.json", trainee))

    SUPPORT_EVENT_DATABASE.clear()
    SUPPORT_EVENT_DATABASE.update(index_json("./scraper/data/supports.json", scenario))

    SCENARIOS_EVENT_DATABASE.clear()
    SCENARIOS_EVENT_DATABASE.update(index_json("./data/scenarios.json"))

    chars = sorted({c for c in CHARACTER_BY_EVENT.values() if c})
    info(f"characters indexed: {len(chars)} -> {chars[:5]}{'...' if len(chars)>5 else ''}")
    info(f"character-event entries: {sum(1 for c in CHARACTER_BY_EVENT.values() if c)}")

def index_json(path: str, group_filter: str | None = None) -> dict:
    p = Path(path)
    if not p.exists():
        return {}

    gfilter = (group_filter or "").strip().casefold()
    data = json.loads(p.read_text(encoding="utf-8"))
    result = {}

    for key, val in data.items():
        # support-style: top-level key is an event
        if isinstance(val, dict) and "choices" in val and "stats" in val:
            group_name = None
            events = {key: val}
        else:
            # character-style: top-level key is a character
            group_name = key
            events = val if isinstance(val, dict) else {}
            if gfilter and group_name.strip().casefold() != gfilter:
                continue  # skip not trainee and scenario

        for raw_name, payload in (events or {}).items():
            ev_key = clean_event_name(raw_name)

            # indexes
            CHARACTER_BY_EVENT[ev_key] = group_name  # None for supports
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
    payload = (CHARACTERS_EVENT_DATABASE.get(k) or SUPPORT_EVENT_DATABASE.get(k) or SCENARIOS_EVENT_DATABASE.get(k))
    if not payload:
        warning(f"Event not found: {event_name}")
        return
    info(f"Event: {event_name}  | key='{k}'")
    info(f"Choices: {payload.get('choices', {})}")
    for idx, row in (payload.get('stats') or {}).items():
        info(f"choice {idx}: {row}")

def find_closest_event(event_name, event_list, threshold=0.8):
    if not event_name:
        return None

    best_match, best_score = None, 0
    for db_event in event_list:
        score = fuzz.token_sort_ratio(event_name.lower(), db_event.lower()) / 100
        if score > best_score:
            best_score = score
            best_match = db_event
    return best_match if best_score >= threshold else None