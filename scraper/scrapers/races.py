import time, logging, re
from selenium.webdriver.common.by import By
from .base import BaseScraper, create_chromedriver

class RaceScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/races", "./data/races.json")

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        race_list = driver.find_element(By.XPATH, "//div[contains(@class, 'races_race_list')]")
        items = race_list.find_elements(By.XPATH, ".//div[contains(@class, 'races_row')]")
        items = items[2:]          # drop Junior Make Debut/Maiden
        items = items[:-7]         # drop URA/GM/Twinkle end
        logging.info(f"Found {len(items)} races.")

        links = [it.find_element(By.XPATH, ".//div[contains(@class, 'races_ribbon')]").find_element(By.XPATH, ".//div[contains(@class, 'utils_linkcolor')]") for it in items]
        ad_closed = False
        for i, link in enumerate(links):
            ad_closed = self.handle_ad_banner(driver, ad_closed)
            logging.info(f"Opening race ({i + 1}/{len(links)})")
            link.click(); time.sleep(0.5)

            dialog = driver.find_element(By.XPATH, "//div[@role='dialog']").find_element(By.XPATH, ".//div[contains(@class, 'races_det_wrapper')]")
            infobox = dialog.find_element(By.XPATH, ".//div[contains(@class, 'races_det_infobox')]")
            schedule = dialog.find_element(By.XPATH, ".//div[contains(@class, 'races_det_schedule')]")
            sched_items = schedule.find_elements(By.XPATH, ".//div[contains(@class, 'races_schedule_item')]")

            caps = infobox.find_elements(By.XPATH, ".//div[contains(@class, 'races_det_item_caption')]")
            vals = infobox.find_elements(By.XPATH, ".//div[contains(@class, 'races_det_item__')]")
            info = {c.text.strip(): v.text.strip() for c, v in zip(caps, vals)}

            race = {
                "name": dialog.find_element(By.XPATH, ".//div[contains(@class, 'races_det_header')]").text,
                "date": dialog.find_element(By.XPATH, ".//div[contains(@class, 'races_schedule_header')]").text.replace("\n", " "),
                "grade": info.get("Grade"),
                "terrain": info.get("Terrain"),
                "distanceType": info.get("Distance (type)"),
                "distanceMeters": int(info.get("Distance (meters)")),
                "fans": int(sched_items[-1].text.replace("Fans gained", "").replace("for 1st place", "").replace("See all", "").strip())
            }
            self.data[race["name"]] = race

            driver.find_element(By.XPATH, "//div[contains(@class, 'sc-f83b4a49-1')]").click()
            time.sleep(0.3)

        self.save_data()
        driver.quit()
