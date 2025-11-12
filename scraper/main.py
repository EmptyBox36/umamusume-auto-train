import time, logging
import argparse

from scrapers.skills import SkillScraper
from scrapers.characters import CharacterScraper
from scrapers.supports import SupportCardScraper
from scrapers.races import RaceScraper
from scrapers.races_icon import RaceIconScraper

scrapers = {
    "skills": [SkillScraper],
    "characters": [CharacterScraper],
    "supports": [SupportCardScraper],
    "races": [RaceScraper],
    "races_icon": [RaceIconScraper],
}

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scraper",
        choices=list(scrapers.keys()),
        nargs="?",                # argument is optional
        help="Which scraper to run"
    )
    args = parser.parse_args()

    def run_with_retry(cls, retries=3, delay=10):
        for attempt in range(1, retries + 1):
            try:
                cls().start()
                return
            except Exception as e:
                logging.error(f"{cls.__name__} failed (attempt {attempt}/{retries}): {e}")
                if attempt < retries:
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error(f"{cls.__name__} permanently failed after {retries} attempts.")

    if args.scraper:
        for scraper_class in scrapers[args.scraper]:
            run_with_retry(scraper_class)
    else:
        for cls in [CharacterScraper, SupportCardScraper]:
            run_with_retry(cls)

    end_time = round(time.time() - start_time, 2)
    logging.info(f"Total time for processing all applications: {end_time} seconds or {round(end_time / 60, 2)} minutes.")
