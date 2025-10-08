import core.state as state

from utils.log import info, warning, error, debug
from utils.strings import clean_event_name 
from core.EventsDatabase import COMMON_EVENT_DATABASE, CHARACTERS_EVENT_DATABASE, SUPPORT_EVENT_DATABASE, SCENARIOS_EVENT_DATABASE, EVENT_TOTALS, find_closest_event
from core.state import STAT_CAPS, check_energy_level, stat_state, check_mood, check_current_year
from core.logic import get_stat_priority
import utils.constants as constants

def get_optimal_choice(event_name):
    if not event_name:
        return (False, 1)

    key = clean_event_name(event_name)
    desired_skills = {s.casefold() for s in (state.SKILL_LIST or [])}

    # Optional fuzzy correction
    if key not in COMMON_EVENT_DATABASE.keys() \
        and key not in CHARACTERS_EVENT_DATABASE.keys() \
        and key not in SUPPORT_EVENT_DATABASE.keys() \
        and key not in SCENARIOS_EVENT_DATABASE.keys():
        best_match = find_closest_event(key)
        if best_match:
            key = best_match
            info(f"[Fuzzy] Using closest match: {best_match}")

    # 1. Select choice in JSON database
    db = CHARACTERS_EVENT_DATABASE if key in CHARACTERS_EVENT_DATABASE else \
         SUPPORT_EVENT_DATABASE if key in SUPPORT_EVENT_DATABASE else \
         SCENARIOS_EVENT_DATABASE if key in SCENARIOS_EVENT_DATABASE else None
    if db:
        # Select choice by skill hint
        result_hint = pick_choice_by_skill_hint(key, desired_skills, db)
        if result_hint is not None:
            return result_hint

        # Select choice by score
        return pick_choice_by_score(key, db)

    # 2. Hardcoded fallback
    if key in COMMON_EVENT_DATABASE:
        info(f"[Custom DB] Exact match found: {key}")
        return COMMON_EVENT_DATABASE[key]

    # 3. Default choice
    warning(f"No match found for {key}. Defaulting to top choice.")
    return (False, 1)


def pick_choice_by_skill_hint(key: str, desired_skills: set[str], hint_map: dict):
    hints = hint_map.get(key, {})
    if hints and desired_skills:
        for idx, hint in hints.items():
            if isinstance(hint, dict):
                hint_name = hint.get("Skill Hint", "").strip()
            else:
                hint_name = str(hint).strip()

            if hint_name in desired_skills:
                total = EVENT_TOTALS.get(key, len(hints))
                info(f"Event skill hint match → {key}: choice {idx} ({hint_name})")
                return (total, idx)
    return None

caps = STAT_CAPS
USE_PRIORITY_ON_CHOICE = False
def score_choice(ev_key, choice_row):
    global caps
    energy_level, max_energy = check_energy_level()

    current_stats = stat_state()  # dict: spd, sta, pwr, guts, wit
    choice_weight = state.CHOICE_WEIGHT

    # normalized stats
    choice_score = 0.0
    for k_map, key in [("spd","Speed"),("sta","Stamina"),("pwr","Power"),
                       ("guts","Guts"),("wit","Wit")]:
        gain = float(choice_row.get(key, 0) or 0)
        cap  = float(caps[k_map])
        current = float(current_stats[k_map])

        norm = gain * max(0.0, cap - current) / cap

        if USE_PRIORITY_ON_CHOICE:
            multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(k_map)]
        else:
            multiplier = 1

        choice_score += choice_weight[k_map] * norm * multiplier

    energy_gain = float(choice_row.get("HP", 0) or 0)

    if (max_energy - energy_level) >= energy_gain or energy_gain < 0:
        choice_score += choice_weight["hp"] * energy_gain * 1
    else:
        choice_score += choice_weight["hp"] * energy_gain * 0.1

    choice_score += choice_weight["max_energy"] * float(choice_row.get("Max Energy", 0) or 0)
    choice_score += choice_weight["skillpts"] * float(choice_row.get("Skill Pts", 0) or 0)
    choice_score += choice_weight["bond"] * float(choice_row.get("Friendship", 0) or 0)

    mood = check_mood()
    mood_index = constants.MOOD_LIST.index(mood)
    mood_gain = float(choice_row.get("Mood", 0) or 0)
    minimum_mood = constants.MOOD_LIST.index(state.MINIMUM_MOOD)
    minimum_mood_junior_year = constants.MOOD_LIST.index(state.MINIMUM_MOOD_JUNIOR_YEAR)
    year = check_current_year()
    year_parts = year.split(" ")

    if year_parts[0] == "Junior":
      mood_check = minimum_mood_junior_year
    else:
      mood_check = minimum_mood

    if mood_index < mood_check or mood_gain < 0:
        choice_score += choice_weight["mood"] * mood_gain
    else:
        choice_score += choice_weight["mood"] * mood_gain * 0.05

    return choice_score

def pick_choice_by_score(key: str, db: dict):
    payload = db.get(key) or {}
    stats = payload.get("stats") or {}

    total = EVENT_TOTALS.get(key, len(payload.get("choices", {})) or len(stats))

    best_idx, best_score = 1, float("-inf")
    for idx, row in stats.items():
        try:
            i = int(idx)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        score = score_choice(key, row)
        debug(f"[Score] {key} -> choice {i}: {score:.3f}")
        if score > best_score:
            best_score, best_idx = score, i

    return (total, best_idx)

