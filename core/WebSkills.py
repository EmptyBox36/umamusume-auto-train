# WebSkills.py
import time
import json
import math
from pathlib import Path

import core.state as state
from core.ocr import extract_text
from core.skill import is_skill_match, scan_skills
from playwright.sync_api import sync_playwright
from utils.constants import CAREER_COMPLETE_SP_REGION
from utils.log import debug, error, info, warning
from utils.screenshot import enhanced_screenshot
from utils.tools import click, sleep

# =========================
# CONFIG
# =========================

RUNNING_STYLE_MAP = {
    "front": "Front Runner",
    "late": "Late Surger",
    "pace": "Pace Chaser",
    "end": "End Closer",
}

UMALATOR_URL = "https://alpha123.github.io/uma-tools/umalator-global/"


# =========================
# UTILS
# =========================


# ------------------------
# Inject purchased skills dynamically
# ------------------------
def inject_purchased_skills(page):
    """
    Dynamically open the skill picker and select each skill in state.PURCHASED_SKILLS
    after chart mode is selected.
    """

    for skill_name in state.PURCHASED_SKILLS:
        if is_excluded_uma_skill(skill_name):
            debug(f"Skipping blacklisted skill: {skill_name}")
            continue

        success = click_skill(page, skill_name)
        if success:
            info(f"Selected purchased skill: {skill_name}")
        else:
            warning(f"Purchased skill not available in simulator: {skill_name}")

def click_skill(page, skill_name: str):
    """
    Open picker, wait for skill to appear, then click the skill.
    Returns True if skill was successfully clicked.
    """

    add_skill_btn = page.query_selector("div.skill.addSkillButton")
    if not add_skill_btn:
        warning("'Add Skill' button not found!")
        return False
    # Determine if the picker is already open
    picker_open = page.query_selector(".horseSkillPickerWrapper.open")

    if not picker_open:
        # Open picker (but only if it's not already open)
        try:
            add_skill_btn.click()
            # Wait for the picker to appear
            try:
                page.wait_for_selector(
                    ".horseSkillPickerWrapper.open", timeout=5000
                )
            except Exception:
                # Fallback to any wrapper
                page.wait_for_selector(".horseSkillPickerWrapper", timeout=2000)
        except Exception:
            # If click failed but picker is open now, continue; otherwise error
            if not page.query_selector(".horseSkillPickerWrapper.open"):
                warning("Failed to open skill picker")
                return False

    time.sleep(0.2)  # UI register time

    try:
        picker_wrapper = page.query_selector(".horseSkillPickerWrapper")
        # Wait for specific skill to appear inside the picker
        skill_elem = picker_wrapper.wait_for_selector(
            f'.skill:has(.skillName:text("{skill_name}"))', timeout=3000
        )
        skill_elem.click()
        time.sleep(0.2)  # UI register time

        # After selecting, wait for the picker to close if it does
        page.wait_for_selector(
            ".horseSkillPickerWrapper.open", state="detached", timeout=3000
        )

        found = True
        return found
    except Exception:
        # If skill not found, try to close picker and return False
        warning(f"Skill not found in picker: {skill_name}")
        page.mouse.click(10, 10)
        found = False
    return found


def is_excluded_uma_skill(name: str) -> bool:
    # Explicit blacklist from config (loaded into state.SKILL_BLACKLIST)
    try:
        if name in state.SKILL_BLACKLIST:
            return True
    except Exception:
        # State may not be initialized; fall back to no explicit blacklist
        pass

    # Exclude prerequisite-tier skills (○)
    if name.strip().endswith("○"):
        return True

    return False


def adjust_skill_cost(name: str, cost: int) -> int:
    """
    ◎ skills require buying the ○ prerequisite.
    Approximate by increasing the cost proportionally
    """
    if name.strip().endswith("◎"):
        return cost * 20 / 9
    return cost


def wait_for_results_to_stabilize(page, check_interval=3, max_wait=30):
    start = time.time()
    previous = None

    while True:
        rows = page.query_selector_all(".basinnChartWrapperWrapper table tbody tr")
        current = [
            [td.inner_text().strip() for td in row.query_selector_all("td")]
            for row in rows
        ]

        if current and current == previous:
            debug("Umalator results stabilized")
            return current

        if time.time() - start > max_wait:
            warning("Umalator stabilization timeout")
            return current

        previous = current
        time.sleep(check_interval)


