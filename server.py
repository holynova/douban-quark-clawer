"""Loopback-only local web workbench. Run: python server.py"""
import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from modules.library import Library, quark_url
from modules.jobs import Jobs

ROOT = Path(__file__).resolve().parent


def make_handler(library, jobs):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status, body, mime='application/json; charset=utf-8', filename=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            port = self.server.server_port
            return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

        def do_GET(self):
            if not self.allowed():
                return self.send(403, {'error': '只允许本机访问。'})
            path = urlparse(self.path).path
            if path == '/api/state':
                return self.send(200, {**library.snapshot(), 'job': jobs.snapshot()})
            if path == '/api/export.json':
                return self.send(200, library.snapshot(), filename='watchlist.json')
            if path == '/api/export.csv':
                out = io.StringIO()
                writer = csv.writer(out)
                writer.writerow(['片名', '年份', '豆瓣', '状态', '夸克链接', '备注'])
                for i in library.snapshot()['items']:
                    values = [i['title'], i['year'], i['douban_url'], i['status'], '\n'.join(i['quark_links']), i['note']]
                    writer.writerow(["'" + v if v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
                return self.send(200, ('\ufeff' + out.getvalue()).encode(), 'text/csv; charset=utf-8', 'watchlist.csv')
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/style.css': ('style.css', 'text/css'), '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
            if path in assets:
                file, mime = assets[path]
                return self.send(200, (ROOT / 'web' / file).read_bytes(), mime + '; charset=utf-8')
            self.send(404, {'error': '页面不存在。'})

        def do_POST(self):
            origin = self.headers.get('Origin')
            if not self.allowed() or (origin and origin != 'http://' + self.headers.get('Host', '')):
                return self.send(403, {'error': '不接受其他网站的请求。'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send(415, {'error': '请使用 JSON 请求。'})
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 2_000_000:
                    raise ValueError('导入文件需小于 2 MB。')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('请求必须是 JSON 对象。')
                if self.path == '/api/import':
                    count = library.merge(data.get('items'))
                    return self.send(200, {'message': f'新增 {count} 部影片，重复项已合并。'})
                if self.path == '/api/job':
                    limit = int(data.get('limit', 300))
                    if not 1 <= limit <= 1000:
                        raise ValueError('导入上限应为 1–1000。')
                    jobs.start(data.get('kind'), str(data.get('url', '')), limit)
                elif self.path == '/api/pause':
                    jobs.pause()
                elif self.path == '/api/delete':
                    if jobs.snapshot()['active']:
                        raise ValueError('请先暂停任务，再移除影片。')
                    library.delete(str(data.get('id')))
                elif self.path == '/api/item':
                    if jobs.snapshot()['active']:
                        raise ValueError('请先暂停任务，再编辑影片。')
                    values = {}
                    if 'quark_links' in data:
                        raw = data['quark_links']
                        if not isinstance(raw, list) or any(not quark_url(v) for v in raw):
                            raise ValueError('请输入有效的 pan.quark.cn/s/ 或 drive.quark.cn/s/ 分享链接。')
                        links = list(dict.fromkeys(quark_url(v) for v in raw))
                        values.update(quark_links=links, status='found' if links else 'pending', error='')
                    if 'note' in data:
                        values['note'] = str(data['note'])[:2000]
                    library.update(str(data.get('id')), **values)
                else:
                    return self.send(404, {'error': '接口不存在。'})
                self.send(200, {'message': '已保存'})
            except (ValueError, TypeError) as exc:
                self.send(400, {'error': str(exc)})
            except Exception:
                self.send(500, {'error': '操作未完成，请检查本地数据目录是否可写。'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description='想看 · 豆瓣与夸克本地工作台')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    library = Library(args.data_dir / 'library.json')
    jobs = Jobs(library)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(library, jobs))
    print(f'想看工作台已启动：http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        jobs.close()
        server.server_close()


if __name__ == '__main__':
    main()
