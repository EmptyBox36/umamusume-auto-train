from PIL import ImageGrab
from typing import Tuple, List, Optional
from utils.log import info, warning, error, debug
from core.recognizer import is_btn_active, match_template, multi_match_templates
from utils.tools import click, sleep, get_secs
from utils.process import do_race, auto_buy_skill, race_day, do_rest, race_prep, after_race, do_recreation, do_train, go_to_training, check_training
from core.state import check_status_effects, check_criteria, check_aptitudes, stop_bot
from core.logic import decide_race_for_goal, most_support_card
from utils.scenario import ura

import core.state as state
import utils.constants as constants

templates = {
  "infirmary": "assets/buttons/infirmary_btn.png",
}

PRIORITY_WEIGHTS_LIST={
  "HEAVY": 0.75,
  "MEDIUM": 0.5,
  "LIGHT": 0.25,
  "NONE": 0
}

screen = ImageGrab.grab()
matches = multi_match_templates(templates, screen=screen)

# Get priority stat from config
def _get_stat_priority(stat_key: str) -> int:
  if stat_key in state.PRIORITY_STAT:
    return state.PRIORITY_STAT.index(stat_key) 
  return 999

def _filter_by_stat_caps(results, current_stats):
  return {
    stat: data for stat, data in results.items()
    if current_stats.get(stat, 0) < state.STAT_CAPS.get(stat, 1200)
  }

def _friend_recreation() -> bool:
    if match_template("assets/icons/friend_recreation_available.png", region=(125, 800, 1000, 1080)): # SCREEN_BOTTOM_REGION
        return True
    return False

def _need_recreation(year: str) -> bool:
  current_mood = state.CURRENT_MOOD_INDEX
  minimum_mood = constants.MOOD_LIST.index(state.MINIMUM_MOOD)
  minimum_mood_with_friend = constants.MOOD_LIST.index(state.MINIMUM_MOOD_WITH_FRIEND)
  minimum_mood_junior_year = constants.MOOD_LIST.index(state.MINIMUM_MOOD_JUNIOR_YEAR)
  year_parts = year.split(" ")

  if year_parts[0] == "Junior":
    mood_check = minimum_mood_junior_year
  else:
    if _friend_recreation():
      # debug("Friend recreation is available")
      mood_check = minimum_mood_with_friend
    else:
      mood_check = minimum_mood

  missing_mood =  mood_check - current_mood
  return missing_mood

def _need_infirmary() -> Tuple[Optional[List[str]], int, Optional[object]]:
  if matches["infirmary"] and is_btn_active(matches["infirmary"][0]):
    info("Check for condition.")
    if click(img="assets/buttons/full_stats.png", minSearch=get_secs(1)):
      sleep(0.5)
      conditions, total_severity = check_status_effects()
      click(img="assets/buttons/close_btn.png", minSearch=get_secs(1))
      return (conditions, total_severity, matches["infirmary"][0])
    else:
        warning("Couldn't find full stats button.")
  return (None, 0, None)

def _summer_next_turn(year: str) -> bool:
    year_parts = year.split(" ")
    if len(year_parts) < 4:
        return False
    if year_parts[0] in ["Classic", "Senior"] and year_parts[3] == "Jun":
        if year_parts[2] == "Early":
            if state.CURRENT_TURN_LEFT == 1:
                return True
            if any("Late Jun" in r.get("date", "") for r in state.RACE_SCHEDULE or []):
                return True
        if year_parts[2] == "Late":
            return True
    return False

def _summer_camp(year: str) -> bool:
    year_parts = year.split(" ")
    if len(year_parts) < 4:
        return False
    if year_parts[0] in ["Classic", "Senior"] and year_parts[3] in ["Jul","Aug"]:
        return True
    return False

