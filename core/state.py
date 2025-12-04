from ast import Constant
from sqlite3 import PrepareProtocol
import cv2
import numpy as np
import re
import difflib
import json
import threading
from math import floor

from utils.log import info, warning, error, debug

from utils.screenshot import capture_region, enhanced_screenshot
from core.ocr import extract_text, extract_number, extract_text_improved, extract_percent
from core.recognizer import match_template, count_pixels_of_color, find_color_of_pixel, closest_color, multi_match_templates

import utils.constants as constants

stop_event = threading.Event()
is_bot_running = False
bot_thread = None
bot_lock = threading.Lock()

MINIMUM_MOOD = None
PRIORITIZE_G1_RACE = None
USE_OPTIMAL_EVENT_CHOICES = None
IS_AUTO_BUY_SKILL = None
SKILL_PTS_CHECK = None
PRIORITY_STAT = None
MAX_FAILURE = None
STAT_CAPS = None
SKILL_LIST = None
CANCEL_CONSECUTIVE_RACE = None
SLEEP_TIME_MULTIPLIER = 1
HINT_POINT = None
TRAINEE_NAME = None
CHOICE_WEIGHT = None
CURRENT_ENERGY_LEVEL=None
MAX_ENERGY = None
CURRENT_MOOD_INDEX = None
CURRENT_STATS = {}
CURRENT_YEAR = None
FORCE_REST = False
CURRENT_TURN_LEFT = None
PREFERRED_POSITION_SET = None
SCENARIO_NAME = ""
CRITERIA = None
DONE_DEBUT = None
FAN_COUNT = -1
TRAINING_RESTRICTED = None
LAST_VALID_STATS = None
VIRTUAL_TURN = None

TURN_REGION = (0,0,0,0)
YEAR_REGION = (0,0,0,0)
FAILURE_REGION = (0,0,0,0)
FAILURE_PERCENT_REGION = (0,0,0,0)

def load_config():
  with open("config.json", "r", encoding="utf-8") as file:
    return json.load(file)

