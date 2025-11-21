from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import urllib.parse
from config import SEARCH_ENGINE_URL, SEARCH_SUFFIX, QUARK_SHARE_URL_PATTERN
from utils.logger import setup_logger

logger = setup_logger()

def search_quark_links(movie_title, driver=None):
    """
    Searches for Quark Cloud Drive links for a given movie title using Selenium.
    Returns a list of unique Quark URLs found.
    """
    should_close_driver = False
    if driver is None:
        from utils.driver import get_driver
        driver = get_driver(headless=False) # Use non-headless to be safer against bot detection
        should_close_driver = True

    query = f'"{movie_title}"{SEARCH_SUFFIX}'
    logger.info(f"Searching for: {query}")
    
    quark_links = set()

    try:
        driver.get(SEARCH_ENGINE_URL)
        
        # Find search box
        # Google's search box name is usually 'q'
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.submit()
        
        # Wait for results or CAPTCHA
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
        except Exception:
            # If search results didn't appear quickly, check for CAPTCHA
            logger.warning("Search results not found immediately. Checking for CAPTCHA...")
            
            is_captcha = False
            try:
                # Check for common CAPTCHA indicators
                if "recaptcha" in driver.page_source.lower() or "unusual traffic" in driver.page_source.lower() or "人机身份验证" in driver.page_source:
                    is_captcha = True
            except:
                pass
            
            if is_captcha:
                logger.warning("!!!" * 10)
                logger.warning("CAPTCHA DETECTED! Please solve the CAPTCHA in the browser window manually.")
                logger.warning("The script is paused and waiting for you to solve it...")
                logger.warning("!!!" * 10)
                
                # Wait up to 5 minutes for the user to solve it
                try:
                    WebDriverWait(driver, 300).until(
                        EC.presence_of_element_located((By.ID, "search"))
                    )
                    logger.info("CAPTCHA solved! Resuming...")
                except Exception:
                    logger.error("Timeout waiting for CAPTCHA solution.")
                    return []
            else:
                logger.warning("Search results failed to load (and no obvious CAPTCHA detected).")
                return []
        
        # Give it a moment to fully render
        time.sleep(2)
        
        # Extract links
        # Method 1: Check all 'a' tags in the result area
        links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in links:
            try:
                href = link.get_attribute("href")
                if not href:
                    continue
                    
                # Extract real URL from Google's redirection if present
                if "/url?q=" in href:
                    parsed = urllib.parse.urlparse(href)
                    query_params = urllib.parse.parse_qs(parsed.query)
                    if 'q' in query_params:
                        href = query_params['q'][0]
                
                # Check against regex
                match = re.search(QUARK_SHARE_URL_PATTERN, href)
                if match:
                    quark_links.add(match.group(1))
            except Exception:
                continue # Stale element or other issue
        
        # Method 2: Check body text for non-clickable links (optional, but Selenium makes it easy to get page source)
        page_source = driver.page_source
        text_matches = re.findall(QUARK_SHARE_URL_PATTERN, page_source)
        for match in text_matches:
            if isinstance(match, tuple):
                quark_links.add(match[0])
            else:
                quark_links.add(match)

    except Exception as e:
        logger.error(f"Error during search: {e}")
        # Save screenshot for debug
        try:
            driver.save_screenshot("debug_search_error.png")
        except:
            pass

    finally:
        if should_close_driver:
            driver.quit()

    found_links = list(quark_links)
    if found_links:
        logger.info(f"Found {len(found_links)} Quark links for '{movie_title}'")
    else:
        logger.info(f"No Quark links found for '{movie_title}'")
        
    return found_links
