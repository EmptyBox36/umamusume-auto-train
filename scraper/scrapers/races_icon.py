import re
import time
import unicodedata

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base import BaseScraper, create_chromedriver


class RaceIconScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            "https://gametora.com/umamusume/races", "./data/race_icons.json"
        )

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        def close_modal(driver, timeout=5):
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            WebDriverWait(driver, timeout).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )

        def hide_sticky_footer(driver):
            driver.execute_script(
                """
              document.querySelectorAll('[class*="publift-widget-sticky_footer"]').forEach(el=>{
                el.style.setProperty('display','none','important');
                el.style.setProperty('visibility','hidden','important');
                el.style.setProperty('pointer-events','none','important');
              });
            """
            )

        def click_link_safely(driver, el, timeout=5):
            hide_sticky_footer(driver)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(el))
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click()", el)

        def normalize_race_name(name: str) -> str:
            s = unicodedata.normalize("NFKC", name)
            # unify punctuation you see on GameTora
            s = (
                s.replace("’", "'")
                .replace("“", '"')
                .replace("”", '"')
                .replace("–", "-")
                .replace("—", "-")
            )
            # kill filesystem-hostile chars
            s = re.sub(r"[\\/|:*?<>]", "-", s)
            # strip any stray hash or quotes that sneaked in
            s = s.replace("#", "").replace('"', "")
            # collapse whitespace
            s = re.sub(r"\s+", " ", s).strip()
            return s

        races = driver.find_elements(By.XPATH, "//div[contains(@class,'races_row')]")[
            2:-7
        ]
        print(f"Found {len(races)} races")

        for i, row in enumerate(races, start=1):
            try:
                # Get race name
                try:
                    race_name = row.find_element(
                        By.XPATH, ".//div[contains(@class,'races_name')]"
                    ).text.strip()
                except Exception:
                    race_name = row.find_element(
                        By.XPATH, ".//div[contains(@class,'races_desc_right')]/div[1]"
                    ).text.strip()

                race_name = normalize_race_name(race_name)
                # Open modal
                link = row.find_element(
                    By.XPATH, ".//div[contains(@class,'utils_linkcolor')]"
                )
                click_link_safely(driver, link)

                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            "//div[@role='dialog']//div[contains(@class,'races_det_imagerow')]//img",
                        )
                    )
                )

                # Extract image URL only
                img = driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//div[contains(@class,'races_det_imagerow')]//img",
                )
                img_url = img.get_attribute("src")

                print(f"[{i}] {race_name} -> {img_url}")

                # Close modal safely
                close_modal(driver)

                # Save JSON data
                self.data[race_name] = {"id": 10000 + i, "icon_url": img_url}

            except Exception as e:
                print(f"Error [{i}] {e}")

        # Save final JSON file only
        self.save_data()
        driver.quit()
