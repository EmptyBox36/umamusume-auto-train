import json, re, time, logging
from typing import Optional
from pathlib import Path
from typing import List, Dict
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, WebDriverException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC

from utils.utils import clean_event_title, STAT_KEYS, ALIASES, DIVIDER_RE, IGNORE_PATTERNS, ALL_STATS, COMMON_EVENT_TITLES, RAND_SPLIT_RE

TOOLTIP_VISIBLE = "//div[contains(@class,'tippy-content')]"
# header is the first div inside tippy-content that holds the event title text
TOOLTIP_HEADER_REL = ".//div[1]"

# ---- helpers ----
def blank_stats():
    d = {k: 0.0 for k in STAT_KEYS}
    # collect all skill hints for this outcome as a list
    d["Skill Hint"] = []
    return d

def _worst_num(text: str) -> float | None:
    nums = re.findall(r"[+-]?\d+", text)
    return float(min(int(n) for n in nums)) if nums else None

def add(d: dict, k: str, v: float):
    if k in d:
        d[k] += v
       
def _finish(d: dict) -> dict:
    d.pop("Skill", None)

    for k in STAT_KEYS:
        if k not in d:
            if k == "Skill Hint":
                d[k] = []
            else:
                d[k] = 0.0

    # if older code ever left a non-list here, normalize it
    if not isinstance(d.get("Skill Hint"), list):
        if d.get("Skill Hint"):
            d["Skill Hint"] = [d["Skill Hint"]]
        else:
            d["Skill Hint"] = []

    return d

def _is_ignorable(line: str) -> bool:
    return any(p in line for p in IGNORE_PATTERNS)

def parse_outcome_block(text: str) -> dict:
    d = blank_stats()
    for ln in (x.strip() for x in text.splitlines() if x.strip()):
        if _is_ignorable(ln):
            continue

        # full recovery to HP +200
        if re.search(r"\bfull\s+energy\s+recovery\b", ln, re.I):
            add(d, "HP", 200.0)
            continue

        # Skill hint lines, possibly more than one per choice.
        if re.search(r"\bhint\b", ln, re.I):
            # skip random skills like "Skill hint (random)"
            if re.search(r"\(random\)", ln, re.I):
                continue

            skill_name = re.sub(r"\s*hint.*", "", ln, flags=re.I).strip()
            if skill_name:
                if not isinstance(d.get("Skill Hint"), list):
                    d["Skill Hint"] = []
                d["Skill Hint"].append(skill_name)
            continue

        # Bond → Friendship
        m = re.search(r"bond\s*([+-]?\d+)", ln, re.I)
        if m:
            add(d, "Friendship", float(m.group(1)))
            continue

        # All stats ±N
        m = re.search(r"\bAll stats\s*([+-]?\d+)", ln, re.I)
        if m:
            val = float(m.group(1))
            for k in ALL_STATS:
                add(d, k, val)
            continue

        m = re.search(r"\bSkill(?:\s+Points?|\s+points?)?\s*([+-]?\d+)", ln, re.I)
        if m:
            add(d, "Skill Pts", float(m.group(1)))
            continue

        # Generic stat line (supports ranges like -5/-20)
        m = re.match(r"^([A-Za-z ][A-Za-z ]*?)\s+(.+)$", ln)
        if m:
            raw, tail = m.group(1).strip(), m.group(2).strip()
            key = ALIASES.get(raw, raw)
            if key in STAT_KEYS:
                val = _worst_num(tail)
                if val is not None:
                    add(d, key, val)
            continue
    d["random"] = False

    return _finish(d)