def reload_config():
  global PRIORITY_STAT, PRIORITY_WEIGHT, MINIMUM_MOOD, MINIMUM_MOOD_JUNIOR_YEAR, MAX_FAILURE, MINIMUM_MOOD_WITH_FRIEND
  global PRIORITIZE_G1_RACE, CANCEL_CONSECUTIVE_RACE, STAT_CAPS
  global PRIORITY_EFFECTS_LIST, SKIP_TRAINING_ENERGY, NEVER_REST_ENERGY, SKIP_INFIRMARY_UNLESS_MISSING_ENERGY, SUMMER_PRIORITY_EFFECTS_LIST
  global POSITION_FOR_SPECIFIC_RACE, PREFERRED_POSITION
  global ENABLE_POSITIONS_BY_RACE, POSITIONS_BY_RACE, POSITION_SELECTION_ENABLED, SLEEP_TIME_MULTIPLIER, STOP_BEFORE_RACE
  global WINDOW_NAME, RACE_SCHEDULE, CONFIG_NAME
  global USE_OPTIMAL_EVENT_CHOICES, HINT_POINT, TRAINEE_NAME, CHOICE_WEIGHT, SCENARIO_NAME, JUNIOR_YEAR_STAT_PRIORITIZE, USE_PRIORITY_ON_CHOICE, EVENT_CHOICES
  global ENABLE_CUSTOM_FAILURE_CHANCE, ENABLE_CUSTOM_LOW_FAILURE, ENABLE_CUSTOM_HIGH_FAILURE, LOW_FAILURE_CONDITION, HIGH_FAILURE_CONDITION
  global IS_AUTO_BUY_SKILL, SKILL_PTS_CHECK, SKILL_LIST, DESIRE_SKILL
  global TURN_REGION, YEAR_REGION, FAILURE_REGION, FAILURE_PERCENT_REGION, TURN_NUMBER_REGION
  global UNITY_TEAM_PREFERENCE, UNITY_SPIRIT_BURST_POSITION

  config = load_config()

  PRIORITY_STAT = config["priority_stat"]
  PRIORITY_WEIGHT = config["priority_weight"]
  MINIMUM_MOOD = config["minimum_mood"]
  MINIMUM_MOOD_WITH_FRIEND = config["minimum_mood_with_friend"]
  MINIMUM_MOOD_JUNIOR_YEAR = config["minimum_mood_junior_year"]
  MAX_FAILURE = config["failure"]["maximum_failure"]
  PRIORITIZE_G1_RACE = config["prioritize_g1_race"]
  CANCEL_CONSECUTIVE_RACE = config["cancel_consecutive_race"]
  STAT_CAPS = config["stat_caps"]
  IS_AUTO_BUY_SKILL = config["skill"]["is_auto_buy_skill"]
  SKILL_PTS_CHECK = config["skill"]["skill_pts_check"]
  SKILL_LIST = config["skill"]["skill_list"]
  PRIORITY_EFFECTS_LIST = {i: v for i, v in enumerate(config["priority_weights"])}
  SKIP_TRAINING_ENERGY = config["skip_training_energy"]
  NEVER_REST_ENERGY = config["never_rest_energy"]
  SKIP_INFIRMARY_UNLESS_MISSING_ENERGY = config["skip_infirmary_unless_missing_energy"]
  PREFERRED_POSITION = config["preferred_position"]
  ENABLE_POSITIONS_BY_RACE = config["enable_positions_by_race"]
  POSITIONS_BY_RACE = config["positions_by_race"]
  POSITION_SELECTION_ENABLED = config["position_selection_enabled"]
  SLEEP_TIME_MULTIPLIER = config["sleep_time_multiplier"]
  WINDOW_NAME = config["window_name"]
  RACE_SCHEDULE = config["race_schedule"]
  CONFIG_NAME = config["config_name"]
  CHOICE_WEIGHT = config["choice_weight"]
  HINT_POINT = config["hint_point"]
  TRAINEE_NAME = config["trainee"]
  SCENARIO_NAME = config["scenario"]
  ENABLE_CUSTOM_FAILURE_CHANCE = config["failure"]["enable_custom_failure"]
  ENABLE_CUSTOM_LOW_FAILURE = config["failure"]["enable_custom_low_failure"]
  ENABLE_CUSTOM_HIGH_FAILURE = config["failure"]["enable_custom_high_failure"]
  LOW_FAILURE_CONDITION = config["failure"]["low_failure_condition"]
  HIGH_FAILURE_CONDITION = config["failure"]["high_failure_condition"]
  JUNIOR_YEAR_STAT_PRIORITIZE = config["use_prioritize_on_junior"]
  USE_PRIORITY_ON_CHOICE = config["use_priority_on_choice"]
  DESIRE_SKILL = config["skill"]["desire_skill"]
  USE_OPTIMAL_EVENT_CHOICES = config["event"]["use_optimal_event_choices"]
  EVENT_CHOICES = config["event"]["event_choices"]
  UNITY_TEAM_PREFERENCE = config["unity"]["prefer_team_race"]
  UNITY_SPIRIT_BURST_POSITION = config["unity"]["spirit_burst_position"]
  # STOP_BEFORE_RACE = config["stop_bot_before_race"]
  SUMMER_PRIORITY_EFFECTS_LIST = {i: v for i, v in enumerate(config["summer_priority_weights"])}
  POSITION_FOR_SPECIFIC_RACE = config["position_for_specific_race"]

  # URA Starter
  if "URA" in SCENARIO_NAME:
    TURN_REGION=(260, 81, 370 - 260, 140 - 81)
    TURN_NUMBER_REGION=(260, 81, 370 - 260, 135 - 81)
    YEAR_REGION=(255, 35, 420 - 255, 60 - 35)
    FAILURE_REGION=(250, 770, 855 - 295, 835 - 770)
    FAILURE_PERCENT_REGION=(250, 790, 855 - 295, 835 - 790)

    # Unity Starter
  if "Unity" in SCENARIO_NAME:
    TURN_REGION = (260, 55, 375 - 260, 110 - 55)
    TURN_NUMBER_REGION = (260, 55, 325 - 260, 110 - 55)
    YEAR_REGION =(385, 40, 565 - 385, 60 - 40)
    FAILURE_REGION=(250, 760, 855 - 250, 810 - 760)
    FAILURE_PERCENT_REGION=(250, 780, 855 - 250, 810 - 780)

