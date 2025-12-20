import re

import core.state as state
import utils.constants as constants
from core.EventsDatabase import (
    ALL_EVENT_KEYS,
    CHARACTERS_EVENT_DATABASE,
    EVENT_CHOICES_MAP,
    EVENT_TOTALS,
    SCENARIOS_EVENT_DATABASE,
    SKILL_HINT_BY_EVENT,
    SUPPORT_EVENT_DATABASE,
    find_closest_event,
)
from core.logic import get_stat_priority
from core.special_events import run_special_event
from core.state import check_energy_level, check_mood
from utils.log import debug, info, warning
from utils.strings import clean_event_name


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
    db = (
        CHARACTERS_EVENT_DATABASE
        if key in CHARACTERS_EVENT_DATABASE
        else (
            SUPPORT_EVENT_DATABASE
            if key in SUPPORT_EVENT_DATABASE
            else SCENARIOS_EVENT_DATABASE if key in SCENARIOS_EVENT_DATABASE else None
        )
    )
    if db:
        result_hint = pick_choice_by_skill_hint(
            key, {s.casefold() for s in (state.DESIRE_SKILL or [])}
        )
        if result_hint is not None:
            return result_hint
        return pick_choice_by_score(key, db)

    warning(f"No match found for {event_name}. Defaulting to top choice.")
    return choice


def _norm_hint(s: str) -> str:
    # strip common decorations like "○" and normalize case/space
    s = re.sub(r"[^\w\s'!-]", " ", s)  # drop symbols e.g. ○ ☆
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
    current_stats = state.CURRENT_STATS or {}
    choice_weight = state.CHOICE_WEIGHT
    caps = state.STAT_CAPS

    score = 0.0

    # 1) Stats: Speed, Stamina, Power, Guts, Wit
    for k_map, key in [
        ("spd", "Speed"),
        ("sta", "Stamina"),
        ("pwr", "Power"),
        ("guts", "Guts"),
        ("wit", "Wit"),
    ]:
        gain = _f(choice_row.get(key, 0), 0.0)
        if gain == 0:
            continue

        cap = _f(caps.get(k_map, 0), 0.0)
        current = _f(current_stats.get(k_map, 0.0), 0.0)

        if gain > 0:
            if cap > 0:
                if current >= cap:
                    norm = 0.0
                else:
                    norm = max(0.0, min(1.0, (cap - current) / cap))
            else:
                norm = 1.0
        else:
            norm = 0.5

        if state.USE_PRIORITY_ON_CHOICE:
            priority_bonus = state.PRIORITY_EFFECTS_LIST[get_stat_priority(k_map)]
            multiplier = 1.0 + priority_bonus
        else:
            multiplier = 1.0

        score += choice_weight[k_map] * multiplier * norm * gain

    # 2) HP (Energy)
    energy_level, max_energy = check_energy_level()
    energy_gain = _f(choice_row.get("HP", 0), 0.0)

    if max_energy > 0 and energy_gain != 0:
        missing_energy = max_energy - energy_level

        if energy_gain > 0:
            overflow = max(0.0, energy_gain - missing_energy)

            if energy_gain > 0:
                overflow_ratio = overflow / energy_gain
            else:
                overflow_ratio = 0.0

            overflow_penalty_weight = 2.0

            if energy_gain > 100:
                overflow_penalty_weight = 0.4

            overflow_mult = 1.0 - (overflow_ratio * overflow_penalty_weight)

            score += choice_weight["hp"] * energy_gain * max(0.0, overflow_mult)
        else:
            hp_penalty_mult = 0.0
            score += choice_weight["hp"] * energy_gain * hp_penalty_mult

    # 3) Mood
    mood = check_mood()
    mood_index = constants.MOOD_LIST.index(mood)
    mood_gain = _f(choice_row.get("Mood", 0), 0.0)
    if mood_gain != 0:
        if mood_gain > 0:
            if mood_index < 4:
                mood_mult = 1.0
            else:
                mood_mult = 0.0
        else:
            mood_mult = 0.0
        score += choice_weight["mood"] * mood_gain * mood_mult

    # 4) Other factors (Max Energy, Skill Pts, Friendship/Bond)
    score += choice_weight["max_energy"] * _f(choice_row.get("Max Energy", 0), 0.0)
    score += choice_weight["skillpts"] * _f(choice_row.get("Skill Pts", 0), 0.0)
    score += choice_weight["bond"] * _f(choice_row.get("Friendship", 0), 0.0)

    # 5) Randomness penalty: prefer stable outcomes when all else equal.
    if choice_row.get("random"):
        score *= 1.3

    return score


def pick_choice_by_score(key: str, db: dict):
    payload = db.get(key) or {}
    stats = payload.get("stats") or {}

    best_idx, best_score = 1, float("-inf")
    for idx, row in stats.items():
        try:
            i = int(idx)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue

        score = score_choice(row)
        debug(f"[Score] {key} -> choice {i}: {score:.3f}")

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
        payload = (
            CHARACTERS_EVENT_DATABASE.get(key)
            or SUPPORT_EVENT_DATABASE.get(key)
            or SCENARIOS_EVENT_DATABASE.get(key)
            or {}
        )
        total = (
            len((payload.get("choices") or {}))
            or len((payload.get("stats") or {}))
            or 0
        )
    if 1 <= chosen <= total:
        info(f"[Custom DB] Exact match: {key} → choice {chosen}")
        return chosen
    warning(f"[Custom DB] Override out of range: {key} → {chosen}. Ignoring.")
    return None
