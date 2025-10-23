import os
import re
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from .base import BaseScraper, create_chromedriver

class RaceIconScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            "https://gametora.com/umamusume/races",
            "./data/race_icons.json"
        )
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.icon_dir = os.path.join(base_dir, "icons")
        os.makedirs(self.icon_dir, exist_ok=True)

    def download_icon(self, url: str, name: str):
        safe = re.sub(r'[<>:"/\\|?*]', "", name).strip().rstrip(".")
        ext = os.path.splitext(url)[1] or ".png"
        path = os.path.join(self.icon_dir, f"{safe}{ext}")
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
        print(f"Failed to download {name}: HTTP {r.status_code}")
        return None

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        def close_modal(driver, timeout=5):
            # press ESC to close
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            # wait until dialog is gone
            WebDriverWait(driver, timeout).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )

        def hide_sticky_footer(driver):
            driver.execute_script("""
              document.querySelectorAll('[class*="publift-widget-sticky_footer"]').forEach(el=>{
                el.style.setProperty('display','none','important');
                el.style.setProperty('visibility','hidden','important');
                el.style.setProperty('pointer-events','none','important');
              });
            """)

        def click_link_safely(driver, el, timeout=5):
            hide_sticky_footer(driver)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(el))
                el.click()
            except Exception:
                # fallback to JS click
                driver.execute_script("arguments[0].click()", el)

        races = driver.find_elements(By.XPATH, "//div[contains(@class,'races_row')]")[2:-7]
        print(f"Found {len(races)} races")

        for i, row in enumerate(races, start=1):
            try:
                # 1) correct race name selector (fallback if needed)
                try:
                    race_name = row.find_element(By.XPATH, ".//div[contains(@class,'races_name')]").text.strip()
                except Exception:
                    race_name = row.find_element(By.XPATH, ".//div[contains(@class,'races_desc_right')]/div[1]").text.strip()

                # open modal
                link = row.find_element(By.XPATH, ".//div[contains(@class,'utils_linkcolor')]")
                click_link_safely(driver, link)                       # <-- replace raw .click()

                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@class,'races_det_imagerow')]//img"))
                )

                # image url
                img = driver.find_element(By.XPATH, "//div[@role='dialog']//div[contains(@class,'races_det_imagerow')]//img")
                img_url = img.get_attribute("src")

                file_path = self.download_icon(img_url, race_name)
                if file_path:
                    print(f"[{i}] {race_name} -> {file_path}")
                else:
                    print(f"[{i}] Failed to download {race_name}")

                # close modal safely
                close_modal(driver)

                self.data[race_name] = {"id": 10000 + i,"icon_url": img_url,}

            except Exception as e:
                print(f"Error [{i}] {e}")

        self.save_data()
        driver.quit()
