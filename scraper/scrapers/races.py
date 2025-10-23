import re, time, logging, calendar
from selenium.webdriver.common.by import By
from .base import BaseScraper, create_chromedriver

SPARKS_URL = "https://gametora.com/umamusume/g1-race-factor-list"

def _mon_abbr(m: str) -> str:
    m = m.strip().capitalize()
    try:
        i = list(calendar.month_name).index(m)
        return calendar.month_abbr[i]
    except ValueError:
        return m

def _format_date(header_text: str) -> str:
    # e.g., "Junior Class July, Second Half" -> "Late Jul"
    m = re.search(r"(Junior|Classic|Senior)\s+Class\s+([A-Za-z]+),\s+(First|Second)\s+Half", header_text)
    if not m:
        return header_text
    half = "Early" if m.group(3) == "First" else "Late"
    return f"{half} {_mon_abbr(m.group(2))}"

def _year_bucket(header_text: str) -> str:
    if "Junior Class" in header_text:  return "Junior Year"
    if "Classic Class" in header_text: return "Classic Year"
    return "Senior Year"

class RaceScraper(BaseScraper):
    def __init__(self):
        # write directly in the new schema file name
        super().__init__("https://gametora.com/umamusume/races", "./data/races.json")

    def _load_g1_sparks(self, driver) -> dict[str, list[str]]:
        """Scrape the G1 race factor list once → {race_name: [spark1, spark2]}."""
        driver.get(SPARKS_URL)
        time.sleep(3)

        mapping = {}
        # Each row lists: thumbnail | name | date | surface | type | sparks...
        rows = driver.find_elements(By.XPATH, "//div[contains(@class,'races_row_factors')]")
        if not rows:
            # fallback: list container then item rows
            rows = driver.find_elements(By.XPATH, "//div[contains(@class,'races_race_list')]//div[contains(@class,'races_row')]")

        for r in rows:
            # race name
            try:
                name_el = r.find_element(By.XPATH, ".//div[contains(@class,'races_name') or contains(@class,'races_desc_right')]/div[1]")
                race_name = name_el.text.strip()
                if not race_name:
                    continue
            except Exception:
                continue

            # two sparks in the right-most factor cells; collect visible span texts
            factor_box = None
            try:
                factor_box = r.find_element(By.XPATH, ".//div[contains(@class,'races_factors')]")
            except Exception:
                # fallback: any spans after columns
                pass

            if factor_box:
                chips = factor_box.find_elements(By.XPATH, ".//*[contains(@class,'factor') or self::span]")
                raw = [c.text.strip() for c in chips if c.text.strip()]

                # stable de-dup then cap at two
                seen, uniq = set(), []
                for t in raw:
                    if t not in seen:
                        seen.add(t)
                        uniq.append(t)
                if uniq:
                    mapping[race_name] = uniq[:2]

        logging.info(f"Sparks mapping loaded for {len(mapping)} races.")
        return mapping

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        # Build sparks map once
        sparks_map = self._load_g1_sparks(driver)

        # Return to race list
        driver.get(self.url)
        time.sleep(3)

        race_list = driver.find_element(By.XPATH, "//div[contains(@class,'races_race_list')]")
        items = race_list.find_elements(By.XPATH, ".//div[contains(@class,'races_row')]")
        items = items[2:]     # drop Junior Make Debut/Maiden
        items = items[:-7]    # drop URA/GM/Twinkle end
        logging.info(f"Found {len(items)} races.")

        self.data = {"Junior Year": {}, "Classic Year": {}, "Senior Year": {}}

        links = [
            it.find_element(By.XPATH, ".//div[contains(@class,'races_ribbon')]//div[contains(@class,'utils_linkcolor')]")
            for it in items
        ]

        ad_closed = False
        for i, link in enumerate(links):
            ad_closed = self.handle_ad_banner(driver, ad_closed)
            logging.info(f"Opening race ({i+1}/{len(links)})")
            link.click(); time.sleep(0.5)

            dialog = driver.find_element(By.XPATH, "//div[@role='dialog']//div[contains(@class,'races_det_wrapper')]")
            infobox = dialog.find_element(By.XPATH, ".//div[contains(@class,'races_det_infobox')]")
            schedule = dialog.find_element(By.XPATH, ".//div[contains(@class,'races_det_schedule')]")
            sched_items = schedule.find_elements(By.XPATH, ".//div[contains(@class,'races_schedule_item')]")

            caps = infobox.find_elements(By.XPATH, ".//div[contains(@class,'races_det_item_caption')]")
            vals = infobox.find_elements(By.XPATH, ".//div[contains(@class,'races_det_item__')]")
            info = {c.text.strip(): v.text.strip() for c, v in zip(caps, vals)}

            race_name = dialog.find_element(By.XPATH, ".//div[contains(@class,'races_det_header')]").text.strip()
            date_header = dialog.find_element(By.XPATH, ".//div[contains(@class,'races_schedule_header')]").text.replace("\n", " ").strip()
            grade = info.get("Grade")

            # fans required and gained from the two last schedule items
            fans_required, fans_gained = 0, 0
            if len(sched_items) >= 2:
                t_req = sched_items[-2].text
                t_gained = sched_items[-1].text
                m1 = re.search(r"(\d+)", t_req)
                m2 = re.search(r"(\d+)", t_gained)
                if m1: fans_required = int(m1.group(1))
                if m2: fans_gained = int(m2.group(1))

            payload = {
                "date": _format_date(date_header),
                "racetrack": info.get("Racetrack"),
                "terrain": info.get("Terrain"),
                "distance": {
                    "type": info.get("Distance (type)"),
                    "meters": int(info.get("Distance (meters)"))
                },
                "fans": {"required": fans_required, "gained": fans_gained},
                "grade": grade
            }

            # Only add sparks for G1
            if grade == "G1":
                payload["sparks"] = sparks_map.get(race_name, [])

            headers = dialog.find_elements(By.XPATH, ".//div[contains(@class,'races_schedule_header')]")

            def bucket_from_header(txt: str) -> str:
                if "Junior" in txt:  return "Junior Year"
                if "Classic" in txt: return "Classic Year"
                return "Senior Year"

            for h in headers:
                header_text = h.text.strip().replace("\n", " ")
                bucket = bucket_from_header(header_text)

                # find date just below each header
                try:
                    date_el = h.find_element(By.XPATH, "following-sibling::div[contains(@class,'races_schedule_item')][1]/div[1]")
                    date_text = date_el.text.strip()
                except Exception:
                    date_text = _format_date(header_text)

                payload_copy = payload.copy()
                payload_copy["date"] = _format_date(date_text)

                self.data.setdefault(bucket, {})
                arr = self.data[bucket].setdefault(race_name, [])

                # skip if same date+meters already recorded for this race in this bucket
                if not any(x["date"] == payload_copy["date"] and
                           x["distance"]["meters"] == payload_copy["distance"]["meters"]
                           for x in arr):
                    arr.append(payload_copy)

            def _parse_date_order(t: str) -> int:
                t = (t or "").strip()
                mon = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                       "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
                m = re.search(r"(Early|Late)\s+([A-Za-z]{3})", t)
                if not m:
                    return 999
                half = 0 if m.group(1) == "Early" else 1
                i = mon.get(m.group(2).title(), 99)
                return i * 2 + half

            def sort_races_bucket(bucket_dict: dict, year_label: str) -> dict:
                # year offset to keep Junior < Classic < Senior globally
                yoff = 0 if year_label == "Junior Year" else (1000 if year_label == "Classic Year" else 2000)

                # sort entries of each race, then sort race names by earliest entry
                def entry_key(e):
                    return yoff + _parse_date_order(e.get("date","")) + (e.get("id", 0) / 1e6)

                sorted_bucket = {}
                for rn, entries in bucket_dict.items():
                    se = sorted(entries, key=entry_key)
                    sorted_bucket[rn] = se

                # sort race names by their earliest entry
                return dict(sorted(sorted_bucket.items(),
                                   key=lambda kv: entry_key(kv[1][0]) if kv[1] else 99999))

            # close dialog
            driver.find_element(By.XPATH, "//div[contains(@class,'sc-f83b4a49-1')]").click()
            time.sleep(0.3)

        # sort buckets like GameTora
        sorted_data = {}
        for y in ["Junior Year", "Classic Year", "Senior Year"]:
            if y in self.data:
                sorted_data[y] = sort_races_bucket(self.data[y], y)

        # assign IDs after sorting
        rid = 10001
        for y in ["Junior Year", "Classic Year", "Senior Year"]:
            if y not in sorted_data:
                continue
            for _, entries in sorted_data[y].items():
                for e in entries:
                    e["id"] = rid
                    rid += 1

        self.data = sorted_data
        self.save_data()
        driver.quit()
