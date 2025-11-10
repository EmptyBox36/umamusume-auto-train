from utils.tools import get_secs, click
from utils.log import info, warning, error, debug
from utils.strings import clean_event_name

import utils.constants as constants
import core.state as state

_SPECIAL = {}
def _register(key):
    def deco(fn):
        _SPECIAL[key] = fn
        return fn
    return deco

def run_special_event(ev_key: str) -> bool:
    fn = _SPECIAL.get(ev_key)
    if not fn:
        return False
    try:
        return bool(fn())
    except Exception as e:
        warning(f"[SPECIAL] Handler for {ev_key} failed: {e}")
        return False

# ---- Unity “A Team at Last” ----

def _pref() -> str:
    # read config; normalize to key in IMG_MAP
    raw = state.UNITY_PREFERENCE or {}
    s = str(raw).strip().lower()
    if "sunny" in s:
        return "sunny"
    if "carrots" in s:
        return "carrots"
    return ""

@_register("a team at last")   # cleaned event key
def handle_unity_team_name() -> bool:
    """
    Variable-choice event. Use configured team if given.
    Default to Carrot when unset. If preferred not found, fall back to Carrot.
    """

    pref = _pref()
    if pref == "sunny":
        if click(img="assets/unity_cup/team_sunny.png", confidence=0.80, minSearch=get_secs(1.0), text=f"[UNITY] Select Team Sunny Day Runners", region=constants.GAME_SCREEN):
            return True
    if pref == "carrots":
        if click(img="assets/unity_cup/team_carrot.png", confidence=0.80, minSearch=get_secs(1.0), text=f"[UNITY] Select Team Carrots", region=constants.GAME_SCREEN):
            return True

    if click(img="assets/unity_cup/team_carrot.png", confidence=0.80, minSearch=get_secs(1.0), text=f"[UNITY] Select Team Carrots", region=constants.GAME_SCREEN):
        return True
    return False