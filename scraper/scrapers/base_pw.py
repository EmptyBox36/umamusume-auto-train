import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PWTimeoutError

from utils.utils import clean_event_title  # same as selenium base.py
from .base import parse_outcome  # reuse your existing parsing logic as-is


# Keep same XPaths you already use in selenium base.py
TOOLTIP_VISIBLE = "//div[contains(@class,'tippy-content')]"
TOOLTIP_HEADER_REL = ".//div[1]"


def create_pw(headless: bool = True):
    """
    Returns (playwright, browser, context, page).
    Call close_pw(...) when done.
    """
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    # match your selenium timeouts (15s)
    page.set_default_timeout(15_000)
    page.set_default_navigation_timeout(15_000)
    return pw, browser, context, page


def close_pw(pw, browser: Browser):
    try:
        browser.close()
    finally:
        pw.stop()


class BaseScraperPW:
    def __init__(self, url: str, output_filename: str):
        self.url = url
        self.output_filename = output_filename
        self.data: Dict[str, Any] = {}
        self.cookie_accepted = False

    def save_data(self, save_path=None):
        base_dir = Path(__file__).resolve().parent.parent / "data"
        output_path = Path(save_path) if save_path else base_dir / Path(self.output_filename).name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

        logging.info(f"Saved {len(self.data)} items to {output_path}")

    def handle_cookie_consent(self, page: Page):
        """
        Selenium version clicks:
        //button[contains(@class, 'legal_cookie_banner_button')]
        """
        if self.cookie_accepted:
            return

        btn = page.locator("xpath=//button[contains(@class, 'legal_cookie_banner_button')]")
        try:
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                time.sleep(0.1)
                logging.info("Cookie consent accepted.")
        except Exception:
            # treat as accepted to avoid retry loops
            pass

        self.cookie_accepted = True

    def handle_ad_banner(self, page: Page, skip: bool = False) -> bool:
        """
        Selenium version clicks:
        //div[contains(@class, 'publift-widget-sticky_footer-button')]
        and returns True once closed
        """
        if skip:
            return True

        btn = page.locator("xpath=//div[contains(@class, 'publift-widget-sticky_footer-button')]")
        try:
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                time.sleep(0.1)
                logging.info("Ad banner dismissed.")
                return True
        except Exception:
            pass
        return False

    def extract_training_event_options(self, tooltip_rows: List[Any]) -> Dict[str, Any]:
        """
        Playwright port of BaseScraper.extract_training_event_options()
        using the same 'sc-*-2' / 'sc-*-0' structure. :contentReference[oaicite:5]{index=5}
        """
        choices: Dict[str, str] = {}
        stats: Dict[str, dict] = {}

        for idx, row in enumerate(tooltip_rows, 1):
            # row is a Locator (from tooltip.locator(...).nth(i))
            option_div = row.locator("xpath=.//div[contains(@class, 'sc-') and contains(@class, '-2 ')]")
            if option_div.count() == 0:
                option_div = row

            fragments = [t.strip() for t in option_div.locator("xpath=.//div").all_inner_texts() if t.strip()]
            if not fragments:
                continue

            if "Randomly either" in fragments[0]:
                option_text = "Randomly either\n----------\n"
                current: List[str] = []
                for frag in fragments[1:]:
                    if frag == "or":
                        if current:
                            option_text += "\n".join(current) + "\n----------\n"
                            current = []
                    else:
                        current.append(frag)
                if current:
                    option_text += "\n".join(current)
            else:
                option_text = "\n".join(fragments)

            option_text = option_text.replace("Wisdom", "Wit")

            key = str(idx)
            choices[key] = f"Choice {idx}"
            stats[key] = parse_outcome(option_text)

        return {"choices": choices, "stats": stats}

    def process_training_events(self, page: Page, item_name: str, data_dict: Dict[str, Any]):
        """
        Playwright port of BaseScraper.process_training_events(). :contentReference[oaicite:6]{index=6}
        """
        events = page.locator("xpath=//button[contains(@class, 'sc-') and contains(@class, '-0 ')]")
        total = events.count()
        logging.info(f"Found {total} training events for {item_name}.")

        ad_banner_closed = False
        last_title = None
        same_title_run = 0
        SAME_TITLE_RUN_LIMIT = 3

        for j in range(total):
            ev = events.nth(j)
            try:
                ev.click()
            except Exception:
                # force click as fallback (Playwright supports force=True)
                ev.click(force=True)

            time.sleep(0.4)

            tooltip_root = page.locator("xpath=//div[@data-tippy-root]")
            if tooltip_root.count() == 0:
                logging.warning(f"No tooltip root for training event ({j + 1}/{total}).")
                continue

            # Event title
            title_el = tooltip_root.first.locator("xpath=.//div[contains(@class, 'sc-') and contains(@class, '-2 ')]").first
            try:
                raw_title = title_el.inner_text().strip()
            except Exception:
                logging.warning(f"No tooltip title found for training event ({j + 1}/{total}).")
                continue

            tooltip_title = raw_title.split("\n", 1)[0].strip()
            if not tooltip_title:
                logging.warning(f"Empty tooltip title for training event ({j + 1}/{total}).")
                continue

            if tooltip_title == last_title:
                same_title_run += 1
            else:
                last_title = tooltip_title
                same_title_run = 0

            if same_title_run >= SAME_TITLE_RUN_LIMIT:
                raise RuntimeError(
                    f"Suspicious repeated tooltip title '{tooltip_title}' "
                    f"for {item_name}: seen {same_title_run + 1} times in a row."
                )

            key = clean_event_title(tooltip_title)
            if key in data_dict:
                logging.info(f"Training event {tooltip_title} ({j + 1}/{total}) already scraped. Skipping.")
                continue

            # Option rows
            rows_locator = tooltip_root.first.locator("xpath=.//div[contains(@class, 'sc-') and contains(@class, '-0 ')]")
            row_count = rows_locator.count()
            if row_count == 0:
                logging.warning(f"No options found for training event {tooltip_title} ({j + 1}/{total}).")
                continue

            logging.info(f"Found {row_count} options for training event {tooltip_title} ({j + 1}/{total}).")
            rows = [rows_locator.nth(i) for i in range(row_count)]

            result = self.extract_training_event_options(rows)
            choices = result.get("choices") or {}
            if len(choices) > 1:
                data_dict[key] = result

            ad_banner_closed = self.handle_ad_banner(page, ad_banner_closed)