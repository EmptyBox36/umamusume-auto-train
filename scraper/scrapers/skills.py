import time
import re
import logging

from .base_pw import BaseScraperPW, create_pw, close_pw


class SkillScraper(BaseScraperPW):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/skills", "./data/skills.json")

    def start(self):
        pw, browser, context, page = create_pw(headless=True)
        try:
            page.goto(self.url, wait_until="domcontentloaded")
            time.sleep(3)
            self.handle_cookie_consent(page)

            # Expand filters
            page.locator(
                "xpath=//div[contains(@class, 'utils_padbottom_half')]"
                "//button[contains(@class, 'filters_button_moreless')]"
            ).first.click()
            time.sleep(0.1)

            # Show ID
            page.locator("xpath=//input[contains(@id, 'showIdCheckbox')]").first.click()
            time.sleep(0.1)

            # Show unique char
            page.locator("xpath=//input[contains(@id, 'showUniqueCharCheckbox')]").first.click()
            time.sleep(0.1)

            rows = page.locator("xpath=//div[contains(@class, 'skills_table_row_ja')]")
            n = rows.count()
            logging.info(f"Found {n} non-hidden and hidden skill rows.")

            result = []
            for i in range(n):
                row = rows.nth(i)
                name = row.locator("xpath=.//div[contains(@class, 'skills_table_jpname')]").first.inner_text().strip()
                desc = row.locator("xpath=.//div[contains(@class, 'skills_table_desc')]").first.inner_text().strip()

                m = re.search(r"\((\d+)\)$", desc)
                sid = int(m.group(1)) if m else None
                clean = re.sub(r"\s*\(\d+\)$", "", desc) if m else desc

                if name:
                    result.append({"id": sid, "name": name, "description": clean})
                    logging.info(f"Scraped skill ({i + 1}/{n}): {name}")

            self.data = result
            self.save_data()

        finally:
            try:
                context.close()
            except Exception:
                pass
            close_pw(pw, browser)