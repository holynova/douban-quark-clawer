# 想看 · 豆瓣 × 夸克片单工作台

[English](./README.en.md) · [GitHub 仓库](https://github.com/holynova/douban-quark-clawer)

把豆瓣「想看」、夸克候选链接和观影备注放在一个本地工作台里。原 `douban-quark-clawer` 的新版，保留 Python 命令行入口。

![想看片单工作台](docs/workbench-desktop.png)

## 启动

需要 Python 3.10+。自动搜索另需 Google Chrome 和可访问 Google 的网络；首次搜索时 Selenium 会自动管理匹配的驱动，可能需要联网下载。

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

macOS 也可双击 `start.command` 启动。

打开 **http://127.0.0.1:8765**。服务仅监听本机；关闭页面不会停止后台任务，退出 Python 服务才会停止。片单持久化在 `output/library.json`，不会上传到项目仓库。

可指定端口和数据目录：

```bash
python server.py --port 8766 --data-dir /path/to/my-watchlist
```

## 使用流程

1. **导入**：粘贴公开的豆瓣想看地址、每行一个片名，或选择 JSON 文件。豆瓣按页保存，支持 50 / 300 / 1000 部上限。
2. **搜索**：点击「开始搜索」，打开独立 Chrome 窗口，按片名寻找夸克分享候选。完成一部保存一部，暂停后可继续，重启服务也不会重新搜索已完成项。
3. **整理**：按状态或片名 / 备注筛选，打开候选链接确认内容，在「整理」中修改链接和备注。
4. **导出**：JSON 可重新导入，CSV 可用表格软件打开。移动端布局也可用于浏览器窄窗口；服务默认不开放局域网访问。

### 状态含义

| 状态 | 含义与后续动作 |
|---|---|
| 等待搜索 | 尚未处理，点击开始搜索 |
| 已收集 | 存在候选链接；不代表内容匹配、链接有效或已经转存 |
| 未找到 | 已加载搜索结果但未提取到直接分享链接，可手动搜索或重试 |
| 搜索失败 | 网络或页面加载异常，可重试 |
| 等待验证 | Google 要求人机验证，队列立即停止；在保留的 Chrome 窗口处理后继续 |

豆瓣需要登录、返回验证页或页面结构变化时，会显示错误，已经导入的页面仍保留。可改用片名或 JSON 导入。不会绕过验证码。重试按钮包含「未找到 / 搜索失败 / 等待验证」，正常开始搜索则跳过「已收集 / 未找到」。

## 旧版数据兼容

支持旧版 `wishlist.json` 的片名数组、`quark_links.json` / 中断文件中的对象数组，以及新版导出的 `{ "version": 2, "items": [...] }`。导入采取合并策略，保留已有链接和备注；有豆瓣条目时按条目 URL 识别，否则按片名识别。不同豆瓣条目的同名电影不会合并。

```json
[
  {"title": "片名", "quark_links": [], "note": "观影备注"}
]
```

分享链接只接受 `pan.quark.cn/s/…` 和 `drive.quark.cn/s/…`，保留 `pwd` / `passcode` 参数。文件大小上限 2 MB，单次最多 5000 条。

## 命令行

```bash
python main.py https://movie.douban.com/people/YOUR_ID/wish --limit 50
python main.py --import-file old-wishlist.json
python main.py                       # 继续已有片单
python main.py --retry               # 重试未找到与失败项
```

命令行和网页使用同一数据格式；请勿同时启动多个进程操作同一数据目录。网页任务遇到验证会保留浏览器供处理；CLI 遇到验证会保存状态后退出，可改用网页继续。

## 能力边界

本项目收集候选链接，不提供电影文件，不校验分享内容，也**不会自动登录或转存到夸克网盘**。旧版 README 的自动转存描述与实际主流程不符，现已更正。旧 `modules/quark_automator.py` 作为历史实验保留，未接入新版流程。

自动搜索只读取搜索结果中的直接夸克分享链接，不递归访问第三方聚合网站。Google / 豆瓣的页面结构和访问限制可能变化；失败会明确显示，手动搜索、链接录入和文件导入可以独立使用。

## 本次验证记录

2026-11-16：20 项离线测试通过；浏览器验证片名与 JSON 导入、去重、非法输入、链接编辑 / 复制、筛选、导出和刷新恢复，并检查 1280px / 390px 布局。真实豆瓣想看片单成功读取 1 条；真实 Google 搜索触发验证码，成功识别为等待验证，未完成真实资源链接获取验证。

## 开发与验证

前端为原生 HTML / CSS / JavaScript，无 Node 构建依赖；后端使用 Python 标准库 HTTP 服务。

```bash
python -m unittest discover -s tests -v
python -m compileall -q modules utils main.py server.py
node --check web/app.js  # 可选的 JS 语法检查
```

测试覆盖导入兼容、原子文件写入后的恢复、去重、分页限制、异常页面、暂停续跑、验证码等待、失败状态、导出与本地 API 的来源校验。外部网站测试不放入离线回归套件。

```text
server.py           本地 Web 服务与 API
main.py             命令行入口
modules/library.py  片单归一化与持久化
modules/jobs.py     可暂停的单任务队列
modules/douban.py   豆瓣片单抓取
modules/search.py   分享链接搜索与验证码状态
web/                响应式工作台
tests/             离线回归测试
```
