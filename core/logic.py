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
    if k != "wit" and int(v["failure"]) <= state.CUSTOM_FAILURE
  }

  # Check if train is bad
  all_others_bad = len(non_wit_results) == 0
  energy_level = state.CURRENT_ENERGY_LEVEL

  if energy_level < state.SKIP_TRAINING_ENERGY:
    info("All trainings are unsafe and WIT training won't help go back up to safe levels, resting instead.")
    return None

  if all_others_bad and wit_data and int(wit_data["failure"]) <= state.CUSTOM_FAILURE and wit_data["total_supports"] >= 2:
    info("All trainings are unsafe, but WIT is safe and has enough support cards.")
    return "wit"

  filtered_results = {
    k: v for k, v in results.items() if int(v["failure"]) <= state.CUSTOM_FAILURE
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

# Do training
def training_logic(results):
  global PRIORITY_WEIGHTS_LIST
  year = state.CURRENT_YEAR
  year_parts = year.split(" ")
  energy_level = state.CURRENT_ENERGY_LEVEL
  priority_weight = PRIORITY_WEIGHTS_LIST[state.PRIORITY_WEIGHT]
  # 2 points for rainbow supports, 1 point for normal supports, 1.5 point for non-maxed supports, +0.5 For Hint, stat priority tie breaker

  training_candidates = results
  for stat_name in training_candidates:
    multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(stat_name)] * priority_weight
    data = training_candidates[stat_name]
    total_rainbow_friends = data[stat_name]["friendship_levels"]["yellow"] + data[stat_name]["friendship_levels"]["max"]
    total_non_maxed_support = data["total_supports"] - ( data["total_friendship_levels"]["yellow"] + data["total_friendship_levels"]["max"] )

    if "Junior Year" in year:
        if not state.JUNIOR_YEAR_STAT_PRIORITIZE:
            multiplier = 1

    #adding total rainbow friends on top of total supports for two times value nudging the formula towards more rainbows
    total_points = ( 1.5 * total_rainbow_friends) + ( 1 * total_non_maxed_support )

    hint_with_non_maxed = 0
    if data["total_hints"] > 0 and total_non_maxed_support > 0:
      hint_with_non_maxed = 1
      total_points = total_points + hint_with_non_maxed
    
    training_candidates[stat_name]["easy_point"] = total_points

    if data["total_hints"] > 0:
      total_points = total_points + state.HINT_POINT - hint_with_non_maxed
    if total_rainbow_friends > 1:
      total_points = total_points + (1 * total_rainbow_friends)
    if total_non_maxed_support > 2:
      total_points = total_points + (2 * total_non_maxed_support)
 
    # Now, Non-maxed = 1, Rainbow = 1.5, if more than 1 rainbow (1 Rainbow = 2.5), if more than 2 non-maxed (1 non-maxed = 3), 0.25 per maxed supports
    # use this training logic: https://docs.google.com/spreadsheets/d/e/2PACX-1vRwrUHivwEYuyROD3oxp5VaKAzpQLUBszAImv38tjEq64_7KiTsktXyDgJA0XEWlU4STFwTPPWw2ONu/pubhtml?gid=0&single=true

    total_points = total_points + (0.25 * (data["total_supports"] - total_rainbow_friends - total_non_maxed_support))
    total_points = total_points * multiplier
    training_candidates[stat_name]["total_points"] = total_points
    training_candidates[stat_name]["total_rainbow_friends"] = total_rainbow_friends
    training_candidates[stat_name]["total_non_maxed_support"] = total_non_maxed_support

    info(f"[{stat_name.upper()}] -> Total Non-Maxed Supports: {total_non_maxed_support}, Total Rainbow Supports: {total_rainbow_friends}, Training point: {total_points}, Condition point:{training_candidates[stat_name]['easy_point']}")

  any_nonmaxed = any(
    data.get("total_non_maxed_support", 0) > 0 
    for data in training_candidates.values())

  highest_points = max(
      training_candidates.items(),
      key=lambda kv: (
          kv[1]["easy_point"],
          -get_stat_priority(kv[0])
      ),
  )

  best_stat, best_point = highest_points
  if state.ENABLE_CUSTOM_FAILURE_CHANCE:
      if state.ENABLE_CUSTOM_HIGH_FAILURE:
          if best_point["easy_point"] > state.HIGH_FAILURE_CONDITION["point"]:
              state.CUSTOM_FAILURE = state.HIGH_FAILURE_CONDITION["failure"]
              info(f"Due to {best_stat.upper()} have high ({best_point['easy_point']}) training point, set maximum failure to {state.CUSTOM_FAILURE}%.")

      # if state.ENABLE_CUSTOM_LOW_FAILURE:
      #     if best_point["easy_point"] < state.LOW_FAILURE_CONDITION["point"]:
      #         state.CUSTOM_FAILURE = state.LOW_FAILURE_CONDITION["failure"]
      #         info(f"Due to {best_stat.upper()} have low ({best_point['easy_point']}) training point, set maximum failure to {state.CUSTOM_FAILURE}%.")

  # Filter out high failure
  training_candidates = {
    stat: data for stat, data in results.items()
    if int(data["failure"]) <= state.CUSTOM_FAILURE
    and not (stat == "wit" and data["easy_point"] < 1)}

  if best_point["easy_point"] < 3 and year_parts[0] in ["Classic", "Senior"] and year_parts[3] in ["Jun"]:
    if (year_parts[2] in ["Early"] and state.CURRENT_TURN_LEFT == "1") or year_parts[2] in ["Late"]:
      if state.CURRENT_ENERGY_LEVEL <= 50:
        state.FORCE_REST = True
        info(f"Next turn is summer camp and training not good enough. Do rest.")
        return False
      else:
        info(f"Next turn is summer camp and training not good enough. Train WIT to get some energy.")
        return "wit"

  if not training_candidates:
    if energy_level > state.SKIP_TRAINING_ENERGY:
      info(f"No suitable training in training logic. But have energy more than skip training energy. Fallback to most support training.")
      return None
    if energy_level <= state.SKIP_TRAINING_ENERGY:
      info(f"Energy level is lower that skip training energy. Do rest.")
      return False

  if len(training_candidates) == 1 and "wit" in training_candidates:
    if any_nonmaxed:
        info(f"Fallback to most support training to avoid training too much wit on junior year.")
        return None

  # training_candidates = {
  #   stat: data for stat, data in results.items()
  #   if int(data["failure"]) <= state.CUSTOM_FAILURE
  #      and data["easy_point"] >= 1
  #      and not (stat == "wit" and data["easy_point"] < 1)
  # }

  # if not training_candidates:
  #   info("No suitable training found under failure threshold.")
  #   return None

  # Find support card in training
  best_rainbow = max(
    training_candidates.items(),
    key=lambda x: (
      x[1]["total_points"],
      -get_stat_priority(x[0])
    )
  )

  best_key, best_data = best_rainbow
  if best_data["easy_point"] < 1.5:
    info(f"Max Friend Value less or equal to 1")
    if training_candidates.get("wit", {}).get("easy_point", 0) >= 1:
        info(f"WIT have Friend Value = 1, train WIT.")
        return "wit"
    elif best_data["easy_point"] == 0:
        if energy_level > 50:
            info(f"Proceeding to most support training.")
            return None

        if energy_level >= state.NEVER_REST_ENERGY:
            info(f"Energy is higher than never rest energy. Fallback to most support training.")
            return None
        else:
            return False
    info(f"{best_key.upper()} have Friend Value = 1, train {best_key.upper()}.")
      
  info(f"Training logic selected: {best_key.upper()} with {best_data['total_points']} points and {best_data['failure']}% fail chance")
  return best_key

def filter_by_stat_caps(results, current_stats):
  return {
    stat: data for stat, data in results.items()
    if current_stats.get(stat, 0) < state.STAT_CAPS.get(stat, 1200)
  }

def all_values_equal(dictionary):
    values = list(dictionary.values())
    return all(value == values[0] for value in values[1:])

# Decide training
def do_something(results):
  year = state.CURRENT_YEAR
  current_stats = state.CURRENT_STATS
  info(f"Current stats: {current_stats}")

  filtered = filter_by_stat_caps(results, current_stats)

  if not filtered:
    info("All stats capped or no valid training.")
    return None

  # if "Junior Year" in year:
  #   result, best_score = focus_max_friendships(filtered)

  #   # If the best option for raising friendship is just one friend, with no hint bonus
  #   if best_score <= 1.3:
  #     return most_support_card(filtered)

  # else:
  result = training_logic(filtered)
  if result is None:
    info("Falling back to most_support_card because rainbow not available.")
    return most_support_card(filtered)
  elif result is False:
    return None
  return result

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
                    ALLOWED_GRADES = {"G1", "G2"}

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