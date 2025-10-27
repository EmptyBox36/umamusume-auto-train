from pickle import TRUE
from statistics import StatisticsError

from cv2.gapi import mul
from core.state import HINT_POINT
from core.state import check_current_year, stat_state, check_energy_level, check_aptitudes
from utils.log import info, warning, error, debug
from utils.tools import sleep, get_secs

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
    k: {
        **v,
        "total_non_maxed_support": v["total_supports"] - (
            v["total_friendship_levels"]["yellow"] + v["total_friendship_levels"]["max"]
        )
    }
    for k, v in results.items() if int(v["failure"]) <= state.CUSTOM_FAILURE
    }

  if not filtered_results:
    info("No safe training found. All failure chances are too high.")
    return None

  # this is the weight adder used for skewing results of training decisions PRIORITY_EFFECTS_LIST[get_stat_priority(x[0])] * PRIORITY_WEIGHTS_LIST[priority_weight]
  # Best training
  best_training = max(filtered_results.items(), key=training_score)

  best_key, best_data = best_training
  
  if best_data["total_supports"] <= 1:
    if int(best_data["failure"]) == 0:
      # WIT must be at least 2 support cards
      if best_key == "wit":
          if energy_level > state.NEVER_REST_ENERGY:
              info(f"Only 1 support and it's WIT but energy is too high for resting to be worth it. Still training.")
              return "wit"
          else:
            info(f"Only 1 support and it's WIT. Skipping.")
            return None
      info(f"Only 1 support but 0% failure. Prioritizing based on priority list: {best_key.upper()}")
      return best_key
    else:
      if energy_level > state.NEVER_REST_ENERGY:
        info(f"Energy is over {state.NEVER_REST_ENERGY}, train anyway.")
        return best_key
      else:
        info("Low value training (only 1 support). Choosing to rest.")
        return None

  info(f"Best training: {best_key.upper()} with {best_data['total_supports']} support cards, {best_data['total_non_maxed_support']} non-maxed support cards with {best_data['failure']}% fail chance and {best_data['total_hints']} total hint.")
  return best_key

PRIORITY_WEIGHTS_LIST={
  "HEAVY": 0.75,
  "MEDIUM": 0.5,
  "LIGHT": 0.25,
  "NONE": 0
}

def training_score(x, all_zero_non_maxed=False):
  global PRIORITY_WEIGHTS_LIST, HINT_POINT
  priority_weight = PRIORITY_WEIGHTS_LIST[state.PRIORITY_WEIGHT]

  if all_zero_non_maxed:
      # If all "total_non_maxed_support" are zero, use "total_supports" as criteria.
      base = x[1]["total_supports"]
  else:
      # If all "total_non_maxed_support" are not zero, use "total_non_maxed_support" as criteria.
      base = x[1]["total_non_maxed_support"] 
  if x[1]["total_hints"] > 0:
      base += state.HINT_POINT
  multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(x[0])] * priority_weight
  total = base * multiplier

  # Debug output
  debug(f"{x[0]} -> base={base}, multiplier={multiplier}, total={total}, priority={get_stat_priority(x[0])}")

  return (total, -get_stat_priority(x[0]))

# def focus_max_friendships(results):
#   global PRIORITY_WEIGHTS_LIST
#   priority_weight = PRIORITY_WEIGHTS_LIST[state.PRIORITY_WEIGHT]

#   filtered_results = {
#       stat: data for stat, data in results.items()
#       if int(data["failure"]) <= state.CUSTOM_FAILURE
#   }

#   if not filtered_results:
#       debug("No trainings under CUSTOM_FAILURE, falling back to most_support_card.")
#       return None, 0

#   for stat_name in filtered_results:
#     if state.JUNIOR_YEAR_STAT_PRIORITIZE:
#       junior_year_multiplier = 1 + state.PRIORITY_EFFECTS_LIST[get_stat_priority(stat_name)] * priority_weight
#     else:
#       junior_year_multiplier = 1

#     data = filtered_results[stat_name]
#     total_rainbow_friends = data[stat_name]["friendship_levels"]["yellow"] + data[stat_name]["friendship_levels"]["max"]
#     # order of importance gray > blue > green, because getting greens to max is easier than blues (gray is very low blue)
#     possible_friendship = (
#                             data["total_friendship_levels"]["green"] * 1.0
#                             + data["total_friendship_levels"]["blue"] * 1.01
#                             + data["total_friendship_levels"]["gray"] * 1.02
#                             + total_rainbow_friends * 0.5
#                           ) * junior_year_multiplier

#     # hints are worth a little more than half a training
#     if data["total_hints"] > 0:
#       hint_values = { "gray": 0.612, "blue": 0.606, "green": 0.6 }
#       for level, bonus in hint_values.items():
#         if data["hints_per_friend_level"].get(level, 0) > 0:
#             possible_friendship += bonus
#             break

#     debug(f"{stat_name} : gray={data['total_friendship_levels']['gray']}, blue={data['total_friendship_levels']['blue']}, green={data['total_friendship_levels']['green']}, total={possible_friendship:.3f}")
#     filtered_results[stat_name]["possible_friendship"] = possible_friendship

#   best_key = max(filtered_results, key=lambda k: (filtered_results[k]["possible_friendship"], -get_stat_priority(k)))
#   best_score = filtered_results[best_key]["possible_friendship"]
#   return best_key, best_score

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

    info(f"[{stat_name.upper()}] -> Total Non-Maxed Supports: {total_non_maxed_support}, Training point: {total_points}")

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

  if not training_candidates:
    if energy_level > state.SKIP_TRAINING_ENERGY:
      info(f"No suitable training in training logic. But have energy more than skip training energy. Fallback to most support training.")
      return None
    if energy_level <= state.SKIP_TRAINING_ENERGY:
      info(f"Energy level is lower that skip training energy. Do rest.")
      return False

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
            if year_parts[0] not in ["Junior", "Finale"] and year_parts[3] not in ["Jul", "Aug"]:
                from core.execute import do_race
                info("Training point is too low and have high energy, try to do race.")
                race = do_race()
                if race is True:
                    return False
                else:
                    from core.execute import click
                    click(img="assets/buttons/back_btn.png", minSearch=get_secs(1), text="No suitable race found. Proceeding to most support training.")
                    sleep(0.5)
                    return None
            else:
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
  year = check_current_year()
  current_stats = stat_state()
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
  no_race = False, None
  # Check if goals is not met criteria AND it is not Pre-Debut AND turn is less than 10 AND Goal is already achieved
  if year == "Junior Year Pre-Debut":
    return no_race
  if turn >= 10:
    return no_race
  criteria_text = criteria or ""
  if any(word in criteria_text for word in keywords):
    info("Criteria word found. Trying to find races.")
    if "Progress" in criteria_text:
      info("Word \"Progress\" is in criteria text.")
      # check specialized goal
      if "G1" in criteria_text or "GI" in criteria_text:
        info("Word \"G1\" is in criteria text.")
        race_list = constants.RACE_LOOKUP.get(year, [])
        if not race_list:
          return False, None
        else:
          best_race = filter_races_by_aptitude(race_list, state.APTITUDES)
          return True, best_race["name"]
      else:
        return False, "any"
    else:
      # if there's no specialized goal, just do any race
      return False, "any"
  return no_race

def filter_races_by_aptitude(race_list, aptitudes):
  GRADE_SCORE = {"a": 2, "b": 1}

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
