# 项目说明

本项目完成两个任务：

- **Task1：豆瓣 Top250 电影信息抓取**（requests 串行 + aiohttp/asyncio 并发优化 + 保存 + 计时）
- **Task2：电商商品信息抓取**（Books to Scrape，使用不同库实现并保存）

> 详细实验过程与结果请见 `report.md`。

---

## 环境准备

```bash
pip install -r requirements.txt
```
如运行 Selenium 方案，请安装 ChromeDriver 并与本机 Chrome 版本匹配。
---

## 快速运行

### Task1：豆瓣电影

```bash
# 基础版（串行，约 12.4s）
python scrape/douban_scrape.py

# 优化版（并发，约 1.3s，加速 9.6x）
python scrape/douban_scrape_optimized.py
```

### Task2：商品信息

```bash
# 方案1: requests + BeautifulSoup
python scrape/books_requests.py

# 方案2: aiohttp + pyquery（并发）
python scrape/books_aiohttp.py

# 方案3: Scrapy框架
python scrape/books_scrapy.py

# 方案4: Selenium（可选）
python scrape/books_selenium.py
```

---

## 数据输出

所有数据保存在 `data/` 目录：

- `douban_movies.csv` / `douban_movies_optimized.csv`（Task1）
- `books_requests.csv` / `books_aiohttp.csv` / `books_scrapy.csv` / `books_selenium.csv`（Task2）

---

## 目录结构

```
woc2/
├── README.md              # 本文件
├── report.md              # 详细实验报告
├── requirements.txt       # 依赖列表
├── scrape/                # 爬虫脚本
│   ├── douban_scrape.py
│   ├── douban_scrape_optimized.py
│   └── books_*.py
└── data/                  # 输出数据
    └── *.csv
