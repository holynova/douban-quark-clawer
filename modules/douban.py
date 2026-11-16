"""Bounded import: blocked pages are never treated as empty watchlists."""
import re
import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from config import USER_AGENT_LIST


def validate_wishlist_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.netloc != 'movie.douban.com' or not re.fullmatch(r'/people/[\w.-]+/wish/?', p.path):
        raise ValueError('请输入 https://movie.douban.com/people/用户ID/wish 格式的地址。')
    return url


def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    if any(word in soup.get_text(' ', strip=True) for word in ('异常请求', '访问异常', '安全验证', '验证码')):
        raise RuntimeError('豆瓣要求验证。请在浏览器中处理，或使用片名 / JSON 导入。')
    items = []
    for item in soup.select('div.item'):
        title = item.select_one('.info .title a')
        if not title:
            continue
        intro = item.select_one('.intro')
        year = re.search(r'\b(?:19|20)\d{2}\b', intro.get_text() if intro else '')
        items.append({'title': title.get_text(' ', strip=True).split('/')[0].strip(),
                      'douban_url': title.get('href', ''), 'year': year.group() if year else ''})
    if not items and not soup.select_one('.grid-view'):
        raise RuntimeError('未识别到公开想看片单，可能需要登录或页面结构已变化。')
    link = soup.select_one('span.next a')
    return items, link.get('href') if link else None


def get_wishlist_items(url, limit=300, on_page=None, stopped=None):
    current = validate_wishlist_url(url)
    visited, items = set(), []
    session = requests.Session()
    try:
        while current and len(items) < limit:
            if stopped and stopped():
                break
            validate_wishlist_url(current)
            if current in visited:
                raise RuntimeError('豆瓣分页重复，已停止以避免无限抓取。')
            visited.add(current)
            response = session.get(current, headers={'User-Agent': USER_AGENT_LIST[0]}, timeout=12, allow_redirects=False)
            if response.status_code != 200:
                raise RuntimeError(f'豆瓣返回 HTTP {response.status_code}，请检查片单是否公开或改用文件导入。')
            batch, next_href = parse_page(response.text)
            batch = batch[:limit - len(items)]
            items.extend(batch)
            if on_page and batch:
                on_page(batch)
            current = urljoin(current, next_href) if next_href else None
            if current and len(items) < limit:
                for _ in range(15):
                    if stopped and stopped():
                        return items
                    time.sleep(.1)
        return items
    finally:
        session.close()


def get_wishlist(url):
    return [item['title'] for item in get_wishlist_items(url)]
