import core.state as state
import utils.constants as constants
from utils.log import debug, info
from utils.tools import click, get_secs, sleep


# Get priority stat from config
def get_stat_priority(stat_key: str) -> int:
    return (
        state.PRIORITY_STAT.index(stat_key) if stat_key in state.PRIORITY_STAT else 999
    )


def check_all_elements_are_same(d):
    sections = list(d.values())
    return all(section == sections[0] for section in sections[1:])


# Will do train with the most support card
# Used in the first year (aim for rainbow)
def most_support_card(results):
    year = state.CURRENT_YEAR
    year_parts = year.split(" ")

    # Seperate wit
    wit_data = results.get("wit")

    # Get all training but wit
    non_wit_results = {
        k: v
        for k, v in results.items()
        if k != "wit" and int(v["failure"]) <= state.MAX_FAILURE
    }

    # Check if train is bad
    all_others_bad = len(non_wit_results) == 0
    energy_level = state.CURRENT_ENERGY_LEVEL

    if energy_level < state.SKIP_TRAINING_ENERGY:
        info(
            "All trainings are unsafe and WIT training won't help go back up to safe levels, resting instead."
        )
        return None

    if (
        all_others_bad
        and wit_data
        and int(wit_data["failure"]) <= state.MAX_FAILURE
        and wit_data["total_supports"] >= 2
    ):
        info("All trainings are unsafe, but WIT is safe and has enough support cards.")
        return "wit"

    filtered_results = {
        k: v for k, v in results.items() if int(v["failure"]) <= state.MAX_FAILURE
    }

    if not filtered_results:
        info("No safe training found. All failure chances are too high.")
        return None

    # this is the weight adder used for skewing results of training decisions PRIORITY_EFFECTS_LIST[get_stat_priority(x[0])] * PRIORITY_WEIGHTS_LIST[priority_weight]
    # Best training
    best_training = max(filtered_results.items(), key=training_score)

    best_key, best_data = best_training

    RACE_IF_LOW = True
    FRIEND_IF_LOW = True

    if best_data["total_supports"] <= 1:
        if int(best_data["failure"]) == 0:
            # WIT must be at least 2 support cards
            if best_key == "wit":
                if best_data["total_supports"] == 0:
                    info(f"Not have any good training.")
                elif energy_level > state.NEVER_REST_ENERGY:
                    info(
                        f"Only 1 support and it's WIT but energy is too high for resting to be worth it. Still training."
                    )
                    state.FORCE_REST = True
                    return "wit"
                else:
                    info(f"Only 1 support and it's WIT. Skipping.")
                    state.FORCE_REST = True
                    return None

        if RACE_IF_LOW:
            if energy_level > state.NEVER_REST_ENERGY:
                if year_parts[0] not in ["Junior", "Finale"] and year_parts[3] not in [
                    "Jul",
                    "Aug",
                ]:
                    from utils.process import do_race

                    fake_criteria = "fan"
                    keywords = ("fan", "Maiden", "Progress")
                    fake_turn = 5

                    info(
                        "Training point is too low and energy is high, try to do graded race."
                    )
                    race_found, race_name = decide_race_for_goal(
                        year, fake_turn, fake_criteria, keywords
                    )
                    info(
                        f"[RACE_IF_LOW] race_found={race_found}, race_name={race_name}"
                    )

                    if race_name:
                        race = do_race(race_found, img=race_name)
                    else:
                        race = False

                    if race is True:
                        return
                    elif race is False:
                        return best_key
                    else:
                        click(
                            img="assets/buttons/back_btn.png",
                            minSearch=get_secs(1),
                            text="No suitable race found.",
                        )
                        sleep(0.5)
                        return best_key

        if energy_level > state.NEVER_REST_ENERGY:
            if best_key == "wit" and best_data["total_supports"] == 0:
                info("Only WIT without support left, Force Rest.")
                state.FORCE_REST = True
                return None
            elif best_data["total_supports"] == 0:
                info(f"Only {best_key.upper()} without support left, Force Rest.")
                state.FORCE_REST = True
                return None
            else:
                info(f"Energy is over {state.NEVER_REST_ENERGY}, train anyway.")
                return best_key
        else:
            info("Low Energy. Choosing to rest.")
            return None

    info(
        f"Best training: {best_key.upper()} with {best_data['total_supports']} support cards, {best_data['total_non_maxed_support']} non-maxed support cards with {best_data['failure']}% fail chance and {best_data['total_hints']} total hint."
    )
    return best_key


