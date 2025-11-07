import re
import time
import logging
from selenium.webdriver.common.by import By
from requests.exceptions import ReadTimeout as RequestsReadTimeout
from selenium.common.exceptions import TimeoutException, WebDriverException

from .base import BaseScraper, create_chromedriver

def _go(driver, url, tries=2):
    for attempt in range(tries):
        try:
            driver.get(url)
            return True
        except (TimeoutException, WebDriverException):
            # try to stop the page if still loading
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
        except RequestsReadTimeout:
            # UC sometimes surfaces the CDP stall as a requests.ReadTimeout
            pass
    return False

class SupportCardURLScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/supports", "supports_url.json")
        self.data = []  # list output like skills.py

    def _clean_name(self, raw: str) -> str:
        # Example raw: "Silence Suzuka (SSR) Support Card"
        name = raw.replace("Support Card", "")
        name = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
        return name

    def _extract_links_from_index(self, driver) -> list[str]:
        # Grid of support cards → each visible card has a parent <a href="...">
        grid = driver.find_element(By.XPATH, "//div[contains(@class,'sc-70f2d7f-0')]")
        items = grid.find_elements(By.XPATH, ".//div[contains(@class,'sc-73e3e686-3')]")
        items = [it for it in items if it.is_displayed()]
        logging.info(f"Found {len(items)} support cards on index.")
        links = []
        for it in items:
            try:
                a = it.find_element(By.XPATH, "./parent::a")
                links.append(a.get_attribute("href"))
            except Exception:
                # Fallback: look for nearest ancestor link
                a = it.find_element(By.XPATH, "./ancestor::a[1]")
                links.append(a.get_attribute("href"))
        return links

    def _scrape_detail(self, driver):
        raw = driver.find_element(By.CSS_SELECTOR, "h1[class*='utils_headingXl']").text
        name = self._clean_name(raw)

        card_img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/supports/tex_support_card_']"
        ).get_attribute("src")

        type_img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/icons/utx_ico_obtain_']"
        ).get_attribute("src")

        rarity_img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/icons/utx_txt_rarity_']"
        ).get_attribute("src")

        return {
            "name": name,
            "image_url": card_img,
            "type_url": type_img,
            "rarity_url": rarity_img,
        }

    def start(self):
        driver = create_chromedriver()
        if not _go(driver, self.url):
            driver.quit(); return
        time.sleep(2)
        self.handle_cookie_consent(driver)

        links = self._extract_links_from_index(driver)
        ad_banner_closed = False
        result = []  # collect list like skills.py

        for i, link in enumerate(links, start=1):
            ad_banner_closed = self.handle_ad_banner(driver, ad_banner_closed)
            logging.info(f"[{i}/{len(links)}] {link}")

            if not _go(driver, link):
                logging.warning(f"Failed to load {link}; restarting driver...")
                driver.quit()
                driver = create_chromedriver()
                if not _go(driver, self.url):
                    logging.warning("Reopen index failed; skipping link."); continue
                time.sleep(1)
                self.handle_cookie_consent(driver)
                ad_banner_closed = False
                if not _go(driver, link):
                    logging.warning(f"Still cannot load {link}, skipping."); continue

            time.sleep(2)
            item = self._scrape_detail(driver)
            if item:  # optional de-dup by name if needed
                result.append(item)

            if i % 12 == 0:
                driver.quit()
                driver = create_chromedriver()
                _ = _go(driver, self.url)
                time.sleep(1); self.handle_cookie_consent(driver); ad_banner_closed = False

        self.data = result
        self.save_data()
        driver.quit()