# Get Stat
def stat_state():
  stat_regions = {
    "spd": constants.SPD_STAT_REGION,
    "sta": constants.STA_STAT_REGION,
    "pwr": constants.PWR_STAT_REGION,
    "guts": constants.GUTS_STAT_REGION,
    "wit": constants.WIT_STAT_REGION
  }

  result = {}
  for stat, region in stat_regions.items():
    img = enhanced_screenshot(region)
    val = extract_number(img)
    try:
        val_int = int(val)
    except (TypeError, ValueError):
        val_int = None

    cap = STAT_CAPS.get(stat, 1200)
    if val_int is not None and 0 <= val_int <= cap:
        result[stat] = val_int
        continue

    text = extract_text(img).lower()
    if "max" in text:
        result[stat] = cap
    else:
        result[stat] = -1
    result[stat] = val
  return result

def check_stats():
    """
    Wrapper for stat_state().
    If any stat is -1 (OCR failure), return LAST_VALID_STATS instead.
    Otherwise update LAST_VALID_STATS.
    """
    global LAST_VALID_STATS

    new_stats = stat_state()

    # OCR error: some stats are -1
    if any(v == -1 for v in new_stats.values()):
        warning(f"OCR stat error detected: {new_stats} -> using LAST_VALID_STATS")
        if LAST_VALID_STATS is not None:
            return LAST_VALID_STATS.copy()
        else:
            # No previous stats (first turn)
            return new_stats

    # Valid stats → update LAST_VALID_STATS
    LAST_VALID_STATS = new_stats.copy()
    return new_stats

# Check support card in each training
def check_support_card(threshold=0.8, target="none"):
  SUPPORT_ICONS = {
    "spd": "assets/icons/support_card_type_spd.png",
    "sta": "assets/icons/support_card_type_sta.png",
    "pwr": "assets/icons/support_card_type_pwr.png",
    "guts": "assets/icons/support_card_type_guts.png",
    "wit": "assets/icons/support_card_type_wit.png",
    "friend": "assets/icons/support_card_type_friend.png"
  }

  count_result = {}

  SUPPORT_FRIEND_LEVELS = {
    "gray": [110,108,120],
    "blue": [42,192,255],
    "green": [162,230,30],
    "yellow": [255,173,30],
    "max": [255,235,120],
  }

  count_result["total_supports"] = 0
  count_result["total_non_maxed_support"] = 0
  count_result["total_hints"] = 0
  count_result["total_friendship_levels"] = {}
  count_result["hints_per_friend_level"] = {}
  count_result["total_white_flame"] = 0
  count_result["total_blue_flame"] = 0

  for friend_level, color in SUPPORT_FRIEND_LEVELS.items():
    count_result["total_friendship_levels"][friend_level] = 0
    count_result["hints_per_friend_level"][friend_level] = 0

  hint_matches = match_template("assets/icons/support_hint.png", constants.SUPPORT_CARD_ICON_BBOX, threshold)
  white_flame_matches = match_template("assets/unity_cup/white_flame.png", constants.SUPPORT_CARD_ICON_BBOX, threshold)
  blue_flame_matches = match_template("assets/unity_cup/blue_flame.png", constants.SUPPORT_CARD_ICON_BBOX, threshold)

  def _dedup(rects, tol=10):
        uniq = []
        for (x,y,w,h) in sorted(rects or [], key=lambda r:(r[1], r[0])):
            if not uniq or abs(y - uniq[-1][1]) > tol or abs(x - uniq[-1][0]) > tol:
                uniq.append((x,y))
        return len(uniq)

  count_result["total_white_flame"] = _dedup(white_flame_matches)
  count_result["total_blue_flame"]  = _dedup(blue_flame_matches)

  for key, icon_path in SUPPORT_ICONS.items():
    count_result[key] = {}
    count_result[key]["supports"] = 0
    count_result[key]["hints"] = 0
    count_result[key]["friendship_levels"]={}

    for friend_level, color in SUPPORT_FRIEND_LEVELS.items():
      count_result[key]["friendship_levels"][friend_level] = 0

    matches = match_template(icon_path, constants.SUPPORT_CARD_ICON_BBOX, threshold)
    for match in matches:
      # add the support as a specific key
      count_result[key]["supports"] += 1
      # also add it to the grand total
      count_result["total_supports"] += 1

      #find friend colors and add them to their specific colors
      x, y, w, h = match
      match_horizontal_middle = floor((2*x+w)/2)
      match_vertical_middle = floor((2*y+h)/2)
      icon_to_friend_bar_distance = 66
      bbox_left = match_horizontal_middle + constants.SUPPORT_CARD_ICON_BBOX[0]
      bbox_top = match_vertical_middle + constants.SUPPORT_CARD_ICON_BBOX[1] + icon_to_friend_bar_distance
      wanted_pixel = (bbox_left, bbox_top, bbox_left+1, bbox_top+1)
      friendship_level_color = find_color_of_pixel(wanted_pixel)
      friend_level = closest_color(SUPPORT_FRIEND_LEVELS, friendship_level_color)
      count_result[key]["friendship_levels"][friend_level] += 1
      count_result["total_friendship_levels"][friend_level] += 1

      if hint_matches:
        for hint_match in hint_matches:
          distance = abs(hint_match[1] - match[1])
          if distance < 45:
            count_result["total_hints"] += 1
            count_result[key]["hints"] += 1
            count_result["hints_per_friend_level"][friend_level] +=1

  count_result["total_non_maxed_support"] = count_result["total_supports"] - (count_result["total_friendship_levels"]["yellow"] + count_result["total_friendship_levels"]["max"])

  return count_result

