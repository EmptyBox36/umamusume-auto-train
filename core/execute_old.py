import pyautogui
from utils.tools import sleep, get_secs, drag_scroll
from PIL import ImageGrab
import cv2
import os
import numpy as np
import time

pyautogui.useImageNotFoundException(False)

import re
import core.state as state
from core.state import check_support_card, check_failure, check_turn, check_mood, check_current_year, check_criteria, check_skill_pts, check_energy_level, get_race_type, check_status_effects, check_aptitudes, stat_state
from core.logic import do_something, decide_race_for_goal

from utils.log import info, warning, error, debug
import utils.constants as constants

from core.recognizer import is_btn_active, match_template, multi_match_templates
from utils.scenario import ura
from core.skill import buy_skill
from core.events import get_optimal_choice
from core.state import get_event_name, stop_bot
from utils.capture import screenshot_bgr
from utils.tools import click, event_choice, auto_buy_skill, race_prep, after_race, race_day, do_race
from utils.tools import do_recreation, go_to_training, check_training, do_train, do_rest

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

PREFERRED_POSITION_SET = False
current_stats = stat_state()
def career_lobby():
  # Program start
  global PREFERRED_POSITION_SET, current_stats
  PREFERRED_POSITION_SET = False
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
    minimum_mood = constants.MOOD_LIST.index(state.MINIMUM_MOOD)
    minimum_mood_junior_year = constants.MOOD_LIST.index(state.MINIMUM_MOOD_JUNIOR_YEAR)
    turn = check_turn()
    year = check_current_year()
    criteria = check_criteria()
    year_parts = year.split(" ")
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
    info(f"Year: {year}")
    info(f"Mood: {mood}")
    info(f"Turn: {turn}")
    info(f"Criteria: {criteria}")
    print("\n=======================================================================================\n")

    # URA SCENARIO
    if year == "Finale Season" and turn == "Race Day":
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
      continue

    # If calendar is race day, do race
    if turn == "Race Day" and year != "Finale Season":
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

    # If Prioritize G1 Race is true, check G1 race every turn
    if state.PRIORITIZE_G1_RACE and "Pre-Debut" not in year and len(year_parts) > 3 and year_parts[3] not in ["Jul", "Aug"]:
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

    # Mood & Infirmary check
    if year_parts[0] == "Junior":
      mood_check = minimum_mood_junior_year
    else:
      mood_check = minimum_mood

    if mood_index < mood_check:
      info("Check condition before choose to recreation or infirmary.")
      if click(img="assets/buttons/full_stats.png", minSearch=get_secs(1)):
        sleep(0.5)
        conditions, total_severity = check_status_effects()
        click(img="assets/buttons/close_btn.png", minSearch=get_secs(1))
        sleep(0.5)
        if total_severity > 1:
          info("Urgent condition found, visiting infirmary.")
          click(boxes=matches["infirmary"][0])
          continue
        else:
          info("Mood is low, trying recreation to increase mood")
          do_recreation()
          continue
      else:
        warning("Coulnd't find full stats button.")
        stop_bot()
        continue

    # Infirmary
    skipped_infirmary=False
    if matches["infirmary"] and is_btn_active(matches["infirmary"][0]):
      # infirmary always gives 20 energy, it's better to spend energy before going to the infirmary 99% of the time.
      if max(0, (max_energy - energy_level)) < state.SKIP_INFIRMARY_UNLESS_MISSING_ENERGY:
        info("Check for urgent condition.")
        if click(img="assets/buttons/full_stats.png", minSearch=get_secs(1)):
          sleep(0.5)
          conditions, total_severity = check_status_effects()
          click(img="assets/buttons/close_btn.png", minSearch=get_secs(1))
          if total_severity > 1:
            info("Urgent condition found, visiting infirmary immediately.")
            click(boxes=matches["infirmary"][0])
            continue
          else:
            info(f"Non-urgent condition found, skipping infirmary because of high energy.")
            skipped_infirmary=True
        else:
          warning("Coulnd't find full stats button.")
      else:
        click(boxes=matches["infirmary"][0], text="Character debuffed, going to infirmary.")
        continue

    # Check if we need to race for goal
    if not "Achieved" in criteria:
      if state.APTITUDES == {}:
        sleep(0.1)
        if click(img="assets/buttons/full_stats.png", minSearch=get_secs(1)):
          sleep(0.5)
          check_aptitudes()
          click(img="assets/buttons/close_btn.png", minSearch=get_secs(1))
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

    # Check training button
    if not go_to_training():
      debug("Training button is not found.")
      continue

    # Last, do training
    sleep(0.5)
    results_training = check_training()

    best_training = do_something(results_training)
    if best_training:
      go_to_training()
      sleep(0.5)
      do_train(best_training)
    else:
      if year_parts[0] == "Finale" and "Finals" in criteria:
        go_to_training()
        sleep(0.5)
        do_train("wit")
      else:
        do_rest(energy_level)
    sleep(1)
