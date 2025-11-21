import requests
from bs4 import BeautifulSoup
import time
import random
from config import USER_AGENT_LIST
from utils.logger import setup_logger

logger = setup_logger()

def get_random_header():
    return {
        'User-Agent': random.choice(USER_AGENT_LIST)
    }

def get_wishlist(url):
    """
    Scrapes the Douban user's wishlist and returns a list of movie titles.
    Handles pagination automatically.
    """
    movies = []
    current_url = url
    page_count = 1

    logger.info(f"Starting to scrape wishlist from: {url}")

    while current_url:
        logger.info(f"Scraping page {page_count}...")
        try:
            response = requests.get(current_url, headers=get_random_header(), timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch page: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find grid view items
            items = soup.find_all('div', class_='item')
            if not items:
                logger.warning("No items found on this page. Maybe end of list or layout change.")
                break

            for item in items:
                # Extract title
                # Title is usually in div.info > ul > li.title > a > em
                # Or sometimes just div.info > ul > li.title > a
                title_tag = item.select_one('.info .title a')
                if title_tag:
                    # Get text, remove content like " / Original Title" if needed, 
                    # but usually the first part is the Chinese title which is good for search.
                    # The text might be "Matrix / The Matrix"
                    full_title = title_tag.get_text(strip=True)
                    # Split by / and take the first part (usually Chinese title)
                    title = full_title.split('/')[0].strip()
                    movies.append(title)
            
            # Pagination
            next_link = soup.find('span', class_='next')
            if next_link and next_link.find('a'):
                next_href = next_link.find('a')['href']
                # Handle relative URL
                if not next_href.startswith('http'):
                    # If it's just query params like ?start=15, join with current base or original base
                    # Douban pagination usually keeps the path but changes params.
                    # Safest is to join with the response.url
                    from urllib.parse import urljoin
                    current_url = urljoin(response.url, next_href)
                else:
                    current_url = next_href
                
                page_count += 1
                # Polite delay
                time.sleep(random.uniform(1, 3))
            else:
                current_url = None

        except Exception as e:
            logger.error(f"Error scraping page: {e}")
            break

    logger.info(f"Finished scraping. Found {len(movies)} movies.")
    return movies