def _parse_failure_digits(raw: str) -> int | None:
    digits = re.sub(r"[^\d]", "", raw or "")
    if not digits:
        return None

    # --- Case A: 3-digit OCR cases like 399, 309 ---
    if len(digits) == 3:
        first_two = digits[:2]
        if first_two.isdigit():
            v = int(first_two)
            if 0 <= v <= 100:
                return v

    # --- Case B: 2-digit ambiguous cases like 39, 29, 19 ---
    if len(digits) == 2:
        # If OCR adds a trailing '9', real value is usually single digit (3% → 39)
        if digits[1] == "9":
            return int(digits[0])
        # no trailing 9 → treat normally (e.g., 30, 23)
        return int(digits)

    # --- Case C: 1-digit clean value ---
    if len(digits) == 1:
        return int(digits)

    # --- Case D: fallback for clean 0–100 ---
    if digits.isdigit():
        v = int(digits)
        if 0 <= v <= 100:
            return v

    return None

def check_failure():
    failure_text = enhanced_screenshot(FAILURE_REGION)
    failure_percent = enhanced_screenshot(FAILURE_PERCENT_REGION)

    label = extract_text(failure_text).lower()
    pct_text = extract_text(failure_percent)

    debug(f"raw_label: {label}")
    debug(f"raw_pct_text: {pct_text}")

    if not label.startswith("failure"):
        return -1

    # 1) read percent from the badge region only
    hits = list(re.finditer(r'(\d(?:\s?\d){0,2})\s*%', pct_text))
    if hits:
      v = int(hits[-1].group(1).replace(" ", ""))
      if 0 <= v <= 100:
        return v

    # 2) legacy fallbacks on the full label text
    m = re.search(r"failure\s+(\d{1,3})\s*%", label)
    if m:
      return int(m.group(1))

    m = re.search(r"failure\s+(\d+)", label)
    if m:
        v = _parse_failure_digits(m.group(1))
        if v is not None:
            return v

    return 99

# Check mood
def check_mood():
  mood = enhanced_screenshot(constants.MOOD_REGION)
  mood_text = extract_text(mood).upper()

  for known_mood in constants.MOOD_LIST:
    if known_mood in mood_text:
      return known_mood

  warning(f"Mood not recognized: {mood_text}")
  return "UNKNOWN"

