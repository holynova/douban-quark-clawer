from modules.douban import get_wishlist
import sys

def test_douban():
    # Use a known public wishlist or take from args
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default to Ah Bei's wishlist (public)
        url = "https://movie.douban.com/people/ahbei/wish"
    
    print(f"Testing scraper with URL: {url}")
    movies = get_wishlist(url)
    
    print(f"Found {len(movies)} movies:")
    for m in movies[:10]:
        print(f"- {m}")
    
    if len(movies) > 0:
        print("Verification SUCCESS")
    else:
        print("Verification FAILED (or empty list)")

if __name__ == "__main__":
    test_douban()
