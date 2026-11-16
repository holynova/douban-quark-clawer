"""Search candidates only; no automatic transfer or CAPTCHA bypass."""
import html
import re
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
from modules.library import quark_url


class SearchBlocked(RuntimeError):
    pass


def extract_links(source):
    text = html.unescape(unquote(source))
    candidates = re.findall(r'https?://(?:pan|drive)\.quark\.cn/s/[a-zA-Z0-9]+(?:\?[^\s<>"\']*)?', text)
    return list(dict.fromkeys(u for u in (quark_url(v) for v in candidates) if u))


def search_quark_links(movie_title, driver=None):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    own = driver is None
    if own:
        from utils.driver import get_driver
        driver = get_driver()
    try:
        driver.get('https://www.google.com/search?q=' + quote_plus(f'"{movie_title}" 夸克 site:pan.quark.cn/s/'))
        def ready(d):
            content = d.page_source.lower()
            if '/sorry/' in d.current_url or any(s in content for s in ('unusual traffic', '人机身份验证', 'g-recaptcha')):
                raise SearchBlocked('Google 要求验证；已暂停队列。请在搜索窗口完成验证，再点击继续搜索。')
            return d.find_elements(By.ID, 'search') or d.find_elements(By.ID, 'topstuff')
        try:
            WebDriverWait(driver, 12).until(ready)
        except TimeoutException as exc:
            raise RuntimeError('搜索结果未加载，可能是网络、同意页面或页面结构变化。') from exc
        links = []
        for anchor in driver.find_elements(By.CSS_SELECTOR, '#search a'):
            href = anchor.get_attribute('href') or ''
            p = urlparse(href)
            if p.path == '/url':
                href = parse_qs(p.query).get('q', parse_qs(p.query).get('url', [href]))[0]
            links.extend(extract_links(href))
        for result in driver.find_elements(By.ID, 'search'):
            links.extend(extract_links(result.text))
        return list(dict.fromkeys(links))
    finally:
        if own:
            driver.quit()