# Check turn
def check_turn():
    turn = enhanced_screenshot(TURN_REGION)
    turn_text = extract_text(turn)

    turn_num = enhanced_screenshot(TURN_NUMBER_REGION)
    turn_num_ex = extract_number(turn_num)

    # debug(f"raw_turn_text: {turn_text}")
    # debug(f"raw_turn_num: {turn_num_ex}")

    if "race" in turn_text.lower():
        return "Race Day"
    if "goal" in turn_text.lower():
        return "Goal"

    turn_text = turn_text.replace("I", "1")
    # debug(f"clean_turn_text: {turn_text}")

    digits_only = re.sub(r"[^\d]", "", turn_text)

    if digits_only:
      if 0 < int(digits_only) < 50:
        return int(digits_only)

    if turn_num_ex:
        if 0 < int(turn_num_ex) < 50:
          return int(turn_num_ex)

    # if normal version fail use improved version
    turn_text = extract_text_improved(turn)
    if "race" in turn_text.lower():
        return "Race Day"
    if "goal" in turn_text.lower():
        return "Goal"

    turn_text = turn_text.replace("I", "1")
    # debug(f"clean_improved_turn_text: {turn_text}")

    digits_only = re.sub(r"[^\d]", "", turn_text)

    if digits_only:
      if 0 < int(digits_only) < 50:
        return int(digits_only)

    return -1

def _norm(s: str) -> str:
    # normalize OCR noise: collapse spaces, lowercase
    return re.sub(r"\s+", " ", s or "").strip().casefold()

def check_unity() -> str:
    """
    Returns the canonical round name ONLY if OCR text is in UNITY_ROUND_LIST.
    Otherwise returns "".
    """
    img = enhanced_screenshot(constants.UNITY_ROUND_REGION)
    raw = extract_text(img)

    # build normalized lookup of allowed rounds
    canon_by_norm = {_norm(x): x for x in constants.UNITY_ROUND_LIST}

    key = _norm(raw)
    if key in canon_by_norm:
        return canon_by_norm[key]

    # Optional: fuzzy rescue to handle small OCR errors
    # raise cutoff to be strict
    match = difflib.get_close_matches(key, canon_by_norm.keys(), n=1, cutoff=0.92)
    return canon_by_norm[match[0]] if match else None

# Check year
def check_current_year():
  year = enhanced_screenshot(YEAR_REGION)
  text = extract_text(year)
  return text

# Check criteria
def check_criteria():
  img = enhanced_screenshot(constants.CRITERIA_REGION)
  text = extract_text(img)
  return text

def check_criteria_detail():
  img = enhanced_screenshot(constants.CRITERIA_DETAIL_REGION)
  text = extract_text(img)
  return text

def check_debut_status():
  global DONE_DEBUT
  region = (440, 620, 430+1, 620+1)
  pixel = find_color_of_pixel(region)

  if isinstance(pixel, int):
    return False

  not_debut_color = (213,213,213)

  pixel = np.array(pixel)
  target = np.array(not_debut_color)

  is_match = np.all(np.abs(pixel - target) <= 5)
  if not is_match:
    debug("Already Finish Debut Race.")
    DONE_DEBUT = True
    return
    
  debug("Debut Race is Not Finish.")
  DONE_DEBUT = False
  return

def check_fans():
    global FAN_COUNT
    img = enhanced_screenshot(constants.FANS_REGION)
    text = extract_text(img)

    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^\d,]", "", text)
    text = text.replace(",", "")

    if text.isdigit():
        FAN_COUNT = int(text)
    else:
        FAN_COUNT = -1

    return FAN_COUNT

def check_fans_after_race(region):
    global FAN_COUNT
    img = enhanced_screenshot(region)
    text = extract_text(img)

    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^\d,]", "", text)
    text = text.replace(",", "")

    if text.isdigit():
        FAN_COUNT = int(text)
    else:
        FAN_COUNT = -1

    return FAN_COUNT

def check_skill_pts():
  img = enhanced_screenshot(constants.SKILL_PTS_REGION)
  text = extract_number(img)
  return text

previous_right_bar_match=""

