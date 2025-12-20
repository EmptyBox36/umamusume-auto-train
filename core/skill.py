import core.state as state
import Levenshtein
import numpy as np
import pyautogui
import utils.constants as constants
from core.ocr import extract_text
from core.recognizer import is_btn_active, match_template
from utils.log import debug, info
from utils.screenshot import enhanced_screenshot
from utils.tools import click, drag_scroll, sleep


def is_skill_match(
    text: str, skill_list: list[str] | None, threshold: float = 0.8
) -> bool:
    """
    Match a skill from OCR text against the skill list.

    If skill_list is None or empty, ALL SKILLS MATCH.
    """

    # ✅ Match everything if no skill list is provided
    if not skill_list:
        return True

    racecourses = [
        "Tokyo",
        "Nakayama",
        "Hanshin",
        "Kyoto",
        "Chukyo",
        "Sapporo",
        "Hakodate",
        "Fukushima",
        "Niigata",
        "Kokura",
        "Oi",
    ]

    specific_keywords = racecourses + [
        "Sprint",
        "Mile",
        "Medium",
        "Long",
        "Short",
        "Turf",
        "Dirt",
        "Front",
        "Pace",
        "Late",
        "End",
    ]

    text_lower = text.lower()
    text_words = set(text_lower.split())

    text_specific_keyword = None
    for keyword in specific_keywords:
        if keyword.lower() in text_lower:
            text_specific_keyword = keyword
            break

    for skill in skill_list:
        skill_lower = skill.lower()
        skill_words = set(skill_lower.split())

        skill_specific_keyword = None
        for keyword in specific_keywords:
            if keyword.lower() in skill_lower:
                skill_specific_keyword = keyword
                break

        similarity = Levenshtein.ratio(text_lower, skill_lower)

        common_words = text_words & skill_words
        word_overlap = (
            len(common_words) / max(len(text_words), len(skill_words))
            if max(len(text_words), len(skill_words)) > 0
            else 0
        )

        if text_specific_keyword and skill_specific_keyword:
            if (
                text_specific_keyword.lower() == skill_specific_keyword.lower()
                and similarity >= 0.9
            ):
                debug(f"Specific skill match: '{text}' ~ '{skill}' ({similarity:.2f})")
                return True

        elif skill_specific_keyword and not text_specific_keyword:
            if similarity >= 0.9:
                debug(f"Specific skill match: '{text}' ~ '{skill}' ({similarity:.2f})")
                return True

        elif text_specific_keyword and not skill_specific_keyword:
            continue

        else:
            if similarity >= threshold:
                debug(
                    f"General skill match (string): '{text}' ~ '{skill}' ({similarity:.2f})"
                )
                return True
            elif word_overlap >= 0.85 and len(common_words) >= 3:
                debug(
                    f"General skill match (word reorder): "
                    f"'{text}' ~ '{skill}' (overlap: {word_overlap:.2f})"
                )
                return True

    debug(f"No match for '{text}'")
    return False


def list_unchanged(curr_img, prev_img, same_count):
    if prev_img is None:
        return False, curr_img, 0

    if np.array_equal(curr_img, prev_img):
        same_count += 1
    else:
        same_count = 0

    if same_count >= 3:
        info("Skill list unchanged for 3 loops. Exiting early.")
        return True, curr_img, same_count

    return False, curr_img, same_count


def scroll_loop(iterations=20):
    for i in range(iterations):
        if state.stop_event.is_set():
            return
        if i > 10:
            sleep(0.5)
        yield i


def scan_skills(context, skill_list=None):
    """
    Scan skills on the skill screen.

    skill_list:
      - None → ALL SKILLS MATCH
      - list[str] → filtered matching
    """
    pyautogui.moveTo(constants.SCROLLING_SELECTION_MOUSE_POS)

    context["prev_img"] = None
    context["same_count"] = 0
    context["skill_list"] = skill_list

    for _ in scroll_loop():
        buy_skill_icon = match_template("assets/icons/buy_skill.png", threshold=0.9)

        if buy_skill_icon:
            for x, y, w, h in buy_skill_icon:
                unchanged = on_skill(x, y, w, h, context)
                if unchanged:
                    return

        drag_scroll(constants.SKILL_SCROLL_BOTTOM_MOUSE_POS, -450)


def on_skill(x, y, w, h, ctx):
    """
    ctx keys:
      mode: "collect" | "buy"
      skills: list
      MAX_COST
      MIN_DISCOUNT
      prev_img
      same_count
      skill_list
    """

    name_region = (x - 420, y - 40, w + 275, h + 5)
    discount_region = (x - 80, y - 30, w - 3, h - 8)
    cost_region = (x - 70, y - 3, w + 33, h + 10)

    name_img = enhanced_screenshot(name_region)

    unchanged, ctx["prev_img"], ctx["same_count"] = list_unchanged(
        np.array(name_img), ctx["prev_img"], ctx["same_count"]
    )
    if unchanged:
        return True

    skill_name = extract_text(name_img)

    skill_list = ctx.get("skill_list", state.SKILL_LIST)

    if not is_skill_match(skill_name, skill_list):
        return False

    discount_text = extract_text(enhanced_screenshot(discount_region)) or "0"

    cost_text = extract_text(enhanced_screenshot(cost_region))

    try:
        discount = int(discount_text)
        cost = int(cost_text)
    except ValueError:
        return False

    if discount < ctx["MIN_DISCOUNT"] or cost > ctx["MAX_COST"]:
        return False

    if ctx["mode"] == "collect":
        ctx["skills"].append({"name": skill_name, "discount": discount, "cost": cost})

    elif ctx["mode"] == "buy":
        selected_skill_names = {s["name"] for s in ctx["skills"]}

        # normalize name to reduce OCR variance
        normalized_name = skill_name.strip()

        if normalized_name in selected_skill_names:
            if is_btn_active((x, y, w, h)):
                info(f"Buy {normalized_name}")
                pyautogui.doubleClick(x=x + 5, y=y + 5, duration=0.15, interval=0.5)

                state.PURCHASED_SKILLS.append(normalized_name)
                ctx["found"] = True
            else:
                info(f"{normalized_name} found but not enough skill points.")

    return False


def buy_skill(MAX_COST=240, MIN_DISCOUNT=30):

    collect_ctx = {
        "mode": "collect",
        "skills": [],
        "MAX_COST": MAX_COST,
        "MIN_DISCOUNT": MIN_DISCOUNT,
        "found": False,
    }

    scan_skills(collect_ctx, skill_list=state.SKILL_LIST)

    if not collect_ctx["skills"]:
        info("No matching skills found. Exiting early.")
        return False

    click(img="assets/buttons/back_btn.png")
    sleep(0.5)
    click(img="assets/buttons/skills_btn.png")
    sleep(0.5)

    buy_ctx = {
        "mode": "buy",
        "skills": collect_ctx["skills"],
        "MAX_COST": MAX_COST,
        "MIN_DISCOUNT": MIN_DISCOUNT,
        "found": False,
    }

    scan_skills(buy_ctx, skill_list=state.SKILL_LIST)
    return buy_ctx["found"]