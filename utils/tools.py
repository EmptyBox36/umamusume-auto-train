# tools
import pyautogui
import time
import re
import core.state as state
import utils.constants as constants

from utils.log import info, warning, error, debug
from core.state import check_support_card, check_failure, check_skill_pts, get_race_type, get_event_name
from core.recognizer import is_btn_active
from core.skill import buy_skill
from core.events import get_optimal_choice

pyautogui.useImageNotFoundException(False)

training_types = {
  "spd": "assets/icons/train_spd.png",
  "sta": "assets/icons/train_sta.png",
  "pwr": "assets/icons/train_pwr.png",
  "guts": "assets/icons/train_guts.png",
  "wit": "assets/icons/train_wit.png"
}

def sleep(seconds=1):
  time.sleep(seconds * state.SLEEP_TIME_MULTIPLIER)

def get_secs(seconds=1):
  return seconds * state.SLEEP_TIME_MULTIPLIER

def drag_scroll(mousePos, to):
  '''to: negative to scroll down, positive to scroll up'''
  if not state.stop_event:
    return
  if not to or not mousePos:
    error("drag_scroll correct variables not supplied.")
  pyautogui.moveTo(mousePos, duration=0.1)
  pyautogui.mouseDown()
  pyautogui.moveRel(0, to, duration=0.25)
  pyautogui.mouseUp()
  pyautogui.click()