def check_energy_level(threshold=0.85):
  # find where the right side of the bar is on screen
  global previous_right_bar_match
  right_bar_match = match_template("assets/ui/energy_bar_right_end_part.png", constants.ENERGY_BBOX, threshold)
  # longer energy bars get more round at the end
  if not right_bar_match:
    right_bar_match = match_template("assets/ui/energy_bar_right_end_part_2.png", constants.ENERGY_BBOX, threshold)

  if right_bar_match:
    x, y, w, h = right_bar_match[0]
    energy_bar_length = x

    x, y, w, h = constants.ENERGY_BBOX
    top_bottom_middle_pixel = round((y + h) / 2, 0)

    MAX_ENERGY_BBOX = (x, top_bottom_middle_pixel, x + energy_bar_length, top_bottom_middle_pixel+1)


    #[117,117,117] is gray for missing energy, region templating for this one is a problem, so we do this
    empty_energy_pixel_count = count_pixels_of_color([117,117,117], MAX_ENERGY_BBOX)

    #use the energy_bar_length (a few extra pixels from the outside are remaining so we subtract that)
    total_energy_length = energy_bar_length - 1
    hundred_energy_pixel_constant = 236 #counted pixels from one end of the bar to the other, should be fine since we're working in only 1080p

    previous_right_bar_match = right_bar_match

    energy_level = ((total_energy_length - empty_energy_pixel_count) / hundred_energy_pixel_constant) * 100
    info(f"Total energy bar length = {total_energy_length}, Empty energy pixel count = {empty_energy_pixel_count}, Diff = {(total_energy_length - empty_energy_pixel_count)}")
    info(f"Remaining energy guestimate = {energy_level:.2f}")
    max_energy = total_energy_length / hundred_energy_pixel_constant * 100
    return energy_level, max_energy
  else:
    warning(f"Couldn't find energy bar, returning -1")
    return -1, -1

def get_race_type():
  race_info_screen = enhanced_screenshot(constants.RACE_INFO_TEXT_REGION)
  race_info_text = extract_text(race_info_screen)
  debug(f"Race info text: {race_info_text}")
  return race_info_text

def get_race_name():
  race_name_screen = enhanced_screenshot(constants.RACE_NAME_TEXT_REGION)
  race_name_text = extract_text(race_name_screen)
  debug(f"Race name text: {race_name_text}")
  return race_name_text

# Severity -> 0 is doesn't matter / incurable, 1 is "can be ignored for a few turns", 2 is "must be cured immediately"
BAD_STATUS_EFFECTS={
  "Migraine":{
    "Severity":2,
    "Effect":"Mood cannot be increased",
  },
  "Night Owl":{
    "Severity":1,
    "Effect":"Character may lose energy, and possibly mood",
  },
  "Practice Poor":{
    "Severity":1,
    "Effect":"Increases chance of training failure by 2%",
  },
  "Skin Outbreak":{
    "Severity":1,
    "Effect":"Character's mood may decrease by one stage.",
  },
  "Slacker":{
    "Severity":2,
    "Effect":"Character may not show up for training.",
  },
  "Slow Metabolism":{
    "Severity":2,
    "Effect":"Character cannot gain Speed from speed training.",
  },
  "Under the Weather":{
    "Severity":0,
    "Effect":"Increases chance of training failure by 5%"
  },
}

GOOD_STATUS_EFFECTS={
  "Charming":"Raises Friendship Bond gain by 2",
  "Fast Learner":"Reduces the cost of skills by 10%",
  "Hot Topic":"Raises Friendship Bond gain for NPCs by 2",
  "Practice Perfect":"Lowers chance of training failure by 2%",
  "Shining Brightly":"Lowers chance of training failure by 5%"
}

def check_status_effects():
  status_effects_screen = enhanced_screenshot(constants.FULL_STATS_STATUS_REGION)

  screen = np.array(status_effects_screen)  # currently grayscale
  screen = cv2.cvtColor(screen, cv2.COLOR_GRAY2BGR)  # convert to 3-channel BGR for display

  #debug_window(screen)

  status_effects_text = extract_text(status_effects_screen)
  debug(f"Status effects text: {status_effects_text}")

  normalized_text = status_effects_text.lower().replace(" ", "")

  matches = [
      k for k in BAD_STATUS_EFFECTS
      if k.lower().replace(" ", "") in normalized_text
  ]

  total_severity = sum(BAD_STATUS_EFFECTS[k]["Severity"] for k in matches)

  debug(f"Matches: {matches}, severity: {total_severity}")
  return matches, total_severity

APTITUDES = {}

