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
    d["Skill Hint"] = ""
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
            d[k] = "" if k == "Skill Hint" else 0.0
    return d

def _is_ignorable(line: str) -> bool:
    return any(p in line for p in IGNORE_PATTERNS)

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
        choices, stats = {}, {}

        def parse_div_row(row):
            label = row.find_element(By.XPATH, ".//span[1]").text.strip()
            full  = (row.text or "").strip()
            effect = full[len(label):].strip() if full.startswith(label) else full
            if not effect:
                # include all descendant div text, not excluding spans
                parts = [d.text.strip() for d in row.find_elements(By.XPATH, ".//div") if d.text.strip()]
                effect = "\n".join(parts).strip()
            return label, effect

        is_table = bool(tooltip_rows and tooltip_rows[0].find_elements(By.XPATH, ".//td[contains(@class,'tooltips_ttable_cell')]"))

        if is_table:
            for k, row in enumerate(tooltip_rows, 1):
                cells = row.find_elements(By.XPATH, ".//td[contains(@class,'tooltips_ttable_cell')]")
                if len(cells) < 2:
                    continue
                label = (cells[0].text or f"Choice {k}").strip()
                effect = "\n".join(div.text.strip() for div in cells[1].find_elements(By.XPATH, ".//div") if div.text.strip())
                effect = effect.replace("Wisdom", "Wit")
                choices[str(k)] = label
                stats[str(k)] = parse_outcome(effect)
        else:
            for k, row in enumerate(tooltip_rows, 1):
                label, effect = parse_div_row(row)
                if not label:
                    continue
                effect = (effect or "").replace("Wisdom", "Wit")
                choices[str(k)] = label
                stats[str(k)] = parse_outcome(effect)

        return {"choices": choices, "stats": stats}

    def process_training_events(self, driver: uc.Chrome, item_name: str, data_dict):
        # ensure ad is closed before the first click
        ad_banner_closed = self.handle_ad_banner(driver, False)
        common_data = {}

        i = 0
        while True:
            try:
                # re-find buttons each loop to avoid stales
                caption = driver.find_element(
                    By.XPATH, "//div[contains(@class,'infobox_caption')][contains(translate(normalize-space(.),"
                              " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'training events')]"
                )
                container = caption.find_element(By.XPATH, "./parent::div")
                buttons = container.find_elements(By.XPATH, ".//button[@aria-expanded]")
                if i >= len(buttons):
                    break
                btn = buttons[i]

                # make sure it is clickable and on screen
                WebDriverWait(driver, 8).until(EC.element_to_be_clickable(btn))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)

                def open_tooltip_for(title: str):
                    # warm-up click sequence to bypass overlays and hydration timing
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.12)
                    try:
                        btn.click()
                    except Exception:
                        ActionChains(driver).move_to_element(btn).click().perform()
                    try:
                        return self._get_visible_tooltip_for(driver, title)
                    except TimeoutException:
                        return None

                title = (btn.text or btn.get_attribute("aria-label") or f"Event {i+1}").strip()
                tooltip = open_tooltip_for(title)
                if tooltip is None:
                    time.sleep(0.3)  # first event after navigation needs a short bind time
                    tooltip = open_tooltip_for(title)
                if tooltip is None:
                    logging.info(f"No tooltip for [{title}] ({i+1}). Skipping.")
                    i += 1
                    continue

                try:
                    tooltip = tooltip.find_element(By.XPATH, ".//div[contains(@class,'tippy-content')]")
                except Exception:
                    pass

                try:
                    rows = tooltip.find_elements(By.XPATH,".//div[contains(@class,'fipImG') and .//div[contains(@class,'jtqpYA')]]") or tooltip.find_elements(By.XPATH, ".//tr")
                    if not rows:
                        logging.info(f"No options for {title} ({i+1}/{len(buttons)}).")
                    elif clean_event_title(title) in data_dict:
                        logging.info(f"Skip duplicate {title} ({i+1}/{len(buttons)}).")
                    else:
                        logging.info(f"Found {len(rows)} options for {title} ({i+1}/{len(buttons)}).")
                        result = self.extract_training_event_options(rows)
                        target = common_data if clean_event_title(title) in COMMON_EVENT_TITLES else data_dict
                        target[clean_event_title(title)] = result

                finally:
                    # close tooltip in a guarded block
                    try:
                        driver.execute_script("document.body.click();")
                        # try unmount
                        WebDriverWait(driver, 3).until(EC.staleness_of(tooltip))
                    except Exception:
                        # fall back to visible → invisible transition
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.invisibility_of_element_located((By.XPATH, TOOLTIP_VISIBLE))
                            )
                        except Exception:
                            pass

                ad_banner_closed = self.handle_ad_banner(driver, ad_banner_closed)

            except StaleElementReferenceException:
                logging.debug(f"Stale at index {i}; retrying next.")

            finally:
                i += 1