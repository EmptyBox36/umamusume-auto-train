import time, re, logging
from selenium.webdriver.common.by import By

from .base import BaseScraper, create_chromedriver

def _go(driver, url, tries=2):
    for attempt in range(1, tries + 1):
        try:
            driver.get(url)
            return True

        except Exception as e:
            msg = str(e)
            logging.error(f"_go error on attempt {attempt}/{tries}: {msg}")

            # Detect broken chrome/CDP session
            if "HTTPConnectionPool" in msg or "Read timed out" in msg or "Repeated tooltip title detected" in msg:
                return "RESTART"

            # Normal retry
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
            time.sleep(2)

    return False

def load_with_retry(driver, url: str, max_retry: int = 3, delay: float = 10.0):
    for attempt in range(1, max_retry + 1):
        try:
            driver.get(url)
            return True  # success
        except Exception as e:
            logging.error(f"Load failed ({attempt}/{max_retry}) for {url}: {e}")
            time.sleep(delay)
    return False

class SupportCardScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://gametora.com/umamusume/supports", "supports.json")

    def start(self):
        driver = create_chromedriver()
        driver.get(self.url)
        time.sleep(5)
        self.handle_cookie_consent(driver)

        grid = driver.find_element(By.XPATH, "//div[contains(@class, 'sc-70f2d7f-0')]")
        items = grid.find_elements(By.XPATH, ".//div[contains(@class, 'sc-73e3e686-3')]")
        items = [it for it in items if it.is_displayed()]
        logging.info(f"Found {len(items)} support cards.")
        links = [it.find_element(By.XPATH, "./..").get_attribute("href") for it in items]

        for i, link in enumerate(links):
            max_link_retry = 3
            attempt = 0

            while attempt < max_link_retry:
                try:
                    # Periodic full restart (keep your existing every-5-cards behavior)
                    if i % 5 == 0:
                        driver.quit()
                        driver = create_chromedriver()
                        _ = _go(driver, self.url)
                        time.sleep(1)

                    logging.info(f"Navigating to {link} ({i + 1}/{len(links)})")

                    result = _go(driver, link, tries=2)

                    if result == "RESTART":
                        logging.warning("Restarting Chrome due to connection failure...")
                        driver.quit()
                        driver = create_chromedriver()
                        _ = _go(driver, self.url)
                        time.sleep(1)
                        # retry the SAME link again
                        if _go(driver, link, tries=2) is not True:
                            if not load_with_retry(driver, link, max_retry=5, delay=10):
                                raise RuntimeError(f"Could not load {link} after Chrome restart")
                    elif result is False:
                        logging.warning("Normal _go failure, trying extended retries...")
                        if not load_with_retry(driver, link, max_retry=5, delay=10):
                            raise RuntimeError(f"Could not load {link}")

                    time.sleep(3)

                    raw = driver.find_element(
                        By.XPATH,
                        "//h1[contains(@class, 'utils_headingXl')]"
                    ).text
                    name = re.sub(r'\s*\(.*?\)', '', raw.replace("Support Card", "")).strip()

                    temp_dict = {}
                    self.process_training_events(driver, name, temp_dict)
                    self.data.update(temp_dict)

                    # success: break retry loop for this link
                    break

                except Exception as e:
                    msg = str(e)
                    attempt += 1
                    logging.error(
                        f"Error while processing {link} ({i + 1}/{len(links)}), "
                        f"attempt {attempt}/{max_link_retry}: {msg}"
                    )

                    # If Chrome/CDP is broken, restart driver and retry this support
                    if "HTTPConnectionPool" in msg or "Read timed out" in msg or "Repeated tooltip title detected" in msg:
                        driver.quit()
                        driver = create_chromedriver()
                        _ = _go(driver, self.url)
                        time.sleep(2)
                        # continue to next attempt of same link
                        continue

                    # Other unexpected errors: re-raise immediately
                    raise

            else:
                # while exhausted without break
                raise RuntimeError(f"Could not process {link} after {max_link_retry} attempts")

        self.save_data()
        driver.quit()