def check_aptitudes():
  global APTITUDES

  image = capture_region(constants.FULL_STATS_APTITUDE_REGION)
  image = np.array(image)
  h, w = image.shape[:2]

  # Ratios for each aptitude box (x, y, width, height) in percentages
  boxes = {
    "surface_turf":   (0.0, 0.00, 0.25, 0.33),
    "surface_dirt":   (0.25, 0.00, 0.25, 0.33),

    "distance_sprint": (0.0, 0.33, 0.25, 0.33),
    "distance_mile":   (0.25, 0.33, 0.25, 0.33),
    "distance_medium": (0.50, 0.33, 0.25, 0.33),
    "distance_long":   (0.75, 0.33, 0.25, 0.33),

    "style_front":  (0.0, 0.66, 0.25, 0.33),
    "style_pace":   (0.25, 0.66, 0.25, 0.33),
    "style_late":   (0.50, 0.66, 0.25, 0.33),
    "style_end":    (0.75, 0.66, 0.25, 0.33),
  }

  aptitude_images = {
    "s" : "assets/ui/aptitude_s.png",
    "a" : "assets/ui/aptitude_a.png",
    "b" : "assets/ui/aptitude_b.png",
    "c" : "assets/ui/aptitude_c.png",
    "d" : "assets/ui/aptitude_d.png",
    "e" : "assets/ui/aptitude_e.png",
    "f" : "assets/ui/aptitude_f.png",
    "g" : "assets/ui/aptitude_g.png"
  }

  crops = {}
  for key, (xr, yr, wr, hr) in boxes.items():
    x, y, ww, hh = int(xr*w), int(yr*h), int(wr*w), int(hr*h)
    cropped_image = np.array(image[y:y+hh, x:x+ww])
    matches = multi_match_templates(aptitude_images, cropped_image)
    for name, match in matches.items():
      if match:
        APTITUDES[key] = name
        #debug_window(cropped_image)

  info(f"Parsed aptitude values: {APTITUDES}. If these values are wrong, please stop and start the bot again with the hotkey.")

def debug_window(screen, x=-1400, y=-100):
  cv2.namedWindow("image")
  cv2.moveWindow("image", x, y)
  cv2.imshow("image", screen)
  cv2.waitKey(0)

# Get event name
def get_event_name():
  img = enhanced_screenshot(constants.EVENT_NAME_REGION)
  text = extract_text(img)
  return text

def stop_bot():
    global is_bot_running, bot_thread, stop_event
    info("[BOT] Stopping...")
    stop_event.set()
    is_bot_running = False

def _find_index_by_substring(text: str, candidates: list[str]) -> int:
    """
    Return index of first candidate whose lowercase substring
    appears in text (case-insensitive). Return -1 if not found.
    """
    if not text:
        return -1
    lower = text.lower()
    for i, c in enumerate(candidates):
        if c.lower() in lower:
            return i
    return -1

def get_virtual_turn(year_txt: str, criteria: str) -> int:
    """
    Map OCR year text to a virtual turn number:

    Pre-Debut  -> 0
    Junior/Classic/Senior (Jan–Dec, Early/Late) -> 1–72
    Finale -> 73

    Returns -1 if parsing fails.
    """
    year_parts = year_txt.split(" ")
    
    if not isinstance(year_txt, str):
        return -1
    if year_txt == "Junior Year Pre-Debut":
        return 0
    if len(year_parts) < 4:
        return -1

    if "Finale" in year_txt:
        if "Qualifier" in criteria:
            return 73
        if "Semifinal" in criteria:
            return 74
        if "Final" in criteria:
            return 75

    year = year_parts[0]
    month = year_parts[3]
    phase = year_parts[2]

    year_idx = _find_index_by_substring(year, constants.YEAR_ORDER)
    month_idx = _find_index_by_substring(month, constants.MONTH_ORDER)
    phase_idx = _find_index_by_substring(phase, constants.PHASE_ORDER)

    if phase_idx == -1:
        if "Early" in phase:
            phase_idx = 0
        elif "Late" in phase:
            phase_idx = 1

    if year_idx == -1 or month_idx == -1 or phase_idx == -1:
        warning(f"Failed to parse virtual turn from year_text='{year_txt}'")
        return -1

    index_0 = year_idx * 24 + month_idx * 2 + phase_idx + 1
    debug(f"{index_0} = {year_idx} * 24 + {month_idx} * 2 + {phase_idx} + 1")
    return index_0