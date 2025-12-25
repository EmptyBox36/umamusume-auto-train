import json

MOOD_REGION = (705, 125, 835 - 705, 150 - 125)
CRITERIA_REGION = (455, 55, 765 - 455, 115 - 55)
SKILL_PTS_REGION = (760, 780, 825 - 760, 815 - 780)
SKIP_BTN_BIG_REGION_LANDSCAPE = (1500, 750, 1920 - 1500, 1080 - 750)
SCREEN_BOTTOM_REGION = (125, 800, 1000 - 125, 1080 - 800)
SCREEN_MIDDLE_REGION = (125, 300, 1000 - 125, 800 - 300)
SCREEN_TOP_REGION = (125, 0, 1000 - 125, 300)
RACE_INFO_TEXT_REGION = (285, 335, 810 - 285, 370 - 335)
RACE_NAME_TEXT_REGION = (350, 25, 780 - 350, 55 - 25)
RACE_LIST_BOX_REGION = (260, 580, 850 - 265, 870 - 580)

AFTER_RACE_FANS_REGION = (410, 535, 800 - 410, 575 - 535)
FANS_REGION = (540, 680, 830 - 540, 715 - 680)
FANS_LABEL_REGION = (260, 530, 830 - 260, 580 - 530)

FULL_STATS_STATUS_REGION = (265, 575, 845 - 265, 940 - 575)
FULL_STATS_APTITUDE_REGION = (395, 340, 820 - 395, 440 - 340)

SPD_STAT_REGION = (310, 723, 55, 20)
STA_STAT_REGION = (405, 723, 55, 20)
PWR_STAT_REGION = (500, 723, 55, 20)
GUTS_STAT_REGION = (595, 723, 55, 20)
WIT_STAT_REGION = (690, 723, 55, 20)
SPD_GAIN_STAT_REGION = (275, 670, 90, 30)
STA_GAIN_STAT_REGION = (370, 670, 90, 30)
PWR_GAIN_STAT_REGION = (465, 670, 90, 30)
GUTS_GAIN_STAT_REGION = (560, 670, 90, 30)
WIT_GAIN_STAT_REGION = (655, 670, 90, 30)
SPD_BONUS_STAT_REGION = (295, 644, 55, 24)
STA_BONUS_STAT_REGION = (390, 644, 55, 24)
PWR_BONUS_STAT_REGION = (485, 644, 55, 24)
GUTS_BONUS_STAT_REGION = (580, 644, 55, 24)
WIT_BONUS_STAT_REGION = (675, 644, 55, 24)

SPD_RACE_STAT_REGION = (308, 775, 55, 25)
STA_RACE_STAT_REGION = (404, 775, 55, 25)
PWR_RACE_STAT_REGION = (500, 775, 55, 25)
GUTS_RACE_STAT_REGION = (596, 775, 55, 25)
WIT_RACE_STAT_REGION = (692, 775, 55, 25)

CAREER_COMPLETE_SP_REGION = (445, 908, 50, 20)

SCROLLING_SELECTION_MOUSE_POS = (560, 680)
SKILL_SCROLL_BOTTOM_MOUSE_POS = (560, 850)
RACE_SCROLL_BOTTOM_MOUSE_POS = (560, 850)
RACE_SCROLL_TOP_MOUSE_POS = (560, 580)

EVENT_NAME_REGION = (241, 205, 365, 30)

MOOD_LIST = ["AWFUL", "BAD", "NORMAL", "GOOD", "GREAT", "UNKNOWN"]

SUPPORT_CARD_ICON_BBOX = (845, 130, 945, 700)
ENERGY_BBOX = (440, 120, 800, 160)
RACE_BUTTON_IN_RACE_BBOX_LANDSCAPE = (800, 950, 1150, 1050)
GAME_SCREEN = (150, 0, 960, 1080)

UNITY_ROUND_REGION = (450, 290, 660 - 450, 330 - 290)
UNITY_ROUND_LIST = [
    "Preseason Round 1",
    "Preseason Round 2",
    "Preseason Round 3",
    "Preseason Round 4",
    "Finals",
]

YEAR_ORDER = ["Junior", "Classic", "Senior"]
MONTH_ORDER = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
PHASE_ORDER = ["Early", "Late"]


OFFSET_APPLIED = False


def adjust_constants_x_coords(offset=405):
    """Shift all region tuples' x-coordinates by `offset`."""

    global OFFSET_APPLIED
    if OFFSET_APPLIED:
        return

    g = globals()
    for name, value in list(g.items()):
        if (
            name.endswith("_REGION")  # only touch REGION constants
            and isinstance(value, tuple)
            and len(value) >= 2
        ):
            # Adjust only the x-coordinates (0 and 2)
            new_value = (
                value[0] + offset,
                value[1],
                value[2],
                value[3],
            )
            # Drop None if length was originally 3
            g[name] = tuple(x for x in new_value if x is not None)

        if (
            name.endswith("_MOUSE_POS")  # only touch REGION constants
            and isinstance(value, tuple)
            and len(value) >= 2
        ):
            # Adjust only the x-coordinates (0 and 2)
            new_value = (
                value[0] + offset,
                value[1],
            )
            # Drop None if length was originally 3
            g[name] = tuple(x for x in new_value if x is not None)

        if (
            name.endswith("_BBOX")  # only touch REGION constants
            and isinstance(value, tuple)
            and len(value) >= 2
        ):
            # Adjust only the x-coordinates (0 and 2)
            new_value = (
                value[0] + offset,
                value[1],
                value[2] + offset,
                value[3],
            )
            # Drop None if length was originally 3
            g[name] = tuple(x for x in new_value if x is not None)
    OFFSET_APPLIED = True


# Load all races once to be used when selecting them
RACES = ""
with open("scraper/data/races.json", "r", encoding="utf-8") as file:
    RACES = json.load(file)

# Build a lookup dict for fast (year, date) searches
RACE_LOOKUP = {}
for year, races in RACES.items():
    for name, data in races.items():
        key = f"{year} {data['date']}"
        race_entry = {"name": name, **data}
        RACE_LOOKUP.setdefault(key, []).append(race_entry)
