from utils.tools import sleep, drag_scroll
import pyautogui
import Levenshtein
import numpy as np

import utils.constants as constants

from utils.log import info, warning, error, debug
from utils.screenshot import enhanced_screenshot
from core.ocr import extract_text
from core.recognizer import match_template, is_btn_active
import core.state as state

def buy_skill():
  pyautogui.moveTo(constants.SCROLLING_SELECTION_MOUSE_POS)
  found = False
  prev_img = None
  same_count = 0

  for i in range(15):
    if state.stop_event.is_set():
      return
    if i > 10:
      sleep(0.5)
    buy_skill_icon = match_template("assets/icons/buy_skill.png", threshold=0.9)

    if buy_skill_icon:
      for x, y, w, h in buy_skill_icon:
        region = (x - 420, y - 40, w + 275, h + 5)
        screenshot = enhanced_screenshot(region)

        curr_img = np.array(screenshot)
        if prev_img is not None:
          if np.array_equal(curr_img, prev_img):
            same_count += 1
          else:
            same_count = 0

          if same_count >= 3:
            info("Skill list unchanged for 3 loops. Exiting early.")
            return found
        prev_img = curr_img

        text = extract_text(screenshot)
        if is_skill_match(text, state.SKILL_LIST):
          button_region = (x, y, w, h)
          if is_btn_active(button_region):
            info(f"Buy {text}")
            pyautogui.click(x=x + 5, y=y + 5, duration=0.15)
            found = True
          else:
            info(f"{text} found but not enough skill points.")

    drag_scroll(constants.SKILL_SCROLL_BOTTOM_MOUSE_POS, -450)

  return found

def is_skill_match(text: str, skill_list: list[str], threshold: float = 0.8) -> bool:
  for skill in skill_list:
    similarity = Levenshtein.ratio(text.lower(), skill.lower())
    if similarity >= threshold:
      return True
  return False