def clean_number(value: str) -> float:
    if not value:
        raise ValueError("Empty numeric value")

    value = value.replace("−", "-").replace("L", "").replace(",", "").replace("\n", "")
    return float(value)


# =========================
# UMALATOR
# =========================


def run_umalator_sim(
    preset_name,
    uma_stats=state.STAT_CAPS,
    running_style=None,
    url=UMALATOR_URL,
):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        # --- Preset ---
        preset_select = page.wait_for_selector("select", timeout=10000)
        for opt in preset_select.query_selector_all("option"):
            if opt.inner_text().strip() == preset_name:
                preset_select.select_option(opt.get_attribute("value"))
                break
        else:
            error(f"Preset '{preset_name}' not found")
            browser.close()
            return []

        # --- Stats ---
        inputs = page.query_selector_all(".horseParam input[type='number']")
        for i, key in enumerate(["spd", "sta", "pwr", "guts", "wit"]):
            inputs[i].fill(str(uma_stats[key]))

        # --- Running style ---
        style_name = RUNNING_STYLE_MAP[running_style]
        style_select = page.wait_for_selector(".horseStrategySelect", timeout=10000)
        for opt in style_select.query_selector_all("option"):
            if opt.inner_text().strip() == style_name:
                style_select.select_option(opt.get_attribute("value"))
                break

        # --- Chart mode ---
        page.wait_for_selector('input[name="mode"][value="chart"]').check()

        # --- inject_purchased_skills ---
        inject_purchased_skills(page)

        # --- Run ---
        page.click("button#run")
        time.sleep(2)

        page.wait_for_selector(
            ".basinnChartWrapperWrapper table tbody tr", timeout=10000
        )
        rows = wait_for_results_to_stabilize(page)

        mean_idx = page.evaluate(
            """
        () => {
            const ths = [...document.querySelectorAll(
                '.basinnChartWrapperWrapper table thead th'
            )];
            return ths.findIndex(h => h.innerText.includes('Mean'));
        }
        """
        )

        if mean_idx == -1:
            error("Mean column not found")
            browser.close()
            return []

        skills = []
        for row in rows:
            try:
                skills.append(
                    {"name": row[0].strip(), "mean": clean_number(row[mean_idx])}
                )
            except Exception:
                continue

        browser.close()
        skills.sort(key=lambda s: s["mean"], reverse=True)
        return skills


