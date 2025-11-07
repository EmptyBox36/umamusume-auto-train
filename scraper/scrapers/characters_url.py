import re
import time
import logging
from selenium.webdriver.common.by import By
from requests.exceptions import ReadTimeout as RequestsReadTimeout
from selenium.common.exceptions import TimeoutException, WebDriverException

from .base import BaseScraper, create_chromedriver  # reuse your driver + save helpers

def _go(driver, url, tries=2):
    for _ in range(tries):
        try:
            driver.get(url)
            return True
        except (TimeoutException, WebDriverException):
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
        except RequestsReadTimeout:
            pass
    return False

class CharactersURLScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/characters", "characters_url.json")
        self.data = []

    def _scrape_detail(self, driver) -> dict | None:
        raw_h1 = driver.find_element(By.CSS_SELECTOR, "h1[class*='utils_headingXl']").text.strip()

        m = re.match(r"^(.*?)(?:\s*\(([^)]+)\))?$", raw_h1)
        base = m.group(1).strip()
        variant = m.group(2)
        display_name = f"{base} ({variant})" if variant else base

        # Full-body standing image
        img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/characters/chara_stand_']"
        ).get_attribute("src")

        return {"name": display_name, "image_url": img}

    def start(self):
        driver = create_chromedriver()
        if not _go(driver, self.url):
            driver.quit(); return
        time.sleep(2)
        self.handle_cookie_consent(driver)

        grid = driver.find_element(By.XPATH, "//div[contains(@class, 'sc-70f2d7f-0')]")
        items = [a for a in grid.find_elements(By.CSS_SELECTOR, "a.sc-73e3e686-1") if a.is_displayed()]
        logging.info(f"Found {len(items)} characters.")
        links = [a.get_attribute("href") for a in items]

        ad_banner_closed = False
        items = []

        for i, link in enumerate(links, start=1):
            ad_banner_closed = self.handle_ad_banner(driver, ad_banner_closed)
            logging.info(f"[{i}/{len(links)}] {link}")

            if not _go(driver, link):
                logging.warning("Detail load failed; restarting driver...")
                driver.quit()
                driver = create_chromedriver()
                if not _go(driver, self.url):
                    logging.warning("Reopen index failed; skipping link."); continue
                time.sleep(1); self.handle_cookie_consent(driver); ad_banner_closed = False
                if not _go(driver, link):
                    logging.warning("Still cannot load; skipping."); continue

            time.sleep(1.5)
            item = self._scrape_detail(driver)
            if item:
                items.append(item)

            if i % 20 == 0:
                driver.quit()
                driver = create_chromedriver()
                _ = _go(driver, self.url)
                time.sleep(1); self.handle_cookie_consent(driver); ad_banner_closed = False

        self.data = sorted(items,key=lambda x: (re.sub(r"\s*\(.*?\)", "", x["name"]).strip().lower(), x["name"].lower()))
        self.save_data()
        driver.quit()