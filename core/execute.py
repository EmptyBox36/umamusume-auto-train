import pyautogui
from PIL import ImageGrab

pyautogui.useImageNotFoundException(False)

import core.state as state
from core.state import check_turn, check_mood, check_current_year, check_criteria, check_energy_level, stat_state, check_aptitudes, check_unity, stop_bot

from utils.log import info, warning, error, debug
import utils.constants as constants

from core.recognizer import is_btn_active, match_template, multi_match_templates
from utils.process import event_choice, check_fan, race_process, after_race
from utils.tools import click, sleep, wait_for_image, get_secs

from logic.ura import ura_logic
from logic.unity import race_prep, unity_logic, unity_race

templates = {
  "event": "assets/icons/event_choice_1.png",
  "acupuncture_accept": "assets/icons/acupuncture_confirm.png",
  "inspiration": "assets/buttons/inspiration_btn.png",
  "next": "assets/buttons/next_btn.png",
  "next2": "assets/buttons/next2_btn.png",
  "cancel": "assets/buttons/cancel_btn.png",
  "tazuna": "assets/ui/tazuna_hint.png",
  "infirmary": "assets/buttons/infirmary_btn.png",
  "retry": "assets/buttons/retry_btn.png",
  "close": "assets/unity_cup/close_btn.png",
  "complete": "assets/buttons/complete_btn.png",
  "view_result":"assets/buttons/view_results.png"
}

def career_lobby():
  # Program start
  state.PREFERRED_POSITION_SET = False
  state.DONE_DEBUT = False
  state.FAN_COUNT = -1
  state.APTITUDES = {}
  while state.is_bot_running and not state.stop_event.is_set():
    screen = ImageGrab.grab()
    matches = multi_match_templates(templates, screen=screen)

    if matches["complete"]:
        stop_bot()
        info("Career complete. Stop bot")
    if click(boxes=matches["acupuncture_accept"]):
      continue
    if event_choice():
      continue
    if check_unity():
      info("Unity Race Day")
      unity_race()
      continue
    if click(boxes=matches["inspiration"], text="Inspiration found."):
      continue
    if matches["view_result"]:
      race_process()
      continue
    if click(boxes=matches["next"], text="next"):
      continue
    if click(boxes=matches["next2"], text="next2"):
      continue
    if matches["cancel"]:
      clock_icon = match_template("assets/icons/clock_icon.png", threshold=0.8)
      if clock_icon:
        stop_bot()
        info("Lost race, Stopping the bot.")
        continue
      else:
        click(boxes=matches["cancel"])
        continue
    if click(boxes=matches["retry"], text="retry"):
      continue
    if click(boxes=matches["close"], text="close"):
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
    criteria = check_criteria()
    current_stats = stat_state()

    if (not state.DONE_DEBUT or state.FAN_COUNT == -1) and year != "Junior Year Pre-Debut":
      check_fan()

    state.CURRENT_ENERGY_LEVEL = energy_level
    state.MAX_ENERGY = max_energy
    state.CURRENT_MOOD_INDEX = mood_index
    state.CURRENT_STATS = current_stats
    state.CURRENT_YEAR = year
    state.CUSTOM_FAILURE = state.MAX_FAILURE
    state.CURRENT_TURN_LEFT = turn
    state.CRITERIA = criteria

    if state.DONE_DEBUT:
        debut_status = "Finish"
    else:
        debut_status = "Unfinish"

    state.FORCE_REST = False
    state.TRAINING_RESTRICTED = False

    print("\n=======================================================================================\n")
    info(f"Trainee: {state.TRAINEE_NAME}")
    info(f"Scenario: {state.SCENARIO_NAME}")
    print("\n=======================================================================================\n")
    info(f"Year: {year}")
    info(f"Mood: {mood}")
    info(f"Turn: {turn}")
    info(f"Criteria: {criteria}")
    print("\n=======================================================================================\n")
    info(f"Debut Status: {debut_status}")
    info(f"fans: {state.FAN_COUNT}")
    print("\n=======================================================================================\n")

    if "URA" in state.SCENARIO_NAME:
        ura_logic()

    if "Unity" in state.SCENARIO_NAME:
        unity_logic()
    
    continue