PRIORITY_WEIGHTS_LIST = {"HEAVY": 0.75, "MEDIUM": 0.5, "LIGHT": 0.25, "NONE": 0}


def training_score(x):
    global PRIORITY_WEIGHTS_LIST
    priority_weight = PRIORITY_WEIGHTS_LIST[state.PRIORITY_WEIGHT]
    base = x[1]["total_supports"]
    non_max_friends = (
        x[1]["total_friendship_levels"]["gray"]
        + x[1]["total_friendship_levels"]["blue"]
        + x[1]["total_friendship_levels"]["green"]
    )
    base += non_max_friends * 1
    if x[1]["total_hints"] > 0:
        base += state.HINT_POINT
    multiplier = (
        1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(x[0])] * priority_weight
    )
    total = base * multiplier

    # Debug output
    debug(
        f"{x[0]} -> base={base}, multiplier={multiplier}, total={total}, priority={get_stat_priority(x[0])}"
    )

    return (total, -get_stat_priority(x[0]))


def filter_by_stat_caps(results, current_stats):
    return {
        stat: data
        for stat, data in results.items()
        if current_stats.get(stat, 0) < state.STAT_CAPS.get(stat, 1200)
    }


def all_values_equal(dictionary):
    values = list(dictionary.values())
    return all(value == values[0] for value in values[1:])


# helper functions
def decide_race_for_goal(year, turn, criteria, keywords):
    no_race = (False, None)
    turn_to_race = 10

    if not state.DONE_DEBUT:
        turn_to_race = 99  # If Fail the Debut race, try to do Maiden race immediately

    # Skip pre-debut
    if year == "Junior Year Pre-Debut":
        return no_race
    if turn >= turn_to_race:
        return no_race

    keywords = [k.casefold() for k in keywords]
    criteria_text = (criteria or "").casefold()

    if any(word.lower() in criteria_text for word in keywords):
        info("Criteria word found. Trying to find races.")

        if state.DONE_DEBUT:
            GRADED_TRIGGERS = ("progress", "fan")
            if any(w in criteria_text for w in GRADED_TRIGGERS):
                info(f'"progress" or "fan" is in criteria text.')

                if "G1" in criteria_text or "GI" in criteria_text:
                    info('Goal mentions "G1"; restricting to only G1 races.')
                    filtered = [r for r in filtered if r.get("grade") == "G1"]
                else:
                    # Get races for this year
                    race_list = constants.RACE_LOOKUP.get(year, [])
                    if not race_list:
                        return False, None

                    if turn <= 2:
                        ALLOWED_GRADES = {"G1", "G2", "G3", "OP"}
                    else:
                        ALLOWED_GRADES = {"G1"}

                filtered = [r for r in race_list if r.get("grade") in ALLOWED_GRADES]

                if not filtered:
                    info("No races available for this turn.")
                    return False, None

                current_fans = state.FAN_COUNT

                if current_fans != -1:
                    filtered = [
                        r
                        for r in filtered
                        if r.get("fans", {}).get("required", 0) <= current_fans
                    ]
                    if not filtered:
                        info(
                            f"No races meet fan requirement. Current fans = {current_fans}."
                        )
                        return False, None

                best_race = filter_races_by_aptitude(filtered, state.APTITUDES)
                if not best_race:
                    info("No matching race by aptitude.")
                    return False, None

                return True, best_race["name"]

        # If criteria keyword matches but no progress → fallback
        return False, "any"

    return no_race


def filter_races_by_aptitude(race_list, aptitudes):
    GRADE_SCORE = {"s": 2, "a": 2, "b": 1}

    results = []
    for race in race_list:
        surface_key = f"surface_{race['terrain'].lower()}"
        distance_key = f"distance_{race['distance']['type'].lower()}"

        s = GRADE_SCORE.get(aptitudes.get(surface_key, ""), 0)
        d = GRADE_SCORE.get(aptitudes.get(distance_key, ""), 0)

        if s and d:  # both nonzero (A or B)
            score = s + d
            results.append((score, race["fans"]["gained"], race))

    if not results:
        return None

    # sort best → worst by score, then fans
    results.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return results[0][2]


