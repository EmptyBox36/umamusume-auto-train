from pickle import TRUE
from statistics import StatisticsError

from cv2.gapi import mul
from utils.log import info, warning, error, debug
from utils.tools import sleep, get_secs, click

import core.state as state
import utils.constants as constants

# Get priority stat from config
def get_stat_priority(stat_key: str) -> int:
  return state.PRIORITY_STAT.index(stat_key) if stat_key in state.PRIORITY_STAT else 999

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
    k: v for k, v in results.items()
    if k != "wit" and int(v["failure"]) <= state.MAX_FAILURE
  }

  # Check if train is bad
  all_others_bad = len(non_wit_results) == 0
  energy_level = state.CURRENT_ENERGY_LEVEL

  if energy_level < state.SKIP_TRAINING_ENERGY:
    info("All trainings are unsafe and WIT training won't help go back up to safe levels, resting instead.")
    return None

  if all_others_bad and wit_data and int(wit_data["failure"]) <= state.MAX_FAILURE and wit_data["total_supports"] >= 2:
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
            info(f"Only 1 support and it's WIT but energy is too high for resting to be worth it. Still training.")
            state.FORCE_REST = True
            return "wit"
        else:
          info(f"Only 1 support and it's WIT. Skipping.")
          state.FORCE_REST = True
          return None

    if RACE_IF_LOW:
      if energy_level > state.NEVER_REST_ENERGY:
        if year_parts[0] not in ["Junior", "Finale"] and year_parts[3] not in ["Jul", "Aug"]:
          from utils.process import do_race

          fake_criteria = "fan"
          keywords = ("fan", "Maiden", "Progress")
          fake_turn = 1

          info("Training point is too low and energy is high, try to do graded race.")
          race_found, race_name = decide_race_for_goal(year, fake_turn, fake_criteria, keywords)
          info(f"[RACE_IF_LOW] race_found={race_found}, race_name={race_name}")

          if race_name:
            race = do_race(race_found, img=race_name)
          else:
            race = False

          if race is True:
            return
          elif race is False:
            return best_key
          else:
            click(img="assets/buttons/back_btn.png", minSearch=get_secs(1), text="No suitable race found.")
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

  info(f"Best training: {best_key.upper()} with {best_data['total_supports']} support cards, {best_data['total_non_maxed_support']} non-maxed support cards with {best_data['failure']}% fail chance and {best_data['total_hints']} total hint.")
  return best_key

PRIORITY_WEIGHTS_LIST={
  "HEAVY": 0.75,
  "MEDIUM": 0.5,
  "LIGHT": 0.25,
  "NONE": 0
}

def training_score(x):
  global PRIORITY_WEIGHTS_LIST
  priority_weight = PRIORITY_WEIGHTS_LIST[state.PRIORITY_WEIGHT]
  base = x[1]["total_supports"]
  non_max_friends = x[1]["total_friendship_levels"]["gray"] + \
                    x[1]["total_friendship_levels"]["blue"] + \
                    x[1]["total_friendship_levels"]["green"]
  base += non_max_friends * 0.5
  if x[1]["total_hints"] > 0:
      base += state.HINT_POINT
  multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(x[0])] * priority_weight
  total = base * multiplier

  # Debug output
  debug(f"{x[0]} -> base={base}, multiplier={multiplier}, total={total}, priority={get_stat_priority(x[0])}")

  return (total, -get_stat_priority(x[0]))

def filter_by_stat_caps(results, current_stats):
  return {
    stat: data for stat, data in results.items()
    if current_stats.get(stat, 0) < state.STAT_CAPS.get(stat, 1200)
  }

def all_values_equal(dictionary):
    values = list(dictionary.values())
    return all(value == values[0] for value in values[1:])

# helper functions
def decide_race_for_goal(year, turn, criteria, keywords):
    no_race = (False, None)
    year_parts = year.split(" ")

    # Skip pre-debut
    if year == "Junior Year Pre-Debut":
        return no_race
    if turn >= 10:
        return no_race

    criteria_text = criteria or ""
    criteria_text = criteria_text.lower()

    if any(word in criteria_text for word in keywords):
        info("Criteria word found. Trying to find races.")

        if state.DONE_DEBUT:
            GRADED_TRIGGERS = ("progress", "fan")
            if any(w in criteria_text for w in GRADED_TRIGGERS):
                info(f'"progress" or "fan" is in criteria text.')

                # Get races for this year
                race_list = constants.RACE_LOOKUP.get(year, [])
                if not race_list:
                    return False, None

                if year_parts[0] in ["Junior"]:
                    ALLOWED_GRADES = {"G1", "G2", "G3"}
                else:
                    ALLOWED_GRADES = {"G1", "G2", "G3"}

                filtered = [r for r in race_list if r.get("grade") in ALLOWED_GRADES]
                if not filtered:
                    info("No allow graded races available for this turn.")
                    return False, None

                if "G1" in criteria_text or "GI" in criteria_text:
                    info('Goal mentions "G1"; restricting to only G1 races.')
                    filtered = [r for r in filtered if r.get("grade") == "G1"]

                    if not filtered:
                        info("No G1 races available for this year.")
                        return False, None

                current_fans = state.FAN_COUNT
                
                if current_fans != -1:
                    filtered = [
                        r for r in filtered
                        if r.get("fans", {}).get("required", 0) <= current_fans
                    ]
                    if not filtered:
                        info(f"No races meet fan requirement. Current fans = {current_fans}.")
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