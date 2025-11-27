import core.state as state
import utils.constants as constants
import re

from utils.log import info, warning, error, debug
from utils.strings import clean_event_name 
from core.EventsDatabase import CHARACTERS_EVENT_DATABASE, SUPPORT_EVENT_DATABASE, SCENARIOS_EVENT_DATABASE, EVENT_TOTALS, SKILL_HINT_BY_EVENT, EVENT_CHOICES_MAP, ALL_EVENT_KEYS
from core.EventsDatabase import find_closest_event
from core.logic import get_stat_priority
from core.special_events import run_special_event
from core.state import check_energy_level, stop_bot

def get_optimal_choice(event_name: str):
    choice = 0
    key = clean_event_name(event_name)
    
    # # For Debug
    # if key == "a team at last":
    #     stop_bot()

    if run_special_event(key):
        info(f"[Special] handled: {key}")
        return None

    # 1) exact override
    r = _apply_override_if_valid(key)
    if r is not None:
        return r

    # 2) fuzzy key
    if key not in ALL_EVENT_KEYS:
        best = find_closest_event(key, ALL_EVENT_KEYS)
        if best:
            info(f"[Fuzzy] Using closest match: {best}")
            if run_special_event(best):
                info(f"[Special] handled: {key}")
                return None
            r = _apply_override_if_valid(best)
            if r is not None:
                return r
            key = best

    # 2) Try override again in case fuzzy changed the key into your map
    chosen = EVENT_CHOICES_MAP.get(key)
    if chosen is not None:
        info(f"[Custom] Using config choice for {event_name} -> {chosen}")
        return int(chosen)

    # 3) Fall back to hint / score like you already do
    db = (CHARACTERS_EVENT_DATABASE if key in CHARACTERS_EVENT_DATABASE else
          SUPPORT_EVENT_DATABASE    if key in SUPPORT_EVENT_DATABASE    else
          SCENARIOS_EVENT_DATABASE  if key in SCENARIOS_EVENT_DATABASE  else None)
    if db:
        result_hint = pick_choice_by_skill_hint(key, {s.casefold() for s in (state.DESIRE_SKILL or [])})
        if result_hint is not None:
            return result_hint
        return pick_choice_by_score(key, db)

    warning(f"No match found for {event_name}. Defaulting to top choice.")
    return choice

def _norm_hint(s: str) -> str:
    # strip common decorations like "○" and normalize case/space
    s = re.sub(r"[^\w\s'!-]", " ", s)   # drop symbols e.g. ○ ☆
    return " ".join(s.split()).casefold()

def pick_choice_by_skill_hint(event_name: str, desired_skills: set[str]):
    hints = SKILL_HINT_BY_EVENT.get(event_name, {})
    if not hints or not desired_skills:
        return None

    desired_norm = {_norm_hint(x) for x in desired_skills}

    for choice, hint in hints.items():
        if isinstance(hint, list):
            for h in hint:
                if _norm_hint(h) in desired_norm:
                    info(f"[Hint] {event_name}: choice {choice} ({h})")
                    return choice
        else:
            if _norm_hint(hint) in desired_norm:
                info(f"[Hint] {event_name}: choice {choice} ({hint})")
                return choice

    return None

def _f(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

def score_choice(choice_row):
    # Score from Stat
    current_stats = state.CURRENT_STATS or {}
    choice_weight = state.CHOICE_WEIGHT
    caps = state.STAT_CAPS

    choice_score = 0.0
    for k_map, key in [("spd","Speed"),("sta","Stamina"),("pwr","Power"),("guts","Guts"),("wit","Wit")]:
        gain = _f(choice_row.get(key, 0), 0)
        cap  = _f(caps[k_map], 1)
        current = _f(current_stats.get(k_map, 0.0), 0.0) 

        # norm = gain * (max(0.0, cap - current) / cap)
        if cap > current:
            norm = (cap - current) / cap
        else: # over-capped
            norm = 0

        if state.USE_PRIORITY_ON_CHOICE:
            multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(k_map)]
        else:
            multiplier = 1

        choice_score += choice_weight[k_map] * multiplier * norm * gain

    # Score from Energy
    energy_level, max_energy = check_energy_level()
    missing_energy = max_energy - energy_level

    energy_gain = float(choice_row.get("HP", 0) or 0)
    if energy_gain < 0:
        energy_penalty = 0.1 # if choice give negative energy have less effect on score
    elif missing_energy >= energy_gain or (energy_gain >= 50 and missing_energy >= 50):
        energy_penalty = 1 # 1 = No Penalty
    else:
        energy_penalty = 0

    choice_score += choice_weight["hp"] * energy_gain * energy_penalty

    # Score from Mood
    mood_index = (state.CURRENT_MOOD_INDEX or 2)
    mood_gain = float(choice_row.get("Mood", 0) or 0)

    if mood_gain < 0:
        mood_penalty = 0 # if choice give negative mood not have effect on score
    elif mood_index < 4: # GREAT
        mood_penalty = 1 # 1 = No Penalty
    else:
        mood_penalty = 0

    choice_score += choice_weight["mood"] * mood_gain * mood_penalty

    # Score from Other factors
    choice_score += choice_weight["max_energy"] * float(choice_row.get("Max Energy", 0) or 0)
    choice_score += choice_weight["skillpts"] * float(choice_row.get("Skill Pts", 0) or 0)
    choice_score += choice_weight["bond"] * float(choice_row.get("Friendship", 0) or 0)

    return choice_score

def pick_choice_by_score(key: str, db: dict):
    payload = db.get(key) or {}
    stats = payload.get("stats") or {}

    # total = EVENT_TOTALS.get(key, len(payload.get("choices", {})) or len(stats))

    best_idx, best_score = 1, float("-inf")
    best_stat_priority = float("-inf")
    for idx, row in stats.items():
        try:
            i = int(idx)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        score = score_choice(row)
        debug(f"[Score] {key} -> choice {i}: {score:.3f}")

        # if this choice has higher score, or equal score but higher stat priority
        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx

def _apply_override_if_valid(key: str):
    chosen = EVENT_CHOICES_MAP.get(key)
    if not chosen:
        return None
    # derive total robustly
    total = EVENT_TOTALS.get(key)
    if total is None:
        # try to read from any loaded DB
        payload = (CHARACTERS_EVENT_DATABASE.get(key)
                   or SUPPORT_EVENT_DATABASE.get(key)
                   or SCENARIOS_EVENT_DATABASE.get(key) or {})
        total = len((payload.get("choices") or {})) or len((payload.get("stats") or {})) or 0
    if 1 <= chosen <= total:
        info(f"[Custom DB] Exact match: {key} → choice {chosen}")
        return chosen
    warning(f"[Custom DB] Override out of range: {key} → {chosen}. Ignoring.")
    return None