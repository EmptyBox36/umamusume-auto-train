import time, re, logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from requests.exceptions import ReadTimeout as RequestsReadTimeout
from selenium.common.exceptions import TimeoutException, WebDriverException

from .base import BaseScraper, create_chromedriver
from utils.utils import clean_event_title, COMMON_EVENT_TITLES

def _go(driver, url, tries=2):
    for attempt in range(1, tries + 1):
        try:
            driver.get(url)
            return True

        except Exception as e:
            msg = str(e)
            logging.error(f"_go error on attempt {attempt}/{tries}: {msg}")

            # Detect broken chrome/CDP session
            if "HTTPConnectionPool" in msg or "Read timed out" in msg:
                return "RESTART"   # signal caller to recreate driver

            # Normal retry
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
            time.sleep(2)

    return False

def load_with_retry(driver, url: str, max_retry: int = 3, delay: float = 10.0):
    for attempt in range(1, max_retry + 1):
        try:
            driver.get(url)
            return True  # success
        except Exception as e:
            logging.error(f"Load failed ({attempt}/{max_retry}) for {url}: {e}")
            time.sleep(delay)
    return False

class CharacterScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/characters", "characters.json")

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)
        self._sort_by_name(driver)

        grid = driver.find_element(By.XPATH, "//div[contains(@class, 'sc-70f2d7f-0')]")
        items = [a for a in grid.find_elements(By.CSS_SELECTOR, "a.sc-73e3e686-1") if a.is_displayed()]
        logging.info(f"Found {len(items)} characters.")
        links = [a.get_attribute("href") for a in items]

        for i, link in enumerate(links):
            if i % 2 == 0:
                driver.quit()
                driver = create_chromedriver()
                _ = _go(driver, self.url)
                time.sleep(1)

            logging.info(f"Navigating to {link} ({i + 1}/{len(links)})")

            result = _go(driver, link, tries=2)

            if result == "RESTART":
                logging.warning("Restarting Chrome due to connection failure...")
                driver.quit()
                driver = create_chromedriver()
                _ = _go(driver, self.url)
                time.sleep(1)
                # retry the SAME link again
                if _go(driver, link, tries=2) is not True:
                    if not load_with_retry(driver, link, max_retry=5, delay=10):
                        raise RuntimeError(f"Could not load {link} after Chrome restart")
            elif result is False:
                logging.warning("Normal _go failure, trying extended retries...")
                if not load_with_retry(driver, link, max_retry=5, delay=10):
                    raise RuntimeError(f"Could not load {link}")

            time.sleep(3)

            # name = driver.find_element(By.XPATH, "//h1[contains(@class, 'utils_headingXl')]").text
            # name = re.sub(r'\s*\(.*?\)', '', name.replace("(Original)", "")).strip()

            raw_h1 = driver.find_element(By.CSS_SELECTOR, "h1[class*='utils_headingXl']").text.strip()
            m = re.match(r"^(.*?)(?:\s*\(([^)]+)\))?$", raw_h1)
            base = m.group(1).strip()
            variant = m.group(2)
            name = f"{base} ({variant})" if variant else base

            if name not in self.data:
                self.data[name] = {}
            self.process_training_events(driver, name, self.data[name])
        
        self.save_data()
        driver.quit()

    def _sort_by_name(self, driver):
        row = driver.find_element(By.XPATH, "//div[contains(@class, 'filters_sort_row')]")
        first = row.find_element(By.XPATH, ".//select[1]")
        first.click(); time.sleep(0.1)
        first.find_element(By.XPATH, ".//option[@value='name']").click(); time.sleep(0.1)
        second = row.find_element(By.XPATH, ".//select[2]")
        second.click(); time.sleep(0.1)
        second.find_element(By.XPATH, ".//option[@value='asc']").click(); time.sleep(0.1)