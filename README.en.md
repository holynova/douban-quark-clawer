<p align="right"><a href="README.md">中文</a></p>

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Douban Quark Crawler — a three-step pipeline: Douban wishlist → Google search → quark_links.json">
</p>

<p align="center">
  <a href="https://douban-quark-clawer.xiaosang.cc/">▶ Project Page</a>
  ·
  <a href="https://github.com/holynova/douban-quark-clawer">GitHub Repository</a>
</p>

An automated Python CLI: it reads your Douban 想看 ("Want to Watch") list in bulk, searches Google for Quark cloud drive share links title by title, and saves the results as JSON. The main flow only searches and exports — no Quark login needed.

## How It Works

1. **Scrape the wishlist** — requests + BeautifulSoup fetch a specified Douban user's 想看 ("Want to Watch") list with automatic pagination, saved to `output/wishlist.json`.
2. **Search link by link** — Selenium drives Chrome to Google each title as `"Title" 夸克`, extracts `pan.quark.cn/s/...` share links from the results page with a regex; it pauses 2 seconds between titles and saves intermediate results every 10 titles.
3. **Export JSON** — everything is merged into `output/quark_links.json`, one `{title, quark_links}` entry per title; progress already searched is saved on Ctrl+C or on error too.

## Usage

Requirements: Python 3.8+, Google Chrome (and network access to Google).

```bash
pip install -r requirements.txt
python main.py https://movie.douban.com/people/YOUR_ID/wish
```

After it finishes, find two files in `output/`:

- `wishlist.json` — every title in the wishlist.
- `quark_links.json` — each title and the Quark cloud drive links found for it.

## Notes

- **CAPTCHA**: if you search too fast, Google may show a CAPTCHA; the script pauses and waits for you to solve it manually in the browser (up to 5 minutes), then resumes automatically.
- **Anti-detection**: the browser runs in visible mode by default (not headless), with a random User-Agent and the `navigator.webdriver` flag hidden.
- **Save-to-drive**: `modules/quark_automator.py` provides a Selenium class for Quark login and 转存 ("save to drive"), but it is **not wired into the `main.py` flow** — the main flow only searches and exports links, no saving.

## Tech

- Python + requests / BeautifulSoup (Douban scraping) + Selenium + webdriver-manager (automatic Chrome driver management).
- Link matching: `pan.quark.cn/s/...` or `drive.quark.cn/s/...` (regex in `config.py`).
- Logs go to both the console and `app.log`; `verify_douban.py` / `verify_search.py` are two standalone smoke-test scripts.

```
main.py                   Entry: two-phase flow + progress saving
config.py                 Config: UA list, search suffix, Quark link regex
modules/douban.py         Scrape the Douban wishlist (auto pagination)
modules/search.py         Selenium Google search + Quark link extraction + CAPTCHA wait
modules/quark_automator.py Quark login and save-to-drive class (not wired into the main flow)
utils/driver.py           Chrome driver (anti-detection config)
utils/logger.py           Logging (console + app.log)
verify_*.py               Smoke-test scripts
requirement.md            Original requirements prompt (design doc)
```
