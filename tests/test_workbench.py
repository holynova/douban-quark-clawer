import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from modules.library import Library, normalize, quark_url
from modules.douban import parse_page, get_wishlist_items, validate_wishlist_url
from modules.search import extract_links, SearchBlocked
from modules.jobs import Jobs
from server import make_handler

PAGE = '''<div class="grid-view"><div class="item"><div class="info"><li class="title"><a href="https://movie.douban.com/subject/1295644/">这个杀手不太冷 / Léon</a></li><li class="intro">1994-09-14 / 法国</li></div></div></div>'''


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'library.json'
        self.lib = Library(self.path)

    def test_legacy_import_dedup_and_persistence(self):
        self.assertEqual(self.lib.merge(['重庆森林', '重庆森林']), 1)
        item = self.lib.snapshot()['items'][0]
        self.lib.update(item['id'], note='一起看')
        self.lib.merge([{'title':'重庆森林', 'quark_links':['https://pan.quark.cn/s/Abc?pwd=1234']}])
        restored = Library(self.path).snapshot()['items'][0]
        self.assertEqual(restored['note'], '一起看')
        self.assertEqual(restored['status'], 'found')
        self.assertIn('pwd=1234', restored['quark_links'][0])

    def test_invalid_import_does_not_partially_write(self):
        with self.assertRaises(ValueError):
            self.lib.merge(['good', {'title':None}])
        self.assertEqual(self.lib.snapshot()['items'], [])
        self.assertFalse(self.path.exists())

    def test_remove_persists_and_preserves_other_items(self):
        self.lib.merge(['A', 'B'])
        self.lib.delete(self.lib.snapshot()['items'][0]['id'])
        self.assertEqual([i['title'] for i in Library(self.path).snapshot()['items']], ['B'])

    def test_share_validation_and_query_preservation(self):
        self.assertIsNone(quark_url('https://pan.quark.cn.evil.com/s/a'))
        self.assertIsNone(quark_url('javascript:alert(1)'))
        self.assertIsNone(quark_url('https://pan.quark.cn@evil.com/s/a'))
        self.assertEqual(quark_url('http://pan.quark.cn/s/abc?utm=bad&pwd=hello'), 'https://pan.quark.cn/s/abc?pwd=hello')

    def test_restart_requeues_unfinished(self):
        self.lib.merge([{'title':'A','status':'searching'}, {'title':'B','status':'found'}])
        self.assertTrue(all(i['status']=='pending' for i in Library(self.path).snapshot()['items']))

    def test_extract_google_encoded_url(self):
        self.assertEqual(extract_links('https%3A%2F%2Fpan.quark.cn%2Fs%2Fabc%3Fpwd%3D1234'), ['https://pan.quark.cn/s/abc?pwd=1234'])

    def test_pause_and_resume_skip_completed(self):
        self.lib.merge(['A','B'])
        calls=[]
        driver=Mock()
        job=None
        def search(title, **_):
            calls.append(title)
            if title=='A':job.pause()
            return ['https://pan.quark.cn/s/'+title]
        job=Jobs(self.lib, search=search, driver_factory=lambda:driver)
        job.start('search');job.thread.join(3)
        self.assertFalse(job.snapshot()['active'])
        self.assertEqual(calls,['A'])
        job.start('search');job.thread.join(3)
        self.assertEqual(calls,['A','B'])
        self.assertTrue(all(i['status']=='found' for i in self.lib.snapshot()['items']))

    def test_blocked_keeps_browser_and_can_retry(self):
        self.lib.merge(['A'])
        driver=Mock()
        search=Mock(side_effect=[SearchBlocked('verify'), []])
        job=Jobs(self.lib,search=search,driver_factory=lambda:driver)
        job.start('search');job.thread.join(3)
        self.assertEqual(self.lib.snapshot()['items'][0]['status'],'blocked')
        driver.quit.assert_not_called()
        job.start('search');job.thread.join(3)
        self.assertEqual(self.lib.snapshot()['items'][0]['status'],'empty')
        driver.quit.assert_called_once()

    def test_failed_search_is_not_empty(self):
        self.lib.merge(['A'])
        job=Jobs(self.lib,search=Mock(side_effect=RuntimeError('offline')),driver_factory=Mock)
        job.start('search');job.thread.join(3)
        item=self.lib.snapshot()['items'][0]
        self.assertEqual(item['status'],'error')
        self.assertEqual(item['error'],'offline')

    def test_prevent_concurrent_tasks(self):
        self.lib.merge(['A'])
        gate=threading.Event()
        job=Jobs(self.lib,search=lambda *a,**k:(gate.wait(1) and []),driver_factory=Mock)
        job.start('search')
        with self.assertRaises(ValueError):job.start('search')
        gate.set();job.thread.join(3)