def click(img: str = None, confidence: float = 0.8, minSearch:float = 2, click: int = 1, text: str = "", boxes = None, region=None):
  if state.stop_event.is_set():
    return False
  if not state.is_bot_running:
    return False

  if boxes:
    if isinstance(boxes, list):
      if len(boxes) == 0:
        return False
      box = boxes[0]
    else :
      box = boxes

    if text:
      debug(text)
    x, y, w, h = box
    center = (x + w // 2, y + h // 2)
    pyautogui.moveTo(center[0], center[1], duration=0.225)
    pyautogui.click(clicks=click, interval=0.15)
    return True

  if img is None:
    return False

  if region:
    btn = pyautogui.locateCenterOnScreen(img, confidence=confidence, minSearchTime=minSearch, region=region)
  else:
    btn = pyautogui.locateCenterOnScreen(img, confidence=confidence, minSearchTime=minSearch)
  if btn:
    if text:
      debug(text)
    pyautogui.moveTo(btn, duration=0.225)
    pyautogui.click(clicks=click, interval=0.15)
    return True

  return False

def go_to_training():
  return click("assets/buttons/training_btn.png")

def check_training():
  if state.stop_event.is_set():
    return {}

  results = {}

  # failcheck enum "train","no_train","check_all"
  # failcheck="check_all"
  margin=5
  for key, icon_path in training_types.items():
    if state.stop_event.is_set():
      return {}

    pos = pyautogui.locateCenterOnScreen(icon_path, confidence=0.8, region=constants.SCREEN_BOTTOM_REGION)
    if pos:
      pyautogui.moveTo(pos, duration=0.1)
      pyautogui.mouseDown()
      support_card_results = check_support_card()

      #if key != "wit":
      #  if failcheck == "check_all":
      #    failure_chance = check_failure()
      #    if failure_chance > (state.MAX_FAILURE + margin):
      #      info("Failure rate too high skip to check wit")
      #      failcheck="no_train"
      #      failure_chance = state.MAX_FAILURE + margin
      #    elif failure_chance < (state.MAX_FAILURE - margin):
      #      info("Failure rate is low enough, skipping the rest of failure checks.")
      #      failcheck="train"
      #      failure_chance = 0
      #  elif failcheck == "no_train":
      #    failure_chance = state.MAX_FAILURE + margin
      #  elif failcheck == "train":
      #    failure_chance = 0
      #else:
      #  if failcheck == "train":
      #    failure_chance = 0
      #  else:
      failure_chance = check_failure()

      support_card_results["failure"] = failure_chance
      results[key] = support_card_results

      debug(f"[{key.upper()}] → Total Supports: {support_card_results['total_supports']}, Total Non-Maxed Supports: {support_card_results['total_non_maxed_support']}, Levels:{support_card_results['total_friendship_levels']}, Fail: {failure_chance}%, Hint: {support_card_results['total_hints']}")
      sleep(0.1)

  pyautogui.mouseUp()
  click(img="assets/buttons/back_btn.png")
  return results

def do_train(train):
  if state.stop_event.is_set():
    return
  train_btn = pyautogui.locateOnScreen(f"assets/icons/train_{train}.png", confidence=0.8, region=constants.SCREEN_BOTTOM_REGION)
  if train_btn:
    click(boxes=train_btn, click=3)

def do_rest(energy_level):
  if state.stop_event.is_set():
    return
  if not state.FORCE_REST:
    if state.NEVER_REST_ENERGY > 0 and energy_level > state.NEVER_REST_ENERGY:
      info(f"Wanted to rest when energy was above {state.NEVER_REST_ENERGY}, retrying from beginning.")
      return
  rest_btn = pyautogui.locateOnScreen("assets/buttons/rest_btn.png", confidence=0.8, region=constants.SCREEN_BOTTOM_REGION)
  rest_summber_btn = pyautogui.locateOnScreen("assets/buttons/rest_summer_btn.png", confidence=0.8, region=constants.SCREEN_BOTTOM_REGION)

  if rest_btn:
    click(boxes=rest_btn)
  elif rest_summber_btn:
    click(boxes=rest_summber_btn)

def do_recreation():
  if state.stop_event.is_set():
    return
  recreation_btn = pyautogui.locateOnScreen("assets/buttons/recreation_btn.png", confidence=0.8, region=constants.SCREEN_BOTTOM_REGION)
  recreation_summer_btn = pyautogui.locateOnScreen("assets/buttons/rest_summer_btn.png", confidence=0.8, region=constants.SCREEN_BOTTOM_REGION)

  if recreation_btn:
    click(boxes=recreation_btn)
    sleep(0.1)
    
    aoi_event = pyautogui.locateCenterOnScreen("assets/ui/aoi_event.png", confidence=0.8)
    tazuna_event = pyautogui.locateCenterOnScreen("assets/ui/tazuna_event.png", confidence=0.8)
    date_complete = pyautogui.locateCenterOnScreen("assets/ui/date_complete.png", confidence=0.8)

    if date_complete:
      pyautogui.moveTo(410, 500, duration=0.15)
      pyautogui.click()
    elif aoi_event:
      pyautogui.moveTo(aoi_event, duration=0.15)
      pyautogui.click(aoi_event)
    elif tazuna_event:
      pyautogui.moveTo(tazuna_event, duration=0.15)
      pyautogui.click(tazuna_event)

  elif recreation_summer_btn:
    click(boxes=recreation_summer_btn)

def do_race(prioritize_g1 = False, img = None):
  if state.stop_event.is_set():
    return False
  click(img="assets/buttons/races_btn.png", minSearch=get_secs(10))

  consecutive_cancel_btn = pyautogui.locateCenterOnScreen("assets/buttons/cancel_btn.png", minSearchTime=get_secs(0.7), confidence=0.8)
  if state.CANCEL_CONSECUTIVE_RACE and consecutive_cancel_btn:
    click(img="assets/buttons/cancel_btn.png", text="[INFO] Already raced 3+ times consecutively. Cancelling race and doing training.")
    return False
  elif not state.CANCEL_CONSECUTIVE_RACE and consecutive_cancel_btn:
    click(img="assets/buttons/ok_btn.png", minSearch=get_secs(0.7))

  sleep(0.7)
  found = race_select(prioritize_g1=prioritize_g1, img=img)
  if not found:
    if img is not None:
      info(f"{img} not found.")
    else:
      info("Race not found.")
    return False

  race_prep()
  sleep(1)
  after_race()
  return True

def race_day():
  if state.stop_event.is_set():
    return
  click(img="assets/buttons/race_day_btn.png", minSearch=get_secs(10), region=constants.SCREEN_BOTTOM_REGION)

  click(img="assets/buttons/ok_btn.png")
  sleep(0.5)

  #move mouse off the race button so that image can be matched
#  pyautogui.moveTo(x=400, y=400)

  for i in range(2):
    if state.stop_event.is_set():
      return
    if not click(img="assets/buttons/race_btn.png", minSearch=get_secs(2)):
      click(img="assets/buttons/bluestacks/race_btn.png", minSearch=get_secs(2))
    sleep(0.5)

  race_prep()
  sleep(1)
  after_race()

def race_select(prioritize_g1=False, img=None):
    if state.stop_event.is_set():
        return False
    pyautogui.moveTo(constants.SCROLLING_SELECTION_MOUSE_POS)
    sleep(0.3)

    if prioritize_g1 and img:
        info(f"Looking for {img}.")
        for _ in range(6):
            if state.stop_event.is_set():
                return False
            if click(img=f"assets/races_icon/{img}.png",
                     minSearch=get_secs(0.7),
                     text=f"{img} found.",
                     region=constants.RACE_LIST_BOX_REGION):
                for _ in range(2):
                    if not click(img="assets/buttons/race_btn.png", minSearch=get_secs(2)):
                        click(img="assets/buttons/bluestacks/race_btn.png", minSearch=get_secs(2))
                    sleep(0.5)
                return True
            drag_scroll(constants.RACE_SCROLL_BOTTOM_MOUSE_POS, -270)

        return False
    else:
        info("Looking for race.")
        for i in range(4):
          if state.stop_event.is_set():
            return False
          match_aptitude = pyautogui.locateOnScreen("assets/ui/match_track.png", confidence=0.8, minSearchTime=get_secs(0.7))

          if match_aptitude:
            # locked avg brightness = 163
            # unlocked avg brightness = 230
            if not is_btn_active(match_aptitude, treshold=200):
              info("Race found, but it's locked.")
              return False
            info("Race found.")
            click(boxes=match_aptitude)

            for i in range(2):
              if state.stop_event.is_set():
                return False
              if not click(img="assets/buttons/race_btn.png", minSearch=get_secs(2)):
                click(img="assets/buttons/bluestacks/race_btn.png", minSearch=get_secs(2))
              sleep(0.5)
            return True
          drag_scroll(constants.RACE_SCROLL_BOTTOM_MOUSE_POS, -270)

        return False

def race_prep():
  global PREFERRED_POSITION_SET

  if state.stop_event.is_set():
    return

  if state.POSITION_SELECTION_ENABLED:
    # these two are mutually exclusive, so we only use preferred position if positions by race is not enabled.
    if state.ENABLE_POSITIONS_BY_RACE:
      click(img="assets/buttons/info_btn.png", minSearch=get_secs(5), region=constants.SCREEN_TOP_REGION)
      sleep(0.5)
      #find race text, get part inside parentheses using regex, strip whitespaces and make it lowercase for our usage
      race_info_text = get_race_type()
      match_race_type = re.search(r"\(([^)]+)\)", race_info_text)
      race_type = match_race_type.group(1).strip().lower() if match_race_type else None
      click(img="assets/buttons/close_btn.png", minSearch=get_secs(2), region=constants.SCREEN_BOTTOM_REGION)

      if race_type != None:
        position_for_race = state.POSITIONS_BY_RACE[race_type]
        info(f"Selecting position {position_for_race} based on race type {race_type}")
        click(img="assets/buttons/change_btn.png", minSearch=get_secs(4), region=constants.SCREEN_MIDDLE_REGION)
        click(img=f"assets/buttons/positions/{position_for_race}_position_btn.png", minSearch=get_secs(2), region=constants.SCREEN_MIDDLE_REGION)
        click(img="assets/buttons/confirm_btn.png", minSearch=get_secs(2), region=constants.SCREEN_MIDDLE_REGION)
    elif not PREFERRED_POSITION_SET:
      click(img="assets/buttons/change_btn.png", minSearch=get_secs(6), region=constants.SCREEN_MIDDLE_REGION)
      click(img=f"assets/buttons/positions/{state.PREFERRED_POSITION}_position_btn.png", minSearch=get_secs(2), region=constants.SCREEN_MIDDLE_REGION)
      click(img="assets/buttons/confirm_btn.png", minSearch=get_secs(2), region=constants.SCREEN_MIDDLE_REGION)
      PREFERRED_POSITION_SET = True

  view_result_btn = pyautogui.locateCenterOnScreen("assets/buttons/view_results.png", confidence=0.8, minSearchTime=get_secs(10), region=constants.SCREEN_BOTTOM_REGION)
  click("assets/buttons/view_results.png", click=3)
  sleep(0.5)
  pyautogui.click()
  sleep(0.1)
  pyautogui.moveTo(constants.SCROLLING_SELECTION_MOUSE_POS)
  for i in range(2):
    if state.stop_event.is_set():
      return
    pyautogui.tripleClick(interval=0.2)
    sleep(0.5)
  pyautogui.click()
  next_button = pyautogui.locateCenterOnScreen("assets/buttons/next_btn.png", confidence=0.9, minSearchTime=get_secs(4), region=constants.SCREEN_BOTTOM_REGION)
  if not next_button:
    info(f"Wouldn't be able to move onto the after race since there's no next button.")
    if click("assets/buttons/race_btn.png", confidence=0.8, minSearch=get_secs(10), region=constants.SCREEN_BOTTOM_REGION):
      info(f"Went into the race, sleep for {get_secs(10)} seconds to allow loading.")
      sleep(10)
      if not click("assets/buttons/race_exclamation_btn.png", confidence=0.8, minSearch=get_secs(10)):
        info("Couldn't find \"Race!\" button, looking for alternative version.")
        click("assets/buttons/race_exclamation_btn_portrait.png", confidence=0.8, minSearch=get_secs(10))
      sleep(0.5)
      skip_btn = pyautogui.locateOnScreen("assets/buttons/skip_btn.png", confidence=0.8, minSearchTime=get_secs(2), region=constants.SCREEN_BOTTOM_REGION)
      skip_btn_big = pyautogui.locateOnScreen("assets/buttons/skip_btn_big.png", confidence=0.8, minSearchTime=get_secs(2), region=constants.SKIP_BTN_BIG_REGION_LANDSCAPE)
      if not skip_btn_big and not skip_btn:
        warning("Coulnd't find skip buttons at first search.")
        skip_btn = pyautogui.locateOnScreen("assets/buttons/skip_btn.png", confidence=0.8, minSearchTime=get_secs(10), region=constants.SCREEN_BOTTOM_REGION)
        skip_btn_big = pyautogui.locateOnScreen("assets/buttons/skip_btn_big.png", confidence=0.8, minSearchTime=get_secs(10), region=constants.SKIP_BTN_BIG_REGION_LANDSCAPE)
      if skip_btn:
        click(boxes=skip_btn, click=3)
      if skip_btn_big:
        click(boxes=skip_btn_big, click=3)
      sleep(3)
      if skip_btn:
        click(boxes=skip_btn, click=3)
      if skip_btn_big:
        click(boxes=skip_btn_big, click=3)
      sleep(0.5)
      if skip_btn:
        click(boxes=skip_btn, click=3)
      if skip_btn_big:
        click(boxes=skip_btn_big, click=3)
      sleep(3)
      skip_btn = pyautogui.locateOnScreen("assets/buttons/skip_btn.png", confidence=0.8, minSearchTime=get_secs(5), region=constants.SCREEN_BOTTOM_REGION)
      click(boxes=skip_btn, click=3)
      #since we didn't get the trophy before, if we get it we close the trophy
      close_btn = pyautogui.locateOnScreen("assets/buttons/close_btn.png", confidence=0.8, minSearchTime=get_secs(5))
      click(boxes=close_btn, click=3)
      info("Finished race skipping job.")

def after_race():
  if state.stop_event.is_set():
    return
  click(img="assets/buttons/next_btn.png", minSearch=get_secs(5))
  sleep(0.3)
  pyautogui.click()
  click(img="assets/buttons/next2_btn.png", minSearch=get_secs(5))

def auto_buy_skill():
  if state.stop_event.is_set():
    return
  if check_skill_pts() < state.SKILL_PTS_CHECK:
    return

  click(img="assets/buttons/skills_btn.png")
  info("Buying skills")
  sleep(0.5)

  if buy_skill():
    pyautogui.locateCenterOnScreen("assets/buttons/confirm_btn.png")
    click(img="assets/buttons/confirm_btn.png", minSearch=get_secs(1), region=constants.SCREEN_BOTTOM_REGION)
    sleep(0.5)
    click(img="assets/buttons/learn_btn.png", minSearch=get_secs(1), region=constants.SCREEN_BOTTOM_REGION)
    sleep(0.5)
    click(img="assets/buttons/close_btn.png", minSearch=get_secs(2), region=constants.SCREEN_MIDDLE_REGION)
    sleep(0.5)
    click(img="assets/buttons/back_btn.png")
  else:
    info("No matching skills found. Going back.")
    click(img="assets/buttons/back_btn.png")

def event_choice():
  event_choice_1 = pyautogui.locateCenterOnScreen("assets/icons/event_choice_1.png", confidence=0.8, minSearchTime=0.2)
  choice_vertical_gap = 112

  if not event_choice_1:
    return False

  if not state.USE_OPTIMAL_EVENT_CHOICES:
    click(boxes=event_choice_1, text="Event found, selecting top choice.")
    return True

  event_name = get_event_name()
  choice = get_optimal_choice(event_name)

  if choice == 0:
    click(boxes=event_choice_1, text="Event found, selecting top choice.")
    return True
    
  x = event_choice_1[0]
  y = event_choice_1[1] + ((choice - 1) * choice_vertical_gap)

  click(boxes=(x, y, 1, 1), text=f"Selecting optimal choice: {choice}")
  return True

def select_event():
  event_choices_icon = pyautogui.locateOnScreen("assets/icons/event_choice_1.png", confidence=0.9, minSearchTime=0.2, region=constants.GAME_SCREEN_REGION)
  choice_vertical_gap = 112

  if not event_choices_icon:
    return False

  if not state.USE_OPTIMAL_EVENT_CHOICE:
    click(boxes=event_choices_icon, text="Event found, selecting top choice.")
    return True

  event_name = get_event_name()

  chosen = event_choice(event_name)
  if chosen == 0:
    click(boxes=event_choices_icon, text="Event found, selecting top choice.")
    return True

  x = event_choices_icon[0]
  y = event_choices_icon[1] + ((chosen - 1) * choice_vertical_gap)
  debug(f"Event choices coordinates: {event_choices_icon}")
  debug(f"Clicking: {x}, {y}")
  click(boxes=(x, y, 1, 1), text=f"Selecting optimal choice: {event_name}")
  return True