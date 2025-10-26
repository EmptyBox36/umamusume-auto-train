import core.state as state
import re

from utils.log import info, warning, error, debug
from utils.strings import clean_event_name 
from core.EventsDatabase import COMMON_EVENT_DATABASE, CHARACTERS_EVENT_DATABASE, SUPPORT_EVENT_DATABASE, SCENARIOS_EVENT_DATABASE, EVENT_TOTALS, SKILL_HINT_BY_EVENT
from core.EventsDatabase import find_closest_event
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
        result_hint = pick_choice_by_skill_hint(key, desired_skills)
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

def _norm_hint(s: str) -> str:
    # strip common decorations like "○" and normalize case/space
    s = re.sub(r"[^\w\s'!-]", " ", s)   # drop symbols e.g. ○ ☆
    return " ".join(s.split()).casefold()

def pick_choice_by_skill_hint(key: str, desired_skills: set[str]):
    hints = SKILL_HINT_BY_EVENT.get(key, {})
    if not hints or not desired_skills:
        return None
    desired_norm = {_norm_hint(x) for x in desired_skills}
    for idx, hint in hints.items():
        if _norm_hint(str(hint)) in desired_norm:
            total = EVENT_TOTALS.get(key, len(hints))
            info(f"Event skill hint match → {key}: choice {idx} ({hint})")
            return (total, idx)
    return None

def score_choice(ev_key, choice_row):
    # Score from Stat
    current_stats = state.CURRENT_STATS
    choice_weight = state.CHOICE_WEIGHT
    caps = state.STAT_CAPS

    choice_score = 0.0
    for k_map, key in [("spd","Speed"),("sta","Stamina"),("pwr","Power"),
                       ("guts","Guts"),("wit","Wit")]:
        gain = float(choice_row.get(key, 0) or 0)
        cap  = float(caps[k_map])
        current = float(current_stats[k_map])

        norm = gain * (max(0.0, cap - current) / cap)

        if state.USE_PRIORITY_ON_CHOICE:
            multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(k_map)]
        else:
            multiplier = 1

        choice_score += choice_weight[k_map] * norm * multiplier

    # Score from Energy
    max_energy = state.MAX_ENERGY
    energy_level = state.CURRENT_ENERGY_LEVEL
    energy_gain = float(choice_row.get("HP", 0) or 0)
    if energy_gain < 0:
        energy_penalty = 0 # if choice give negative energy not have effect on score
    elif (max_energy - energy_level) >= energy_gain:
        energy_penalty = 1 # 1 = No Penalty
    else:
        energy_penalty = 0.1

    choice_score += choice_weight["hp"] * energy_gain * energy_penalty

    # Score from Mood
    mood_index = state.CURRENT_MOOD_INDEX
    mood_gain = float(choice_row.get("Mood", 0) or 0)
    minimum_mood = constants.MOOD_LIST.index(state.MINIMUM_MOOD)
    minimum_mood_junior_year = constants.MOOD_LIST.index(state.MINIMUM_MOOD_JUNIOR_YEAR)
    year = state.CURRENT_YEAR
    year_parts = year.split(" ")

    if year_parts[0] == "Junior":
      mood_check = minimum_mood_junior_year
    else:
      mood_check = minimum_mood

    if mood_gain < 0:
        mood_penalty = 0 # if choice give negative mood not have effect on score
    elif mood_index < mood_check:
        mood_penalty = 1 # 1 = No Penalty
    else:
        mood_penalty = 0.05

    choice_score += choice_weight["mood"] * mood_gain * mood_penalty

    # Score from Other factors
    choice_score += choice_weight["max_energy"] * float(choice_row.get("Max Energy", 0) or 0)
    choice_score += choice_weight["skillpts"] * float(choice_row.get("Skill Pts", 0) or 0)
    choice_score += choice_weight["bond"] * float(choice_row.get("Friendship", 0) or 0)

    return choice_score

def pick_choice_by_score(key: str, db: dict):
    payload = db.get(key) or {}
    stats = payload.get("stats") or {}

    total = EVENT_TOTALS.get(key, len(payload.get("choices", {})) or len(stats))

    best_idx, best_score = 1, float("-inf")
    best_stat_priority = float("-inf")
    for idx, row in stats.items():
        try:
            i = int(idx)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        score = score_choice(key, row)
        debug(f"[Score] {key} -> choice {i}: {score:.3f}")
        stat_priority = get_stat_priority(key)

        # if this choice has higher score, or equal score but higher stat priority
        if (score > best_score) or (abs(score - best_score) < 1e-6 and stat_priority > best_stat_priority):
            best_score = score
            best_stat_priority = stat_priority
            best_idx = i

    return (total, best_idx)

