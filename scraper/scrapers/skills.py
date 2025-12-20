import logging
import re
import time

from selenium.webdriver.common.by import By

from .base import BaseScraper, create_chromedriver


class SkillScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/skills", "./data/skills.json")

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        btn = driver.find_element(
            By.XPATH,
            "//div[contains(@class, 'utils_padbottom_half')]//button[contains(@class, 'filters_button_moreless')]",
        )
        btn.click()
        time.sleep(0.1)
        driver.find_element(
            By.XPATH, "//input[contains(@id, 'showIdCheckbox')]"
        ).click()
        time.sleep(0.1)
        driver.find_element(
            By.XPATH, "//input[contains(@id, 'showUniqueCharCheckbox')]"
        ).click()
        time.sleep(0.1)

        rows = driver.find_elements(
            By.XPATH, "//div[contains(@class, 'skills_table_row_ja')]"
        )
        logging.info(f"Found {len(rows)} non-hidden and hidden skill rows.")

        result = []
        for i, row in enumerate(rows):
            name = row.find_element(
                By.XPATH, ".//div[contains(@class, 'skills_table_jpname')]"
            ).text.strip()
            desc = row.find_element(
                By.XPATH, ".//div[contains(@class, 'skills_table_desc')]"
            ).text.strip()

            m = re.search(r"\((\d+)\)$", desc)
            sid = int(m.group(1)) if m else None
            clean = re.sub(r"\s*\(\d+\)$", "", desc) if m else desc

            if name:
                result.append({"id": sid, "name": name, "description": clean})
                logging.info(f"Scraped skill ({i + 1}/{len(rows)}): {name}")

        self.data = result
        self.save_data()
        driver.quit()