def ura_training(results: dict):
    training_candidates = results
    energy_level = state.CURRENT_ENERGY_LEVEL
    year = state.CURRENT_YEAR
    priority_weight = PRIORITY_WEIGHTS_LIST[state.PRIORITY_WEIGHT]

    for stat_name in training_candidates:
        multiplier = 1 + state.PRIORITY_EFFECTS_LIST[_get_stat_priority(stat_name)] * priority_weight
        summer_multiplier = 1 + state.SUMMER_PRIORITY_EFFECTS_LIST[_get_stat_priority(stat_name)] * priority_weight

        data = training_candidates[stat_name]

        # max_friend_support_card = data["friend"]["friendship_levels"]["green"]  
        friend_value =  data["total_friendship_levels"]["gray"] + data["total_friendship_levels"]["blue"] + data["total_friendship_levels"]["green"]
        friend_training = data[stat_name]["friendship_levels"]["yellow"] + data[stat_name]["friendship_levels"]["max"]

        if friend_value > 2:
            friend_value += 0.5 * friend_value
        if friend_training > 1:
            friend_training += 0.5 * friend_training

        friend_value_point = 1
        rainbow_point = 1.5

        score = (friend_value_point * friend_value) + (rainbow_point * friend_training)

        data["score_befor_multiplier"] = score

        if data["total_hints"] > 0:
            score += state.HINT_POINT

        if _summer_camp(year):
            data["best_score"] = score * summer_multiplier
        else:
            data["best_score"] = score * multiplier

        info(f"[{stat_name.upper()}] -> Non Max Support: {friend_value}, Rainbow Support: {friend_training}, Hint: {data['total_hints']}")
        info(f"[{stat_name.upper()}] -> Score: {data['best_score']}")

    any_nonmaxed = any(
        data.get("total_non_maxed_support", 0) > 0 
        for data in training_candidates.values())

    best_stat, best_point = max(
        training_candidates.items(),
        key=lambda kv: (
            kv[1]["score_befor_multiplier"],
            -_get_stat_priority(kv[0])
        ),
    )

    if state.ENABLE_CUSTOM_FAILURE_CHANCE:
      if state.ENABLE_CUSTOM_HIGH_FAILURE:
          if best_point["score_befor_multiplier"] > state.HIGH_FAILURE_CONDITION["point"]:
              state.CUSTOM_FAILURE = state.HIGH_FAILURE_CONDITION["failure"]
              info(f"Due to {best_stat.upper()} have high ({best_point['score_befor_multiplier']}) training point, set maximum failure to {state.CUSTOM_FAILURE}%.")

      if state.ENABLE_CUSTOM_LOW_FAILURE:
          if best_point["score_befor_multiplier"] < state.LOW_FAILURE_CONDITION["point"]:
              state.CUSTOM_FAILURE = state.LOW_FAILURE_CONDITION["failure"]
              info(f"Due to {best_stat.upper()} have low ({best_point['score_befor_multiplier']}) training point, set maximum failure to {state.CUSTOM_FAILURE}%.")

    # filter by failure & avoid WIT spam
    filtered = {
        k: v for k, v in training_candidates.items()
        if int(v["failure"]) <= state.CUSTOM_FAILURE and not (k == "wit" and v["best_score"] < 1)
    }

    if not filtered:
        if energy_level > state.SKIP_TRAINING_ENERGY:
            info("No suitable training; fallback to most-support.")
            return "fallback", None
        else:
            info("Low energy; rest.")
            return None, None

    if len(filtered) == 1 and "wit" in filtered and any_nonmaxed:
        info("Only WIT available early; fallback to most-support.")
        return "fallback", None

    best_key, best_data = max(
        filtered.items(),
        key=lambda kv: (kv[1]["best_score"], -_get_stat_priority(kv[0])))
      
    info(f"[URA] Training selected: {best_key.upper()} with {best_data['best_score']} points and {best_data['failure']}% fail chance")
    return best_key, best_data

