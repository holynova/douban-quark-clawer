# Douban Quark Crawler (豆瓣夸克资源自动搜刮器)

这是一个全自动化的 Python 工具，用于批量查找用户豆瓣“想看”列表中的电影/剧集资源，并自动将其保存到您的夸克网盘中。

## 功能特点

*   **自动化获取**: 自动抓取指定豆瓣用户的“想看”列表（支持翻页），并保存为 `output/wishlist.json`。
*   **智能搜索**: 使用 Selenium 模拟浏览器在 Google 上搜索夸克网盘分享链接。
*   **数据导出**: 将搜索到的夸克网盘链接保存为 `output/quark_links.json`。
*   **无需登录**: 仅进行搜索和提取，不需要登录夸克网盘。

## 环境要求

*   Python 3.8+
*   Google Chrome 浏览器

## 安装步骤

1.  克隆或下载本项目代码。
2.  安装依赖库：
    ```bash
    pip install -r requirements.txt
    ```

## 使用方法

1.  **运行程序**:
    在终端中运行 `main.py`，并传入您的豆瓣“想看”列表 URL：
    ```bash
    python main.py https://movie.douban.com/people/YOUR_ID/wish
    ```
    *例如*: `python main.py https://movie.douban.com/people/mobile_sang/wish`

2.  **等待完成**:
    程序会自动遍历您的想看列表，搜索资源。
    *   搜索过程中会实时打印进度。
    *   完成后，您可以在 `output/` 目录下找到 `wishlist.json` 和 `quark_links.json`。

## 输出文件

*   `output/wishlist.json`: 包含所有抓取到的电影/剧集名称。
*   `output/quark_links.json`: 包含电影名称及其对应的夸克网盘搜索结果链接。

## 注意事项

*   **Google 访问**: 本工具依赖 Google 搜索，请确保您的网络环境可以访问 Google。
*   **验证码**: 如果搜索过于频繁，Google 可能会弹出验证码。此时程序可能会暂停或失败，建议稍后重试。

## 文件结构

*   `main.py`: 主程序入口。
*   `config.py`: 配置文件（URL、选择器等）。
*   `modules/`: 功能模块（豆瓣抓取、搜索、自动化）。
*   `utils/`: 工具函数（日志、浏览器驱动）。