def parse_randomly(text: str) -> dict:
    # drop the header line
    body = re.sub(r"^\s*Randomly either.*?\n", "", text, flags=re.I | re.S)
    # split on dashed dividers OR an 'or' line (with optional percentage)
    parts = [p.strip() for p in RAND_SPLIT_RE.split(body) if p.strip()]
    if not parts:
        return parse_outcome_block(text)

    worst_d, worst_key = None, (0, float("inf"))
    first_d = None
    combined_hints: list[str] = []

    for part in parts:
        d = parse_outcome_block(part)
        if first_d is None:
            first_d = d

        hints = d.get("Skill Hint") or []
        if not isinstance(hints, list):
            hints = [hints]
        for h in hints:
            h = (h or "").strip()
            if h and h not in combined_hints:
                combined_hints.append(h)

        nums = [v for v in d.values() if isinstance(v, (int, float))]
        if nums:
            key = (min(nums), sum(nums))
            if key < worst_key:
                worst_d, worst_key = d, key

    # if no numeric stats, fall back to the first parsed branch
    if worst_d is None:
        worst_d = first_d or blank_stats()

    worst_d["Skill Hint"] = combined_hints
    worst_d["random"] = True

    return _finish(worst_d)

def parse_outcome(text: str) -> dict:
    return parse_randomly(text) if "Randomly either" in text else parse_outcome_block(text)

def create_chromedriver():

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-features=PrivacySandboxAdsAPIs")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--renderer-process-limit=2")
    opts.add_argument("--force-device-scale-factor=1")

    caps = DesiredCapabilities.CHROME.copy()
    caps["pageLoadStrategy"] = "eager"  # don’t wait for ads/analytics

    driver = uc.Chrome(
        headless=True,
        use_subprocess=True,
        options=opts,
        desired_capabilities=caps,
    )
    driver.set_page_load_timeout(15)
    driver.set_script_timeout(15)
    return driver

