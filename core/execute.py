import pyautogui
from utils.tools import sleep, get_secs, drag_scroll
from PIL import ImageGrab

pyautogui.useImageNotFoundException(False)

import core.state as state
from core.state import check_turn, check_mood, check_current_year, check_criteria, check_energy_level, stat_state, check_aptitudes

from utils.log import info, warning, error, debug
import utils.constants as constants

from core.recognizer import is_btn_active, match_template, multi_match_templates
from utils.process import go_to_training, check_training, event_choice, click, do_race, do_rest, do_train, do_recreation, auto_buy_skill, race_prep, after_race, race_day
import logic.ura as ura_logic
from core.logic import most_support_card, decide_race_for_goal
from utils.scenario import ura

templates = {
  "event": "assets/icons/event_choice_1.png",
  "acupuncture": "assets/icons/acupuncture_confirm.png",
  "inspiration": "assets/buttons/inspiration_btn.png",
  "next": "assets/buttons/next_btn.png",
  "next2": "assets/buttons/next2_btn.png",
  "cancel": "assets/buttons/cancel_btn.png",
  "tazuna": "assets/ui/tazuna_hint.png",
  "infirmary": "assets/buttons/infirmary_btn.png",
  "retry": "assets/buttons/retry_btn.png"
}

state.PREFERRED_POSITION_SET = False
def career_lobby():
  # Program start
  state.PREFERRED_POSITION_SET = False
  while state.is_bot_running and not state.stop_event.is_set():
    screen = ImageGrab.grab()
    matches = multi_match_templates(templates, screen=screen)

    if click(boxes=matches["acupuncture"]):
      continue
    if event_choice():
      continue
    if click(boxes=matches["inspiration"], text="Inspiration found."):
      continue
    if click(boxes=matches["next"]):
      continue
    if click(boxes=matches["next2"]):
      continue
    if click(boxes=matches["cancel"]):
      continue
    if click(boxes=matches["retry"]):
      continue
    if click(img="assets/buttons/back_btn.png"):
      continue

    if not matches["tazuna"]:
      #info("Should be in career lobby.")
      print(".", end="")
      continue

    energy_level, max_energy = check_energy_level()

    mood = check_mood()
    mood_index = constants.MOOD_LIST.index(mood)
    turn = check_turn()
    year = check_current_year()
    year_parts = year.split(" ")
    criteria = check_criteria()
    current_stats = stat_state()

    state.FORCE_REST = False
    state.CURRENT_ENERGY_LEVEL = energy_level
    state.MAX_ENERGY = max_energy
    state.CURRENT_MOOD_INDEX = mood_index
    state.CURRENT_STATS = current_stats
    state.CURRENT_YEAR = year
    state.CUSTOM_FAILURE = state.MAX_FAILURE
    state.CURRENT_TURN_LEFT = turn

    print("\n=======================================================================================\n")
    info(f"Trainee: {state.TRAINEE_NAME}")
    info(f"Scenario: {state.SCENARIO_NAME}")
    print("\n=======================================================================================\n")
    info(f"Year: {year}")
    info(f"Mood: {mood}")
    info(f"Turn: {turn}")
    info(f"Criteria: {criteria}")
    print("\n=======================================================================================\n")

    if state.SCENARIO_NAME == "URA Finale":
        if state.APTITUDES == {}:
            sleep(0.1)
            if click(img="assets/buttons/full_stats.png", minSearch=get_secs(1)):
              sleep(0.5)
              check_aptitudes()
              click(img="assets/buttons/close_btn.png", minSearch=get_secs(1))

        info(f"Current stats: {current_stats}")

        if turn == "Race Day":
            if year == "Finale Season":
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
            if year != "Finale Season":
              info("Race Day.")
              if state.IS_AUTO_BUY_SKILL and year_parts[0] != "Junior":
                auto_buy_skill()
              race_day()
            continue

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
            continue

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
              continue
            else:
              # If there is no race matching to aptitude, go back and do training instead
              click(img="assets/buttons/back_btn.png", minSearch=get_secs(1), text="Proceeding to training.")
              sleep(0.5)

        go_to_training()
        results_training = check_training()
        filtered = ura_logic._filter_by_stat_caps(results_training, current_stats)

        if not filtered:
          info("All stats capped or no valid training")
          continue

        result, best_data = ura_logic.ura_training(filtered)

        if best_data is not None:
            if best_data["best_score"] < 2 and ura_logic._summer_next_turn() :
                if ura_logic._low_energy():
                    state.FORCE_REST = True
                    info("[URA] Summer camp next & low energy → Rest.")
                    do_rest(energy_level)
                else:
                    info("[URA] Summer camp next & okay energy → Train WIT.")
                    go_to_training()
                    sleep(0.5)
                    do_train("wit")
                continue

        conditions, total_severity, infirmary_box = ura_logic._need_infirmary()
        if total_severity > 0:
            if total_severity <= 1 and ura_logic._need_recreation():
                info("[URA] Mood low & Status condition present → Recreation.")
                sleep(0.5)
                do_recreation()
                continue
            # infirmary always gives 20 energy, it's better to spend energy before going to the infirmary 99% of the time.
            if max(0, (max_energy - energy_level)) < state.SKIP_INFIRMARY_UNLESS_MISSING_ENERGY:
                if total_severity > 1 and infirmary_box:
                    info(f"Urgent condition ({conditions}) found, visiting infirmary immediately.")
                    sleep(0.5)
                    click(boxes=infirmary_box, text="Character debuffed, going to infirmary.")
                    continue
                else:
                    info(f"Non-urgent condition ({conditions}) found, skipping infirmary because of high energy.")
            else:
                if infirmary_box:
                    info("[URA] Status condition present → Infirmary.")
                    sleep(0.5)
                    click(boxes=infirmary_box, text="Character debuffed, going to infirmary.")
                    continue

        if best_data is not None:
            if best_data["best_score"] >= 2:
                info(f"[URA] Best Trainind Found → Train {result.upper()}.")
                go_to_training()
                sleep(0.5)
                do_train(result)
                continue

        if ura_logic._need_recreation():
            info("[URA] Mood is low → Recreation.")
            sleep(0.5)
            do_recreation()
            continue

        if best_data is not None:
            if best_data["best_score"] >= 1.1:
                info(f"[URA] Found 1 Friend Training → Train {result.upper()}.")
                go_to_training()
                sleep(0.5)
                do_train(result)
                continue

        if best_data is not None:
            if best_data["best_score"] >= 0 :
                info(f"[URA] Use most_support_card.")
                result = most_support_card(filtered)
                if result is not None:
                    go_to_training()
                    sleep(0.5)
                    do_train(result)
                    info(f"[URA] most_support_card training found → Train {result.upper()}.")
                    continue

        if year_parts[0] == "Finale" and "Finals" in criteria:
            go_to_training()
            sleep(0.5)
            do_train("wit")
            info(f"[URA] No training found, but it was last turn → Train WIT.")
            continue

        info(f"[URA] No training found → Rest.")
        do_rest(energy_level)
        sleep(1)