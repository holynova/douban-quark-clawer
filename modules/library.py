"""Persistent watchlist; all writes use atomic replacement."""
import copy
import hashlib
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode


def now():
    return datetime.now(timezone.utc).isoformat()


def quark_url(value):
    if not isinstance(value, str):
        return None
    p = urlparse(value.strip())
    if p.scheme not in ('http', 'https') or p.netloc not in ('pan.quark.cn', 'drive.quark.cn'):
        return None
    if not re.fullmatch(r'/s/[a-zA-Z0-9]+/?', p.path):
        return None
    query = parse_qs(p.query)
    code = {k: query[k][0] for k in ('pwd', 'passcode') if k in query}
    return 'https://' + p.netloc + p.path.rstrip('/') + ('?' + urlencode(code) if code else '')


def normalize(data):
    if isinstance(data, dict):
        data = data.get('items')
    if not isinstance(data, list) or not data or len(data) > 5000:
        raise ValueError('请导入包含 1–5000 部影片的数组或工作台 JSON。')
    items = []
    for raw in data:
        raw = {'title': raw} if isinstance(raw, str) else raw
        if not isinstance(raw, dict) or not isinstance(raw.get('title'), str) or not raw['title'].strip():
            raise ValueError('每部影片都需要非空的 title。')
        title = raw['title'].strip()[:300]
        subject = str(raw.get('douban_url', ''))
        if not re.fullmatch(r'https://movie\.douban\.com/subject/\d+/?', subject):
            subject = ''
        key = subject or title.casefold()
        links_raw = raw.get('quark_links', [])
        if not isinstance(links_raw, list):
            raise ValueError('quark_links 必须是链接数组。')
        links = list(dict.fromkeys(u for u in (quark_url(v) for v in links_raw) if u))
        status = raw.get('status', 'pending')
        if status not in ('pending', 'found', 'empty', 'error', 'blocked'):
            status = 'pending'
        status = 'found' if links else ('pending' if status == 'found' else status)
        items.append({'id': hashlib.sha256(key.encode()).hexdigest()[:16], 'title': title,
                      'douban_url': subject, 'year': str(raw.get('year', ''))[:10],
                      'quark_links': links, 'status': status,
                      'note': str(raw.get('note', ''))[:2000],
                      'error': str(raw.get('error', ''))[:500], 'updated_at': raw.get('updated_at') or now()})
    return items


class Library:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.data = {'version': 2, 'items': []}
        if self.path.exists():
            source = json.loads(self.path.read_text(encoding='utf-8'))
            if source.get('items'):
                self.data['items'] = normalize(source)

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.data)

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)

    def merge(self, data):
        incoming = normalize(data)
        with self.lock:
            existing = {i['id']: i for i in self.data['items']}
            count = 0
            for item in incoming:
                if item['id'] in existing:
                    old = existing[item['id']]
                    old['quark_links'] = list(dict.fromkeys(old['quark_links'] + item['quark_links']))
                    if old['quark_links']:
                        old['status'] = 'found'
                    if not old['note']:
                        old['note'] = item['note']
                else:
                    self.data['items'].append(item)
                    existing[item['id']] = item
                    count += 1
            self._save()
            return count

    def update(self, item_id, **values):
        with self.lock:
            item = next((i for i in self.data['items'] if i['id'] == item_id), None)
            if item is None:
                raise ValueError('找不到这部影片。')
            item.update(values, updated_at=now())
            self._save()

    def delete(self, item_id):
        with self.lock:
            self.data['items'] = [i for i in self.data['items'] if i['id'] != item_id]
            self._save()
