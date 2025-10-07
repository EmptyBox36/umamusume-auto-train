import time, re, logging
from selenium.webdriver.common.by import By
from .base import BaseScraper, create_chromedriver

class SupportCardScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/supports", "supports.json")

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        grid = driver.find_element(By.XPATH, "//div[contains(@class, 'sc-70f2d7f-0')]")
        items = grid.find_elements(By.XPATH, ".//div[contains(@class, 'sc-73e3e686-3')]")
        items = [it for it in items if it.is_displayed()]
        logging.info(f"Found {len(items)} support cards.")
        links = [it.find_element(By.XPATH, "./..").get_attribute("href") for it in items]

        for i, link in enumerate(links):
            logging.info(f"Navigating to {link} ({i + 1}/{len(links)})")
            driver.get(link); time.sleep(3)
            raw = driver.find_element(By.XPATH, "//h1[contains(@class, 'utils_headingXl')]").text
            name = re.sub(r'\s*\(.*?\)', '', raw.replace("Support Card", "")).strip()
            temp_dict = {}
            self.process_training_events(driver, name, temp_dict)
            self.data.update(temp_dict)

        self.save_data()
        driver.quit()
