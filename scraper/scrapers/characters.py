import time
import re
import logging
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PWTimeoutError

from .base_pw import BaseScraperPW, create_pw, close_pw


def goto_with_retry(page, url: str, base: str, tries: int = 3, delay: float = 2.0):
    target = urljoin(base, url)  # makes /path -> https://gametora.com/path
    for attempt in range(1, tries + 1):
        try:
            page.goto(target, wait_until="domcontentloaded")
            return True
        except Exception as e:
            logging.error(f"goto error {attempt}/{tries}: {e}")
            try:
                page.evaluate("window.stop()")
            except Exception:
                pass
            time.sleep(delay)
    return False

class CharacterScraper(BaseScraperPW):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/characters", "characters.json")

    def _sort_by_name(self, page):
        row = page.locator("xpath=//div[contains(@class, 'filters_sort_row')]").first
        first = row.locator("xpath=.//select[1]").first
        first.select_option("name")
        time.sleep(0.1)
        second = row.locator("xpath=.//select[2]").first
        second.select_option("asc")
        time.sleep(0.1)

    def start(self):
        pw, browser, context, page = create_pw(headless=True)
        try:
            page.goto(self.url, wait_until="domcontentloaded")
            time.sleep(3)

            self.handle_cookie_consent(page)
            self._sort_by_name(page)

            grid = page.locator("xpath=//div[contains(@class, 'sc-70f2d7f-0')]").first
            items = grid.locator("css=a.sc-73e3e686-1")
            links = []
            for i in range(items.count()):
                a = items.nth(i)
                if a.is_visible():
                    href = a.get_attribute("href")
                    if href:
                        links.append(href)

            logging.info(f"Found {len(links)} characters.")

            for i, link in enumerate(links):
                max_link_retry = 3
                attempt = 0

                while attempt < max_link_retry:
                    try:
                        # Your Selenium code restarts every character (i % 1 == 0). :contentReference[oaicite:10]{index=10}
                        # In Playwright, restart the context/page instead (lighter than restarting OS process).
                        context.close()
                        context = browser.new_context()
                        page = context.new_page()
                        page.set_default_timeout(15_000)
                        page.set_default_navigation_timeout(15_000)

                        goto_with_retry(page, self.url, base=self.url, tries=3)
                        time.sleep(0.5)
                        self.handle_cookie_consent(page)
                        self._sort_by_name(page)

                        logging.info(f"Navigating to {link} ({i + 1}/{len(links)})")
                        if not goto_with_retry(page, link, base=self.url, tries=5):
                            raise RuntimeError(f"Could not load {link}")

                        time.sleep(1.0)

                        raw_h1 = page.locator("css=h1[class*='utils_headingXl']").first.inner_text().strip()
                        m = re.match(r"^(.*?)(?:\s*\(([^)]+)\))?$", raw_h1)
                        base = m.group(1).strip()
                        variant = m.group(2)
                        name = f"{base} ({variant})" if variant else base

                        attempt_data = {}
                        self.process_training_events(page, name, attempt_data)
                        self.data[name] = attempt_data
                        break

                    except Exception as e:
                        attempt += 1
                        logging.error(
                            f"Error while processing {link} ({i + 1}/{len(links)}), "
                            f"attempt {attempt}/{max_link_retry}: {e}"
                        )
                        if attempt >= max_link_retry:
                            raise

            self.save_data()

        finally:
            try:
                context.close()
            except Exception:
                pass
            close_pw(pw, browser)