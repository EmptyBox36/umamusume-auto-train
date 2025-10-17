import core.state as state
import re

from utils.log import info, warning, error, debug
from utils.strings import clean_event_name 
from core.EventsDatabase import COMMON_EVENT_DATABASE, CHARACTERS_EVENT_DATABASE, SUPPORT_EVENT_DATABASE, SCENARIOS_EVENT_DATABASE, EVENT_TOTALS, SKILL_HINT_BY_EVENT, find_closest_event
from core.state import STAT_CAPS, check_energy_level, stat_state, check_mood, check_current_year
from core.logic import get_stat_priority
import utils.constants as constants

def get_optimal_choice(event_name):
    if not event_name:
        return (False, 1)

    key = clean_event_name(event_name)
    desired_skills = {s.casefold() for s in state.SKILL_LIST}

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
    """
    Returns (total_choices, choice_idx) or None.
    Normalizes event key, fuzzy-matches keys, and tolerates hint key variants.
    """
    if not desired_skills:
        return None

    k = _norm_seen_event(key)
    hints = hint_map.get(k)

    if not hints:
        # fuzzy to handle punctuation/case differences
        best = _closest_key(k, hint_map.keys())
        if best:
            k = best
            hints = hint_map[best]

    if not hints:
        return None

    for idx, raw in hints.items():
        hint_name = _extract_hint_name(raw)
        # debug(f"[HINT DEBUG] {key} → map:{k} choice {idx} hint='{hint_name}'")
        if hint_name and hint_name.casefold() in desired_skills:
            total = EVENT_TOTALS.get(k, len(hints))
            info(f"[HINT] {key} → choose {idx} ({hint_name}) [mapped:{k}]")
            return (total, int(idx))

    return None

def score_choice(ev_key, choice_row):
    from core.execute import current_stats
    global caps
    energy_level, max_energy = check_energy_level()

    choice_weight = state.CHOICE_WEIGHT
    caps = STAT_CAPS

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

def _extract_hint_name(hint) -> str:
    if isinstance(hint, dict):
        m = {k.lower().replace(" ", ""): v for k, v in hint.items()}
        val = m.get("skillhint", "")
    else:
        val = str(hint or "")
    val = val.strip()
    return "" if not val or val.lower() == "(random)" else val

def _lev(a: str, b: str) -> int:
    n, m = len(a), len(b)
    if n > m: a, b, n, m = b, a, m, n
    prev = list(range(m + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[m]

def _closest_key(key: str, keys, max_d: int = 3):
    best, best_d = None, max_d + 1
    for k in keys:
        d = _lev(key, k)
        if d < best_d:
            best, best_d = k, d
    return best if best_d <= max_d else None

def _norm_seen_event(name: str) -> str:
    k = clean_event_name(name)
    # strip UI junk like "... choice", "... event"
    return re.sub(r"\b(choice|event)\b", "", k).strip()