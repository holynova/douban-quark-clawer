"""Legacy CLI, now sharing the resumable workbench library."""
import argparse
import json
import time
from pathlib import Path
from modules.library import Library
from modules.jobs import Jobs


def main():
    parser = argparse.ArgumentParser(description='豆瓣想看 → 夸克候选链接（支持断点续跑）')
    parser.add_argument('url', nargs='?', help='公开的豆瓣想看 URL；省略时继续已有片单')
    parser.add_argument('--limit', type=int, default=300)
    parser.add_argument('--import-file', type=Path, help='导入旧版或新版 JSON')
    parser.add_argument('--retry', action='store_true', help='重试失败、等待验证和未找到的影片')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'output')
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error('--limit 应为 1–1000')
    library = Library(args.output / 'library.json')
    jobs = Jobs(library)
    def wait():
        previous = ''
        while jobs.snapshot()['active']:
            message = jobs.snapshot()['message']
            if message != previous:
                print(message, flush=True)
                previous = message
            time.sleep(.2)
        print(jobs.snapshot()['message'], flush=True)
    try:
        if args.import_file:
            library.merge(json.loads(args.import_file.read_text(encoding='utf-8')))
        if args.url:
            jobs.start('import', args.url, args.limit)
            wait()
            if jobs.snapshot()['message'].startswith('任务未完成'):
                return 1
        statuses = ('empty', 'error', 'blocked') if args.retry else ('pending', 'error', 'blocked')
        if any(i['status'] in statuses for i in library.snapshot()['items']):
            jobs.start('retry' if args.retry else 'search')
            wait()
        else:
            print('没有待处理影片。可先导入片单，或使用 --retry。')
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'quark_links.json').write_text(json.dumps(library.snapshot()['items'], ensure_ascii=False, indent=2), encoding='utf-8')
        items = library.snapshot()['items']
        if jobs.snapshot()['message'].startswith('任务未完成') or any(i['status'] in ('error', 'blocked') for i in items):
            return 1
        return 0
    except KeyboardInterrupt:
        jobs.pause()
        print('已请求暂停。已完成的影片已保存在 library.json。')
        return 130
    except (ValueError, OSError) as exc:
        print(f'未完成：{exc}')
        return 1
    finally:
        jobs.close()


if __name__ == '__main__':
    raise SystemExit(main())
