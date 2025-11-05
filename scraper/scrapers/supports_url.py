import re
import time
import logging
from selenium.webdriver.common.by import By

from .base import BaseScraper, create_chromedriver


class SupportCardURLScraper(BaseScraper):
    """
    Scrapes per-card asset URLs from GameTora supports:
      - main card image URL
      - type icon URL
      - rarity icon URL
    Output: data/supports_url.json
    """
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/supports", "supports_url.json")

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
        # Title → character/support name
        raw = driver.find_element(By.CSS_SELECTOR, "h1[class*='utils_headingXl']").text
        name = self._clean_name(raw)

        # Main card image
        card_img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/supports/tex_support_card_']"
        ).get_attribute("src")

        # Type icon (small square icon row)
        type_img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/icons/utx_ico_obtain_']"
        ).get_attribute("src")

        # Rarity icon (“SSR/SR/R” text rendered as image)
        rarity_img = driver.find_element(
            By.CSS_SELECTOR, "img[src*='/icons/utx_txt_rarity_']"
        ).get_attribute("src")

        self.data[name] = {
            "name": name,
            "image_url": card_img,
            "type_url": type_img,
            "rarity_url": rarity_img,
        }

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        links = self._extract_links_from_index(driver)

        for i, link in enumerate(links, start=1):
            logging.info(f"[{i}/{len(links)}] {link}")
            driver.get(link)
            time.sleep(2.5)
            self._scrape_detail(driver)
            if i % 20 == 0:            # tune as needed
                driver.quit()
                driver = create_chromedriver()

        self.save_data()
        driver.quit()