class DoubanTests(unittest.TestCase):
    def test_metadata_and_pagination(self):
        items, link=parse_page(PAGE+'<span class="next"><a href="?start=15">后页</a></span>')
        self.assertEqual(items[0]['title'],'这个杀手不太冷')
        self.assertEqual(items[0]['year'],'1994')
        self.assertEqual(link,'?start=15')

    def test_blocked_and_changed_pages_raise(self):
        for html in ('<h1>安全验证</h1>','<h1>Log in</h1>'):
            with self.assertRaises(RuntimeError):parse_page(html)
        self.assertEqual(parse_page('<div class="grid-view"></div>'),([],None))

    def test_only_public_douban_path(self):
        for url in ('http://127.0.0.1/', 'https://movie.douban.com.evil.com/people/x/wish','https://movie.douban.com/subject/1/'):
            with self.assertRaises(ValueError):validate_wishlist_url(url)

    @patch('modules.douban.requests.Session')
    def test_limit_stops_before_next_request(self, cls):
        session=cls.return_value
        session.get.return_value=Mock(status_code=200,text=PAGE+'<span class="next"><a href="?start=15">next</a></span>')
        result=get_wishlist_items('https://movie.douban.com/people/a/wish',limit=1)
        self.assertEqual(len(result),1)
        session.get.assert_called_once()
        session.close.assert_called_once()

    @patch('modules.douban.requests.Session')
    def test_external_pagination_rejected(self, cls):
        session=cls.return_value
        session.get.return_value=Mock(status_code=200,text=PAGE+'<span class="next"><a href="https://evil.com/people/a/wish">next</a></span>')
        with patch('modules.douban.time.sleep'):
            with self.assertRaises(ValueError):get_wishlist_items('https://movie.douban.com/people/a/wish')
        session.get.assert_called_once()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.lib=Library(Path(self.tmp.name)/'library.json')
        self.jobs=Jobs(self.lib)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.lib,self.jobs))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.tmp.cleanup()

    def post(self,path,data,headers=None):
        return urlopen(Request(self.base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json',**(headers or {})}),timeout=3)

    def test_import_edit_export(self):
        with self.post('/api/import',{'items':['A']}) as r:self.assertEqual(r.status,200)
        item=self.lib.snapshot()['items'][0]
        with self.post('/api/item',{'id':item['id'],'note':'=1+1','quark_links':['https://pan.quark.cn/s/abc?pwd=1234']}) as r:self.assertEqual(r.status,200)
        with urlopen(self.base+'/api/export.json') as r:data=json.load(r)
        self.assertEqual(data['items'][0]['status'],'found')
        with urlopen(self.base+'/api/export.csv') as r:csv=r.read().decode('utf-8-sig')
        self.assertIn("'=1+1",csv)

    def test_cross_origin_rejected(self):
        with self.assertRaises(HTTPError) as error:
            self.post('/api/import',{'items':['A']},{'Origin':'https://evil.com'})
        self.assertEqual(error.exception.code,403)
        error.exception.close()
        self.assertEqual(self.lib.snapshot()['items'],[])

    def test_rebinding_host_rejected(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.base+'/api/state',headers={'Host':'evil.com'}))
        self.assertEqual(error.exception.code,403)
        error.exception.close()

    def test_invalid_edit_keeps_existing_data(self):
        self.lib.merge(['A'])
        item=self.lib.snapshot()['items'][0]
        with self.assertRaises(HTTPError) as error:
            self.post('/api/item',{'id':item['id'],'quark_links':['javascript:alert(1)']})
        self.assertEqual(error.exception.code,400)
        error.exception.close()
        self.assertEqual(self.lib.snapshot()['items'][0]['status'],'pending')

    def test_static_allowlist(self):
        with self.assertRaises(HTTPError) as error:urlopen(self.base+'/output/library.json')
        self.assertEqual(error.exception.code,404)
        error.exception.close()


if __name__=='__main__':unittest.main()
