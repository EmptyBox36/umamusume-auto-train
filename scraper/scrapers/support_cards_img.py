import os
import re
import time
import json
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

class SupportCardImageScraper:
    ARCHIVE_URL = "https://game8.co/games/Umamusume-Pretty-Derby/archives/535928"
    OUT_DIR = "./data"
    OUTPUT_JSON = "support_card_url.json"

    STAT_SET = {"Speed", "Stamina", "Power", "Guts", "Wit", "Pal"}
    RARITY_SET = {"SSR", "SR", "R"}

    ALLOWED_RARITIES = {"SSR", "SR"}
    RARITY_ORDER = {
        "SSR": 0,
        "SR": 1,
        "R": 2,
    }

    def start(self):
        os.makedirs(self.OUT_DIR, exist_ok=True)
        out_path = os.path.join(self.OUT_DIR, self.OUTPUT_JSON)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.ARCHIVE_URL, wait_until="networkidle")

            self._ensure_all_cards_loaded(page)

            if not self._open_first_card_modal(page):
                raise RuntimeError("Could not open any card modal")

            seen_keys = set()
            results = []

            while True:
                info = self._scrape_current_modal(page)
                if not info:
                    break

                if info["rarity"] not in self.ALLOWED_RARITIES:
                    if not self._click_next(page):
                        break
                    continue

                record = {
                    "name": info["title"],
                    "character": info["character"],
                    "type": info["stat"],
                    "rarity": info["rarity"],
                    "image_url": info["img_url"],
                }

                # Dedup
                key = self._dedup_key(record)
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(record)
                    print(f"[OK] {record['name']} ({record['character']}) ({record['type']}) ({record['rarity']})")

                if not self._click_next(page):
                    break

            browser.close()

        results.sort(
            key=lambda r: (
                self.RARITY_ORDER.get(r["rarity"], 99),
                r["name"].lower(),
            )
        )

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(results)} records to: {out_path}")

    def _dedup_key(self, record: dict) -> str:
        # stable dedup key; avoids duplicates from modal navigation quirks
        return f"{record['name']}|{record['character']}|{record['type']}|{record['rarity']}|{record['image_url']}"

    def _parse_modal_name(self, raw: str) -> Tuple[str, str]:
        m = re.match(r"^(.*?)\s*\((.*?)\)$", raw)
        if m:
            return m.group(2), m.group(1)
        return raw, "Unknown"

    def _scrape_current_modal(self, page) -> Optional[dict]:
        modal = page.locator("div[class*='modalContent']").first
        try:
            modal.wait_for(state="visible", timeout=2000)
        except PWTimeoutError:
            return None

        img_url = modal.locator("img[class*='modalImage']").first.get_attribute("src")
        raw_name = modal.locator("div[class*='modalName']").first.inner_text().strip()
        title, character = self._parse_modal_name(raw_name)

        tags = modal.locator("span[class*='iconWithTextText']").all_inner_texts()
        stat = next((t for t in tags if t in self.STAT_SET), "Unknown")
        rarity = next((t for t in tags if t in self.RARITY_SET), "Unknown")

        return {
            "img_url": img_url,
            "title": title,
            "character": character,
            "stat": stat,
            "rarity": rarity,
        }

    def _ensure_all_cards_loaded(self, page):
        last = 0
        for _ in range(60):
            page.mouse.wheel(0, 2000)
            time.sleep(0.4)
            h = page.evaluate("document.body.scrollHeight")
            if h == last:
                return
            last = h

    def _open_first_card_modal(self, page) -> bool:
        thumbs = page.locator("img[src*='img.game8.jp']").filter(
            has_not=page.locator("img[class*='modalImage']")
        )
        for i in range(min(30, thumbs.count())):
            try:
                thumbs.nth(i).click()
                page.locator("div[class*='modalContent']").first.wait_for(state="visible", timeout=2000)
                return True
            except Exception:
                pass
        return False

    def _click_next(self, page) -> bool:
        try:
            btn = page.locator("button[aria-label='Next item']").first
            if btn.is_visible():
                btn.click()
                time.sleep(0.2)
                return True
        except Exception:
            pass
        return False