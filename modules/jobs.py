"""Single task queue, saved after every completed item."""
import threading
from modules.douban import get_wishlist_items, validate_wishlist_url
from modules.search import search_quark_links, SearchBlocked
from utils.driver import get_driver


class Jobs:
    def __init__(self, library, search=search_quark_links, driver_factory=get_driver):
        self.library, self.search, self.driver_factory = library, search, driver_factory
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread = None
        self.driver = None
        self.state = {'active': False, 'kind': '', 'message': '准备就绪', 'done': 0, 'total': 0}

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def _set(self, **values):
        with self.lock:
            self.state.update(values)

    def start(self, kind, url='', limit=300):
        with self.lock:
            if self.state['active']:
                raise ValueError('已有任务运行中，请先暂停。')
            if kind == 'import':
                validate_wishlist_url(url)
            elif kind not in ('search', 'retry'):
                raise ValueError('未知任务。')
            self.stop.clear()
            statuses = ('error', 'blocked', 'empty') if kind == 'retry' else ('pending', 'error', 'blocked')
            items = [i for i in self.library.snapshot()['items'] if i['status'] in statuses]
            if kind != 'import' and not items:
                raise ValueError('没有待搜索影片。可以导入片单，或重试未找到的影片。')
            self._set(active=True, kind=kind, message='正在准备…', done=0, total=len(items))
            self.thread = threading.Thread(target=self._run, args=(kind, url, limit, items), daemon=True)
            self.thread.start()

    def pause(self):
        self.stop.set()
        self._set(message='正在暂停，当前请求结束后保存…')

    def _run(self, kind, url, limit, items):
        blocked = False
        try:
            if kind == 'import':
                def page(batch):
                    added = self.library.merge(batch)
                    state = self.snapshot()
                    self._set(done=state['done'] + len(batch), message=f'已读取 {state["done"] + len(batch)} 部，本页新增 {added} 部')
                result = get_wishlist_items(url, limit, on_page=page, stopped=self.stop.is_set)
                message = f'导入完成：读取 {len(result)} 部影片' + ('，已达到本次上限' if len(result) == limit else '')
            else:
                if self.driver is None:
                    self.driver = self.driver_factory()
                errors = 0
                for index, item in enumerate(items):
                    if self.stop.is_set():
                        break
                    self._set(message=f'正在搜索 · {item["title"]}')
                    try:
                        links = self.search(item['title'], driver=self.driver)
                        self.library.update(item['id'], quark_links=links, status='found' if links else 'empty', error='')
                    except SearchBlocked as exc:
                        self.library.update(item['id'], status='blocked', error=str(exc))
                        self._set(message=str(exc))
                        blocked = True
                        break
                    except Exception as exc:
                        errors += 1
                        self.library.update(item['id'], status='error', error=str(exc)[:500])
                    self._set(done=index + 1)
                    if index + 1 < len(items) and self.stop.wait(2):
                        break
                message = f'搜索结束，{errors} 部失败可重试' if errors else '本轮搜索完成，结果已保存'
            if not blocked:
                self._set(message='已暂停，进度已保存' if self.stop.is_set() else message)
        except Exception as exc:
            self._set(message=f'任务未完成：{exc}')
        finally:
            if not blocked and self.driver is not None:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            self._set(active=False)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