def _get_next_scheduled_race():
    """Return the next scheduled race (dict) based on state.VIRTUAL_TURN."""
    schedule = state.RACE_SCHEDULE or []
    virtual_turn = state.VIRTUAL_TURN or None

    if virtual_turn is None:
        return None

    candidates = []
    for r in schedule:
        if not isinstance(r, dict):
            continue
        tn = r.get("turnNumber")
        if isinstance(tn, int) and tn >= virtual_turn:
            candidates.append(r)

    if not candidates:
        return None

    # nearest future race by turnNumber
    return min(candidates, key=lambda x: x["turnNumber"])


def _get_required_fans_for_scheduled_race(race_entry: dict) -> int:
    """
    Look up the fan requirement of a scheduled race using constants.RACE_LOOKUP
    and races.json data.
    """
    name = race_entry.get("name")
    year = race_entry.get("year")
    date = race_entry.get("date")

    if not (name and year and date):
        return 0

    # RACE_LOOKUP is keyed by "Classic Year Early May", etc.
    lookup_key = f"{year} {date}"
    race_list = constants.RACE_LOOKUP.get(lookup_key, [])

    for r in race_list:
        if r.get("name") == name:
            return r.get("fans", {}).get("required", 0)

    return 0


def check_fans_for_upcoming_schedule() -> bool:
    next_race = _get_next_scheduled_race()
    if not next_race:
        return False

    virtual_turn = state.VIRTUAL_TURN
    if virtual_turn is None:
        return False

    next_turn = next_race.get("turnNumber")
    if not isinstance(next_turn, int):
        return False

    gap = next_turn - virtual_turn
    # ignore past/this-turn races and races that are still far away
    if gap <= 0:
        return False
    # Do objective race before do any optional race
    if gap >= state.CURRENT_TURN_LEFT:
        return False
    # "very low" gap → tweakable threshold
    MAX_GAP_TURNS = 5
    if gap > MAX_GAP_TURNS:
        return False

    required_fans = _get_required_fans_for_scheduled_race(next_race)
    current_fans = state.FAN_COUNT

    # if we can't read fans or already meet requirement, do nothing
    if required_fans <= 0 or current_fans == -1 or current_fans >= required_fans:
        return False

    debug(f"{next_race['name']} in {gap} turn(s) require {required_fans} fans, but currently have {state.FAN_COUNT} fans")

    from utils.process import check_fan, do_race
    debug("re-checking the fans count")
    check_fan()
    current_fans = state.FAN_COUNT
    debug(f"current fans counts is {state.FAN_COUNT}")

    if required_fans <= 0 or current_fans == -1 or current_fans >= required_fans:
        return False

    # Use the same graded-race finder, but with a fan/progress-style criteria.
    fake_criteria = "fan"
    keywords = ("fan", "Maiden", "Progress")

    # Use current year/turn-left like other logic
    year = state.CURRENT_YEAR

    race_found, race_name = decide_race_for_goal(year, gap, fake_criteria, keywords)
    info(f"[FAN_FARM] race_found={race_found}, race_name={race_name}")

    if not race_name:
        # no race candidate or filtered out by aptitude/requirements
        return False

    if race_name == "any":
        # let do_race pick any race
        race_result = do_race(race_found, img=None)
    else:
        race_result = do_race(race_found, img=race_name)

    if race_result is True:
        info("[FAN_FARM] Extra race done to farm fans before scheduled goal.")
        return True

    if race_result is False:
        # race screen opened but could not run anything (no eligible race)
        info("[FAN_FARM] No suitable race actually run, go back to training.")
        return False

    # race_result is None or unexpected → make sure we go back
    click(
        img="assets/buttons/back_btn.png",
        minSearch=get_secs(1),
        text="[FAN_FARM] Aborting extra race, back to training.",
    )
    sleep(0.5)
    return False
