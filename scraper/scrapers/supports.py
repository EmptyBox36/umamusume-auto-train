import time
import re
import logging
from urllib.parse import urljoin

from .base_pw import BaseScraperPW, create_pw, close_pw


def goto_with_retry(page, url: str, base: str, tries: int = 3, delay: float = 2.0):
    target = urljoin(base, url)
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

class SupportCardScraper(BaseScraperPW):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/supports", "supports.json")

    def start(self):
        pw, browser, context, page = create_pw(headless=True)
        try:
            page.goto(self.url, wait_until="domcontentloaded")
            time.sleep(3)

            self.handle_cookie_consent(page)

            grid = page.locator("xpath=//div[contains(@class, 'sc-70f2d7f-0')]").first
            items = grid.locator("xpath=.//div[contains(@class, 'sc-73e3e686-3')]")

            links = []
            for i in range(items.count()):
                it = items.nth(i)
                if not it.is_visible():
                    continue
                # match selenium: it.find_element(By.XPATH, "./..").get_attribute("href") :contentReference[oaicite:13]{index=13}
                href = it.locator("xpath=./..").get_attribute("href")
                if href:
                    links.append(href)

            logging.info(f"Found {len(links)} support cards.")

            for i, link in enumerate(links):
                max_link_retry = 3
                attempt = 0

                while attempt < max_link_retry:
                    try:
                        # keep your "restart every 5 cards" behavior :contentReference[oaicite:14]{index=14}
                        if i % 5 == 0:
                            context.close()
                            context = browser.new_context()
                            page = context.new_page()
                            page.set_default_timeout(15_000)
                            page.set_default_navigation_timeout(15_000)
                            goto_with_retry(page, self.url, base=self.url, tries=3)
                            time.sleep(0.5)
                            self.handle_cookie_consent(page)

                        logging.info(f"Navigating to {link} ({i + 1}/{len(links)})")
                        if not goto_with_retry(page, link, base=self.url, tries=3):
                            raise RuntimeError(f"Could not load {link}")

                        time.sleep(1.0)

                        raw = page.locator("xpath=//h1[contains(@class, 'utils_headingXl')]").first.inner_text()
                        name = re.sub(r"\s*\(.*?\)", "", raw.replace("Support Card", "")).strip()

                        temp_dict = {}
                        self.process_training_events(page, name, temp_dict)

                        self.data.update(temp_dict)
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