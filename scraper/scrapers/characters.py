import time, re, logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .base import BaseScraper, create_chromedriver
from utils.utils import clean_event_title, COMMON_EVENT_TITLES

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
            logging.info(f"Navigating to {link} ({i + 1}/{len(links)})")
            driver.get(link); time.sleep(3)
            name = driver.find_element(By.XPATH, "//h1[contains(@class, 'utils_headingXl')]").text
            name = re.sub(r'\s*\(.*?\)', '', name.replace("(Original)", "")).strip()
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
