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
    text: str, skill_list: list[str] | list[dict] | None, threshold: float = 0.85
) -> tuple[bool, str | None]:
    """
    Match a skill from OCR text against the skill list.

    Returns `(matched: bool, canonical_name: Optional[str])`.

    If `skill_list` is None or empty, all skills match and canonical_name is None.
    Supports both formats: list[str] and list[dict] (with 'name' key).
    """

    # ✅ Match everything if no skill list is provided
    if not skill_list:
        return True, None

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
        return False, None

    # determine if text contains any keyword
    text_keywords = {k for k in specific_keywords if k in text_lower}

    best_match = None
    best_score = 0.0

    for skill in skill_list:
        # Handle both string and dict formats
        if isinstance(skill, dict):
            skill_name = skill.get("name", "")
        else:
            skill_name = skill or ""
        
        skill_lower = (skill_name or "").lower().strip()
        if not skill_lower:
            continue

        similarity = Levenshtein.ratio(text_lower, skill_lower)

        skill_keywords = {k for k in specific_keywords if k in skill_lower}

        # If either side contains any specific keyword, prefer strict similarity
        if text_keywords or skill_keywords:
            if similarity >= 0.93 and similarity > best_score:
                best_score = similarity
                best_match = skill
            continue

        # fallback: general string similarity or strong word overlap
        common_words = text_words & set(skill_lower.split())
        word_overlap = (
            len(common_words) / max(len(text_words), len(skill_lower.split()))
            if max(len(text_words), len(skill_lower.split())) > 0
            else 0
        )

        if similarity >= threshold and similarity > best_score:
            best_score = similarity
            best_match = skill

        if word_overlap >= 0.85 and len(common_words) >= 3 and similarity > best_score:
            best_score = similarity
            best_match = skill

    if best_match:
        # Extract the name from dict or use string directly
        matched_name = best_match.get("name") if isinstance(best_match, dict) else best_match
        debug(f"Matched '{text}' -> '{matched_name}' ({best_score:.2f})")
        return True, matched_name

    debug(f"No match for '{text}'")
    return False, None





def list_unchanged(curr_skills, prev_skills, same_count):
    """
    Compare lists of detected skill names across iterations.
    Returns (is_unchanged: bool, same_count: int)
    """
    if prev_skills is None:
        return False, 0

    if curr_skills == prev_skills:
        same_count += 1
    else:
        same_count = 0

    if same_count >= 3:
        info("Skill list unchanged for 3 loops. Exiting early.")
        return True, same_count

    return False, same_count


def scroll_loop(iterations=20):
    for i in range(iterations):
        if state.stop_event.is_set():
            return
        # UI stabilization sleep
        sleep(0.1)
        yield i


def scan_skills(context):
    """
    Scan skills on the skill screen.
    """
    pyautogui.moveTo(constants.SCROLLING_SELECTION_MOUSE_POS)

    context["same_count"] = 0
    context["prev_skills"] = None

    for _ in scroll_loop():
        # Reset detected skills list for this iteration
        context["curr_skills"] = []
        
        buy_skill_icon = match_template("assets/icons/buy_skill.png", threshold=0.9)

        if buy_skill_icon:
            for x, y, w, h in buy_skill_icon:
                # on_skill may return True to signal stopping (all bought)
                stop = on_skill(x, y, w, h, context)
                if stop:
                    return

        # Check if the list of detected skills is unchanged
        unchanged, context["same_count"] = list_unchanged(
            context["curr_skills"],
            context["prev_skills"],
            context["same_count"]
        )
        if unchanged:
            return

        context["prev_skills"] = list(context["curr_skills"])
        drag_scroll(constants.SKILL_SCROLL_BOTTOM_MOUSE_POS, -450)


def on_skill(x, y, w, h, ctx):
    """
    ctx keys:
      mode: "collect" | "buy"
      collected_skills: list (populated in collect mode)
      skills_to_buy: list (populated in buy mode)
      max_cost: int
      min_discount: int
      found: bool - set to True if any skill bought
      curr_skills: list - skills detected in current iteration
      bought_names: set - skills bought so far
      prev_skills: list or None 
      same_count: int - count of unchanged iterations
      "collect_all_skills": bool (optional) - if set, collect all skills regardless of skill list
    """

    name_region = (x - 420, y - 40, w + 275, h + 5)
    discount_region = (x - 80, y - 30, w - 3, h - 8)
    cost_region = (x - 70, y - 3, w + 33, h + 10)

    name_img = enhanced_screenshot(name_region)

    skill_name = extract_text(name_img)
    
    # Track this skill as detected in the current iteration
    ctx.setdefault("curr_skills", []).append(skill_name)

    # find canonical skill name from OCR against known skill list
    matched, matched_skill = is_skill_match(skill_name, ctx.get("skills_to_buy") or list(state.SKILL_LIST))
    
    # If collect_all_skills flag is set, bypass matching and collect everything
    if ctx.get("collect_all_skills"):
        matched = True
        matched_skill = skill_name
    
    if not matched:
        return False

    discount_text = extract_text(enhanced_screenshot(discount_region)) or "0"

    cost_text = extract_text(enhanced_screenshot(cost_region))

    try:
        discount = int(discount_text.strip()[:2])
        cost = int(cost_text)
        debug(f"Skill '{skill_name}' costs {cost} SP with {discount}% discount")
    except ValueError:
        return False

    if discount < ctx["min_discount"] or cost > ctx["max_cost"]:
        debug(f"Skill '{skill_name}' skipped due to cost/discount (cost: {cost}, discount: {discount}%)")
        return False
    
    # prefer canonical matched name when available
    canonical_name = (matched_skill).strip()

    if ctx["mode"] == "collect":
        # Collect skills from the game, storing them for later purchase phase
        ctx.setdefault("collected_skills", []).append({"name": canonical_name, "discount": discount, "cost": cost})
        info(f"Collected {canonical_name} (discount: {discount}%, cost: {cost})")

    elif ctx["mode"] == "buy":

        # Build target skill names from skills_to_buy (only for buy mode)
        # Supports both shapes: list[dict] (from collected_skills) or list[str]
        target_skills = set()
        for s in ctx.get("skills_to_buy", []):
            if isinstance(s, dict):
                name = s.get("name", "")
            else:
                name = s or ""
            if name:
                target_skills.add(name.strip())
            # Buy skills that are in our target list

        if canonical_name in target_skills:
            if is_btn_active((x, y, w, h)):
                info(f"Buy {canonical_name}")
                pyautogui.doubleClick(x=x + 5, y=y + 5, duration=0.15, interval=0.5)

                # store canonical name in global purchased list
                state.PURCHASED_SKILLS.append(canonical_name)
                ctx["found"] = True
                # record this purchase in the buy context
                ctx.setdefault("bought_names", set()).add(canonical_name)

                # if we've purchased all target skills, stop scanning
                if target_skills and ctx["bought_names"] >= target_skills:
                    info("All requested skills purchased. Exiting scan.")
                    return True
            else:
                info(f"{canonical_name} found but not enough skill points.")

    return False


def buy_skill(MAX_COST=240, MIN_DISCOUNT=30):
    buy_ctx = {
        "mode": "buy",
        "skills_to_buy": state.SKILL_LIST,
        "max_cost": MAX_COST,
        "min_discount": MIN_DISCOUNT,
        "found": False,
    }

    scan_skills(buy_ctx)
    return buy_ctx["found"]
