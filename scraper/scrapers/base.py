import json, re, time, logging
from pathlib import Path
from typing import List, Dict
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from utils.utils import clean_event_title, STAT_KEYS, ALIASES, DIVIDER_RE, IGNORE_PATTERNS, ALL_STATS, COMMON_EVENT_TITLES, RAND_SPLIT_RE

# ---- helpers ----
def blank_stats():
    d = {k: 0.0 for k in STAT_KEYS}
    d["Skill Hint"] = ""
    return d

def _worst_num(text: str) -> float | None:
    nums = re.findall(r"[+-]?\d+", text)
    return float(min(int(n) for n in nums)) if nums else None

def add(d: dict, k: str, v: float):
    if k in d:
        d[k] += v

        
def _finish(d: dict) -> dict:
    for k in STAT_KEYS:
        if k not in d:
            d[k] = "" if k == "Skill Hint" else 0.0
    return d

def _is_ignorable(line: str) -> bool:
    return any(p in line for p in IGNORE_PATTERNS)

def add(d: dict, k: str, v: float):
    if k in d: d[k] += v

def _finish(d: dict) -> dict:
    for k in STAT_KEYS:
        if k not in d:
            d[k] = "" if k == "Skill Hint" else 0.0
    return d

def parse_outcome_block(text: str) -> dict:
    d = blank_stats()
    for ln in (x.strip() for x in text.splitlines() if x.strip()):
        if _is_ignorable(ln): 
            continue

        # Skill hint: keep only the skill name; "(random)" → ""
        if re.search(r"\bhint\b", ln, re.I):
            d["Skill Hint"] = "" if re.search(r"\(random\)", ln, re.I) else re.sub(r"\s*hint.*", "", ln, flags=re.I).strip()
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
    return _finish(d)

def parse_randomly(text: str) -> dict:
    # drop the header line
    body = re.sub(r"^\s*Randomly either.*?\n", "", text, flags=re.I|re.S)
    # split on dashed dividers OR an 'or' line (with optional percentage)
    parts = [p.strip() for p in RAND_SPLIT_RE.split(body) if p.strip()]
    if not parts:
        return parse_outcome_block(text)

    # choose worst: most negative single delta, then lowest sum
    worst_d, worst_key = None, (0, float("inf"))
    for part in parts:
        d = parse_outcome_block(part)
        nums = [v for v in d.values() if isinstance(v, (int, float))]
        if not nums:
            continue
        key = (min(nums), sum(nums))
        if key < worst_key:
            worst_d, worst_key = d, key

    return _finish(worst_d or blank_stats())

def parse_outcome(text: str) -> dict:
    return parse_randomly(text) if "Randomly either" in text else parse_outcome_block(text)

def create_chromedriver():
    return uc.Chrome(headless=True, use_subprocess=True)

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

    def extract_training_event_options(self, tooltip_rows: List[WebElement]):
        """Return {"choices": {"1": label, ...}, "stats": {"1": {...}, ...}}."""
        choices, stats = {}, {}
        for i, row in enumerate(tooltip_rows, start=1):
            tds = row.find_elements(By.XPATH, ".//td[contains(@class, 'tooltips_ttable_cell')]")
            left = (tds[0].text or f"Choice {i}").strip()
            # right cell may have multiple <div>s; join with \n like current scraper
            right_divs = tds[1].find_elements(By.XPATH, ".//div")
            effect_text = "\n".join(d.text.strip() for d in right_divs)
            effect_text = effect_text.replace("Wisdom", "Wit")
            choices[str(i)] = left
            stats[str(i)] = parse_outcome(effect_text)
        return {"choices": choices, "stats": stats}


    def process_training_events(self, driver: uc.Chrome, item_name: str, data_dict: Dict[str, List[str]]):
        """Processes the training events for the given item.

        Args:
            driver (uc.Chrome): The Chrome driver.
            item_name (str): The name of the item.
            data_dict (Dict[str, List[str]]): The data dictionary to modify.
        """
        all_training_events = driver.find_elements(By.XPATH, "//div[contains(@class, 'compatibility_viewer_item')]")
        logging.info(f"Found {len(all_training_events)} training events for {item_name}.")

        ad_banner_closed = False
        common_data = {}

        for j, training_event in enumerate(all_training_events):
            self.safe_click(driver, training_event)
            time.sleep(0.3)

            tooltip = driver.find_element(By.XPATH, "//div[@data-tippy-root]")
            try:
                raw_title = tooltip.find_element(By.XPATH, ".//div[contains(@class, 'tooltips_ttable_heading')]").text
                tooltip_title = clean_event_title(raw_title)

            except NoSuchElementException:
                logging.info(f"No tooltip title found for training event ({j + 1}/{len(all_training_events)}).")
                continue

            tooltip_rows = tooltip.find_elements(By.XPATH, ".//tr")
            if len(tooltip_rows) == 0:
                logging.info(f"No options found for training event {tooltip_title} ({j + 1}/{len(all_training_events)}).")
                continue
            elif tooltip_title in data_dict:
                logging.info(f"Training event {tooltip_title} ({j + 1}/{len(all_training_events)}) already exists.")
                continue

            logging.info(f"Found {len(tooltip_rows)} options for training event {tooltip_title} ({j + 1}/{len(all_training_events)}).")

            result = self.extract_training_event_options(tooltip_rows)
            target = common_data if tooltip_title in COMMON_EVENT_TITLES else data_dict
            target[tooltip_title] = result

            ad_banner_closed = self.handle_ad_banner(driver, ad_banner_closed)
