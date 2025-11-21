import sys
import time
import json
import os
from utils.logger import setup_logger
from utils.driver import get_driver
from modules.douban import get_wishlist
from modules.search import search_quark_links

logger = setup_logger()

def ensure_output_dir():
    if not os.path.exists("output"):
        os.makedirs("output")

def save_to_json(data, filename):
    filepath = os.path.join("output", filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Saved data to {filepath}")

def main():
    logger.info("Starting Douban Quark Crawler...")
    
    if len(sys.argv) < 2:
        logger.error("Usage: python main.py <douban_user_wishlist_url>")
        print("Example: python main.py https://movie.douban.com/people/your_id/wish")
        sys.exit(1)
    
    user_url = sys.argv[1]
    logger.info(f"Target User URL: {user_url}")

    ensure_output_dir()

    # Phase 1: Get Wishlist
    movies = get_wishlist(user_url)
    if not movies:
        logger.error("No movies found or failed to scrape wishlist.")
        sys.exit(1)
        
    logger.info(f"Found {len(movies)} movies in wishlist.")
    
    # Save Wishlist to JSON
    save_to_json(movies, "wishlist.json")

    # Initialize Driver
    logger.info("Initializing Browser for Search...")
    driver = get_driver(headless=False) # Keep visible to avoid some bot detection, or switch to True if preferred
    
    try:
        # Phase 2: Search Loop
        results = []
        
        for i, movie in enumerate(movies):
            logger.info(f"[{i+1}/{len(movies)}] Searching: {movie}")
            
            # Search
            links = search_quark_links(movie, driver=driver)
            
            movie_result = {
                "title": movie,
                "quark_links": links
            }
            results.append(movie_result)
            
            if links:
                logger.info(f"Found {len(links)} links for {movie}")
            else:
                logger.warning(f"No links found for {movie}")
            
            # Save intermediate results periodically (optional, but good for long runs)
            if (i + 1) % 10 == 0:
                save_to_json(results, "quark_links_partial.json")
            
            # Polite delay between movies
            time.sleep(2)

        # Final Save
        save_to_json(results, "quark_links.json")
        
        # Clean up partial file
        if os.path.exists(os.path.join("output", "quark_links_partial.json")):
            os.remove(os.path.join("output", "quark_links_partial.json"))

        logger.info("="*30)
        logger.info("All tasks completed.")
        logger.info(f"Total Movies Processed: {len(movies)}")
        logger.info(f"Results saved to output/quark_links.json")
        logger.info("="*30)

    except KeyboardInterrupt:
        logger.warning("User interrupted the process. Saving current progress...")
        save_to_json(results, "quark_links_interrupted.json")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if 'results' in locals():
            save_to_json(results, "quark_links_error.json")
    finally:
        logger.info("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()