class BaseScraper:
    def __init__(self, url: str, output_filename: str):
        self.url = url
        self.output_filename = output_filename
        self.data = {}
        self.cookie_accepted = False

    def safe_click(self, driver: uc.Chrome, element: WebElement, retries: int = 3, delay: float = 0.5):
        for _ in range(retries):
            try:
                element.click()
                return True
            except ElementClickInterceptedException:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    driver.execute_script("arguments[0].click();", element)
                    return True
                except WebDriverException:
                    time.sleep(delay)
        return False

    def save_data(self, save_path=None):
        # set default to ../data relative to script location
        base_dir = Path(__file__).resolve().parent.parent / "data"
        output_path = Path(save_path) if save_path else base_dir / Path(self.output_filename).name

        # ensure the folder exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

        logging.info(f"Saved {len(self.data)} items to {output_path}")

    def handle_cookie_consent(self, driver: uc.Chrome):
        if not self.cookie_accepted:
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(@class, 'legal_cookie_banner_button')]")
                if btn:
                    btn.click()
                    time.sleep(0.1)
                    self.cookie_accepted = True
                    logging.info("Cookie consent accepted.")
            except NoSuchElementException:
                logging.info("No cookie consent button found.")
                self.cookie_accepted = True

    def handle_ad_banner(self, driver: uc.Chrome, skip=False):
        if not skip:
            try:
                btn = driver.find_element(By.XPATH, "//div[contains(@class, 'publift-widget-sticky_footer-button')]")
                if btn and btn.is_displayed():
                    btn.click()
                    time.sleep(0.1)
                    logging.info("Ad banner dismissed.")
                    return True
            except NoSuchElementException:
                logging.info("No ad banner found.")
            return False
        return True

    def _get_visible_tooltip_for(self, driver: uc.Chrome, title: str) -> Optional[WebElement]:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, TOOLTIP_VISIBLE))
        )
        tips = driver.find_elements(By.XPATH, TOOLTIP_VISIBLE)
        title_norm = (title or "").strip().lower()

        for tip in reversed(tips):  # newest usually last
            try:
                header = tip.find_element(By.XPATH, TOOLTIP_HEADER_REL).text.strip().lower()
            except Exception:
                header = ""
            if title_norm and title_norm in header:
                return tip
        return tips[-1] if tips else None

    def extract_training_event_options(self, tooltip_rows: List[WebElement]):
        """
        Extract training event options from tooltip rows, using the same dynamic
        sc-*-2 / sc-*-0 patterns as main.py, and convert to {choices, stats}.
        """
        choices: Dict[str, str] = {}
        stats: Dict[str, dict] = {}

        for idx, tooltip_row in enumerate(tooltip_rows, 1):
            try:
                # Main content block for this option
                event_option_div = tooltip_row.find_element(
                    By.XPATH,
                    ".//div[contains(@class, 'sc-') and contains(@class, '-2 ')]"
                )
            except NoSuchElementException:
                # Fallback: use the row itself if inner div not found
                event_option_div = tooltip_row

            # All text fragments inside this option
            event_result_divs = event_option_div.find_elements(By.XPATH, ".//div")
            text_fragments = [div.text.strip() for div in event_result_divs if div.text.strip()]

            if not text_fragments:
                continue

            # Handle "Randomly either" layout exactly like main.py
            if "Randomly either" in text_fragments[0]:
                option_text = "Randomly either\n----------\n"
                current_group: list[str] = []
                for fragment in text_fragments[1:]:
                    if fragment == "or":
                        # finish current branch
                        if current_group:
                            option_text += "\n".join(current_group) + "\n----------\n"
                            current_group = []
                    else:
                        current_group.append(fragment)
                # last branch
                if current_group:
                    option_text += "\n".join(current_group)
            else:
                # Regular multi-line outcome
                option_text = "\n".join(text_fragments)

            # Normalize terminology to match your stats keys
            option_text = option_text.replace("Wisdom", "Wit")

            key = str(idx)
            choices[key] = f"Choice {idx}"
            stats[key] = parse_outcome(option_text)

        return {"choices": choices, "stats": stats}

    def process_training_events(self, driver: uc.Chrome, item_name: str, data_dict):
        """Processes the training events for the given item, main.py style.

        Args:
            driver (uc.Chrome): The Chrome driver.
            item_name (str): The name of the item (character/support).
            data_dict (dict): The data dictionary to modify.
        """
        # All training-event buttons in the infobox
        all_training_events = driver.find_elements(
            By.XPATH,
            "//button[contains(@class, 'sc-') and contains(@class, '-0 ')]"
        )
        logging.info(f"Found {len(all_training_events)} training events for {item_name}.")

        ad_banner_closed = False

        for j, training_event in enumerate(all_training_events):
            # Click the event row (with JS fallback)
            self.safe_click(driver, training_event)
            time.sleep(1.0)

            # Tooltip root created by tippy.js
            try:
                tooltip = driver.find_element(By.XPATH, "//div[@data-tippy-root]")
            except NoSuchElementException:
                logging.warning(f"No tooltip root for training event ({j + 1}/{len(all_training_events)}).")
                continue

            # Event title inside tooltip
            try:
                raw_title = tooltip.find_element(
                    By.XPATH,
                    ".//div[contains(@class, 'sc-') and contains(@class, '-2 ')]"
                ).text.strip()

                tooltip_title = raw_title.split("\n", 1)[0].strip()
                if not tooltip_title:
                    logging.warning(f"Empty tooltip title for training event ({j + 1}/{len(all_training_events)}).")
                    continue

                key = clean_event_title(tooltip_title)
                if key in data_dict:
                    logging.info(
                        f"Training event {tooltip_title} ({j + 1}/{len(all_training_events)}) "
                        f"was already scraped. Skipping."
                    )
                    continue
            except NoSuchElementException:
                logging.warning(
                    f"No tooltip title found for training event ({j + 1}/{len(all_training_events)})."
                )
                continue

            # Each option row inside the tooltip
            tooltip_rows = tooltip.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'sc-') and contains(@class, '-0 ')]"
            )
            if len(tooltip_rows) == 0:
                logging.warning(
                    f"No options found for training event {tooltip_title} "
                    f"({j + 1}/{len(all_training_events)})."
                )
                continue

            logging.info(
                f"Found {len(tooltip_rows)} options for training event {tooltip_title} "
                f"({j + 1}/{len(all_training_events)})."
            )

            result = self.extract_training_event_options(tooltip_rows)

            choices = result.get("choices") or {}
            if len(choices) > 1:
                data_dict[key] = result

            # Handle sticky ad banner between events
            ad_banner_closed = self.handle_ad_banner(driver, ad_banner_closed)