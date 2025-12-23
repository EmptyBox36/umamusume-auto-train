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

    # keywords and racecourses (all lowercase for comparisons)

    specific_keywords = [
        "tokyo",
        "nakayama",
        "hanshin",
        "kyoto",
        "chukyo",
        "sapporo",
        "hakodate",
        "fukushima",
        "niigata",
        "kokura",
        "oi",
        "sprint",
        "mile",
        "medium",
        "long",
        "short",
        "turf",
        "dirt",
        "front",
        "pace",
        "late",
        "end",
        "ignited spirit",
        "burning spirit",
    ]

    text_lower = (text or "").lower().strip()
    text_words = set(text_lower.split())

    # fast path: empty text
    if not text_lower:
        return False

    # determine if text contains any keyword
    text_keywords = {k for k in specific_keywords if k in text_lower}

    for skill in skill_list:
        skill_lower = (skill or "").lower().strip()
        if not skill_lower:
            continue

        similarity = Levenshtein.ratio(text_lower, skill_lower)

        skill_keywords = {k for k in specific_keywords if k in skill_lower}

        # If either side contains any specific keyword, require a strict match
        if text_keywords or skill_keywords:
            if similarity >= 0.93:
                debug(f"Keyword-strict match: '{text}' ~ '{skill}' ({similarity:.2f})")
                return True
            continue

        # fallback: general string similarity or strong word overlap
        common_words = text_words & set(skill_lower.split())
        word_overlap = (
            len(common_words) / max(len(text_words), len(skill_lower.split()))
            if max(len(text_words), len(skill_lower.split())) > 0
            else 0
        )

        if similarity >= threshold:
            debug(
                f"General skill match (string): '{text}' ~ '{skill}' ({similarity:.2f})"
            )
            return True

        if word_overlap >= 0.85 and len(common_words) >= 3:
            debug(
                f"General skill match (word reorder): '{text}' ~ '{skill}' (overlap: {word_overlap:.2f})"
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
    
    normalized_name = skill_name.strip()
    selected_skill_names = {s["name"].strip() for s in ctx["skills"]}

    if ctx["mode"] == "collect":
        # Normalize name and avoid duplicates in collect mode
        if normalized_name in selected_skill_names:
            return False
        else:
            ctx["skills"].append({"name": normalized_name, "discount": discount, "cost": cost})
            info(f"Collected {normalized_name} (discount: {discount}%, cost: {cost})")

    elif ctx["mode"] == "buy":
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

    click(img="assets/buttons/back_btn.png")
    sleep(0.5)

    if not collect_ctx["skills"]:
        info("No matching skills found. Exiting early.")
        return False
    
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