def fetch_and_save_presets(url: str = UMALATOR_URL, out_path: str = "scraper/data/preset_names.json") -> list:
    """Fetch preset options from the Umalator page and save them to JSON.

    Returns a list of {label, value} objects.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)

            # Try well-known select id first, then fall back to the first <select>
            select_el = None
            try:
                select_el = page.wait_for_selector("select#P0-0", timeout=5000)
            except Exception:
                try:
                    select_el = page.wait_for_selector("select", timeout=5000)
                except Exception:
                    select_el = None

            presets: list[dict] = []
            if select_el:
                for opt in select_el.query_selector_all("option"):
                    try:
                        label = opt.inner_text().strip()
                        value = opt.get_attribute("value")
                        # Exclude empty labels and sentinel values
                        if not label:
                            continue
                        if str(value) == "-1":
                            continue
                        presets.append({"label": label, "value": value})
                    except Exception:
                        continue

            browser.close()

        # Ensure directory exists and write file
        out_file = Path(out_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with out_file.open("w", encoding="utf-8") as f:
            json.dump({"presets": presets}, f, ensure_ascii=False, indent=2)

        info(f"Saved {len(presets)} presets to {out_path}")
        return presets
    except Exception as e:
        error(f"Failed to fetch/save presets from {url}: {e}")
        return []


# =========================
# MAIN LOGIC
# =========================


def select_best_skills_by_mean():
    """
    OCR finds in-game skills
    Umalator defines which skills are allowed and total improvement
    OCR can NEVER introduce new skills
    """
    preset_name = getattr(state, "SKILL_PRESET_NAME", "") or ""
    # Determine which Umalator URL to use:
    # - If a preset is selected, use the default UMALATOR_URL
    # - If no preset is selected, use a custom URL from config (state.SKILL_UMALATOR_URL)
    if not preset_name.strip():
        custom_url = getattr(state, "SKILL_UMALATOR_URL", "") or ""
        if not custom_url.strip():
            info("No race preset selected (preset_name empty) — skipping Umalator run")
            return []
        url_to_use = custom_url
    else:
        url_to_use = UMALATOR_URL

    # --- Read SP ---
    screen = enhanced_screenshot(CAREER_COMPLETE_SP_REGION)
    try:
        current_sp = int(extract_text(screen))
    except ValueError:
        warning("Failed to OCR skill points; assuming 0")
        current_sp = 0

    debug(f"Current skill points: {current_sp}")

    # --- Select stats safely ---
    if is_valid_stat_block(state.CURRENT_STATS):
        debug("Using current stats")
        umastats = state.CURRENT_STATS

    elif is_valid_stat_block(state.LAST_VALID_STATS):
        debug("Using last valid stats")
        umastats = state.LAST_VALID_STATS

    else:
        debug("Using stat caps")
        umastats = state.STAT_CAPS

    # --- OCR scan (collect mode) ---
    scan_ctx = {
        "mode": "collect",
        "collected_skills": [],
        "skills_to_buy": [],
        "max_cost": 999,
        "min_discount": 0,
        "found": False,
    }

    click(img="assets/buttons/finale_skills.png")
    sleep(0.5)
    scan_skills(scan_ctx)
    sleep(0.5)
    click(img="assets/buttons/back_btn.png")
    sleep(0.5)

    if not scan_ctx["collected_skills"]:
        info("No matching skills found. Exiting early.")
        return []
    
    click(img="assets/buttons/skills_btn.png")
    sleep(0.5)

    # --- Run Umalator ---
    uma_results = run_umalator_sim(
        preset_name=preset_name, uma_stats=umastats, running_style=state.PREFERRED_POSITION, url=url_to_use
    )

    if not uma_results:
        warning("Umalator returned no results")
        return []

    allowed_uma = {
        s["name"]: s["mean"]
        for s in uma_results
        if not is_excluded_uma_skill(s["name"])
    }

    debug(f"Allowed Umalator skills: {len(allowed_uma)}")

    # --- Merge OCR → Umalator (UMA-gated) ---
    merged = []

    for ingame in scan_ctx["collected_skills"]:
        for uma_name, mean in allowed_uma.items():
            matched, _ = is_skill_match(ingame["name"], [uma_name])
            if matched:
                base_cost = int(ingame["cost"])
                adjusted_cost = adjust_skill_cost(uma_name, base_cost)

                merged.append(
                    {"name": uma_name, "cost": adjusted_cost, "mean": float(mean)}
                )
                break

    if not merged:
        warning("No OCR skills matched allowed Umalator skills")
        return []

    # --- Deduplicate If needed ---
    unique = {}
    for s in merged:
        if s["name"] not in unique or s["mean"] > unique[s["name"]]["mean"]:
            unique[s["name"]] = s

    candidates = list(unique.values())

    # --- Knapsack ---
    max_sp = int(current_sp)
    dp = [(0.0, []) for _ in range(max_sp + 1)]

    for idx, skill in enumerate(candidates):
        # ensure cost is an integer index (ceil to be conservative)
        cost = int(math.ceil(skill["cost"]))
        value = skill["mean"]

        for sp in range(max_sp, cost - 1, -1):
            prev_val, prev_items = dp[sp - cost]
            new_val = prev_val + value
            if new_val > dp[sp][0]:
                dp[sp] = (new_val, prev_items + [idx])

    _, best_idxs = max(dp, key=lambda x: x[0])
    selected = [candidates[i] for i in best_idxs]

    if not selected:
        info("No matching skills found. Exiting early.")
        return []

    debug("Final selected skills:")
    for s in selected:
        debug(f"  - {s['name']} | cost={s['cost']} | mean={s['mean']:.4f}")

    # --- Buy phase (guarded) ---
    buy_ctx = {
        "mode": "buy",
        "skills_to_buy": selected,
        "max_cost": 999,
        "min_discount": 0,
        "found": False,
        "collect_all_skills": True,
    }

    click(img="assets/buttons/finale_skills.png")
    sleep(0.5)
    scan_skills(buy_ctx)

    return selected


REQUIRED_STATS = ("spd", "sta", "pwr", "guts", "wit")


def is_valid_stat_block(stats: dict) -> bool:
    """
    A stat block is valid if:
    - It is a dict
    - Contains all required keys
    - All values are ints >= 1
    """
    if not isinstance(stats, dict):
        return False

    for k in REQUIRED_STATS:
        v = stats.get(k)
        if not isinstance(v, int) or v < 1:
            return False

    return True
