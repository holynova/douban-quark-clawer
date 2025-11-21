from modules.search import search_quark_links
import sys

def test_search():
    # Use a known movie or take from args
    if len(sys.argv) > 1:
        movie = sys.argv[1]
    else:
        movie = "流浪地球2"
    
    print(f"Testing search for: {movie}")
    links = search_quark_links(movie)
    
    print(f"Found {len(links)} links:")
    for link in links:
        print(f"- {link}")
    
    if len(links) > 0:
        print("Verification SUCCESS")
    else:
        print("Verification FAILED (or no links found, which might be expected)")

if __name__ == "__main__":
    test_search()