def ura_logic() -> str:
    criteria = state.CRITERIA
    turn = state.CURRENT_TURN_LEFT
    year = state.CURRENT_YEAR
    year_parts = year.split(" ")
    energy_level = state.CURRENT_ENERGY_LEVEL
    max_energy = state.MAX_ENERGY
    missing_energy = max_energy - energy_level
    current_stats = state.CURRENT_STATS

    if state.APTITUDES == {}:
        sleep(0.1)
        if click(img="assets/buttons/full_stats.png", minSearch=get_secs(1)):
            sleep(0.5)
            check_aptitudes()
            click(img="assets/buttons/close_btn.png", minSearch=get_secs(1))

    info(f"Current stats: {current_stats}")

    if turn == "Race Day":
        if "Finale" in year:
            info("URA Finale")
            if state.IS_AUTO_BUY_SKILL:
                auto_buy_skill()
            ura()
            for i in range(2):
                if not click(img="assets/buttons/race_btn.png", minSearch=get_secs(2)):
                    click(img="assets/buttons/bluestacks/race_btn.png", minSearch=get_secs(2))
                sleep(0.5)

            race_prep()
            sleep(1)
            after_race()

        # If calendar is race day, do race
        if "Finale" not in year:
            if match_template("assets/buttons/race_day_btn.png", region=(125, 800, 1000, 1080)): # SCREEN_BOTTOM_REGION
                info("Race Day.")
                if state.IS_AUTO_BUY_SKILL and year_parts[0] != "Junior":
                    auto_buy_skill()
                race_day()
        return

    if state.RACE_SCHEDULE:
      race_done = False
      for race_list in state.RACE_SCHEDULE:
        if state.stop_event.is_set():
          break
        if len(race_list):
          if race_list['year'] in year and race_list['date'] in year:
            debug(f"Race now, {race_list['name']}, {race_list['year']} {race_list['date']}")
            if do_race(state.PRIORITIZE_G1_RACE, img=race_list['name']):
              race_done = True
              break
            else:
              click(img="assets/buttons/back_btn.png", minSearch=get_secs(1), text=f"{race_list['name']} race not found. Proceeding to training.")
              sleep(0.5)
      if race_done:
        return

    if not "Achieved" in criteria:
        keywords = ("fan", "Maiden", "Progress")

        prioritize_g1, race_name = decide_race_for_goal(year, turn, criteria, keywords)
        info(f"prioritize_g1: {prioritize_g1}, race_name: {race_name}")
        if race_name:
            if race_name == "any":
                race_found = do_race(prioritize_g1, img=None)
            else:
                race_found = do_race(prioritize_g1, img=race_name)

            if race_found:
                return
            else:
                # If there is no race matching to aptitude, go back and do training instead
                click(img="assets/buttons/back_btn.png", minSearch=get_secs(1), text="Proceeding to training.")
                sleep(0.5)

    go_to_training()
    sleep(0.5)
    results_training = check_training()
    filtered = _filter_by_stat_caps(results_training, current_stats)

    if not filtered:
        info("All stats capped or no valid training")
        return

    result, best_data = ura_training(filtered)

    if _summer_next_turn(year):
        if best_data is None:
            state.FORCE_REST = True
            info("[URA] Summer camp next & low energy → Rest.")
            do_rest(energy_level)
            return

        if best_data["best_score"] < 2:
            if state.CURRENT_ENERGY_LEVEL <= 50:
                state.FORCE_REST = True
                info("[URA] Summer camp next & low energy → Rest.")
                do_rest(energy_level)
            else:
                info("[URA] Summer camp next & okay energy → Train WIT.")
                sleep(0.5)
                go_to_training()
                sleep(0.5)
                do_train("wit")
            return

    missing_mood = _need_recreation(year)
    summer_camp = _summer_camp(year)

    if matches["infirmary"] and is_btn_active(matches["infirmary"][0]):
        conditions, total_severity, infirmary_box = _need_infirmary()
        if total_severity > 0:
            if total_severity <= 1 and missing_mood > 0 and not (summer_camp and missing_energy < 40):
                info("[URA] Mood low & Status condition present → Recreation.")
                sleep(0.5)
                do_recreation()
                return
            # infirmary always gives 20 energy, it's better to spend energy before going to the infirmary 99% of the time.
            if max(0, missing_energy) < state.SKIP_INFIRMARY_UNLESS_MISSING_ENERGY:
                if total_severity > 1 and infirmary_box:
                    info(f"Urgent condition ({conditions}) found, visiting infirmary immediately.")
                    sleep(0.5)
                    click(boxes=infirmary_box, text="Character debuffed, going to infirmary.")
                    return
                else:
                    info(f"Non-urgent condition ({conditions}) found, skipping infirmary because of high energy.")
            else:
                if infirmary_box:
                    info("[URA] Status condition present → Infirmary.")
                    sleep(0.5)
                    click(boxes=infirmary_box, text="Character debuffed, going to infirmary.")
                    return
    if not summer_camp:
        if missing_mood > 1:
            info("[URA] Mood is low → Recreation.")
            sleep(0.5)
            do_recreation("friend")
            return

    if best_data is not None:
        if best_data["best_score"] >= 3 or (summer_camp and best_data["best_score"] >= 1.5):
            info(f"[URA] Best Trainind Found → Train {result.upper()}.")
            sleep(0.5)
            go_to_training()
            sleep(0.5)
            do_train(result)
            return

    if missing_mood > 0 and not (summer_camp and missing_energy < 40):
        info("[URA] Mood is low → Recreation.")
        sleep(0.5)
        do_recreation("friend")
        return

    if best_data is not None:
        if best_data["best_score"] >= 1:
            info(f"[URA] Found 1 Friend Training → Train {result.upper()}.")
            sleep(0.5)
            go_to_training()
            sleep(0.5)
            do_train(result)
            return

    if best_data is not None:
        if best_data["best_score"] >= 0:
            info(f"[URA] Use most_support_card.")
            results = most_support_card(filtered)
            if results is not None:
                if results is not False:
                   sleep(0.5)
                   go_to_training()
                   sleep(0.5)
                   do_train(results)
                   info(f"[URA] most_support_card training found → Train {results.upper()}.")
                   return

    if result == "fallback":
        info(f"[URA] Use most_support_card.")
        results = most_support_card(filtered)
        if results is not None:
            if results is not False:
                sleep(0.5)
                go_to_training()
                sleep(0.5)
                do_train(results)
                info(f"[URA] most_support_card training found → Train {results.upper()}.")
                return

    if "Finale" in year:
        if _friend_recreation():
            sleep(0.5)
            do_recreation("friend")
            return
        if "Finals" in criteria:
            sleep(0.5)
            go_to_training()
            sleep(0.5)
            do_train("wit")
            info(f"[URA] No training found, but it was last turn → Train WIT.")
            return

    info(f"[URA] No training found → Rest.")
    do_rest(energy_level)
    sleep(1)
    return