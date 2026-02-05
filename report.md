# 爬虫向任务报告

## 1. 任务概述

本次作业包含两个任务：

- **Task1（豆瓣）**：使用 `requests` 获取豆瓣 Top250 电影信息，保存并记录耗时；在此基础上优化代码，使爬取速度提升 50% 以上。
- **Task2（电商）**：选择平台，使用三种以上不同库爬取商品信息并保存（如使用逆向，可只用一种库）。本项目使用示例站点 **Books to Scrape** 作为电商商品列表来源，并实现多种抓取方式。

---

## 2. Task1：豆瓣 Top250 电影信息抓取与优化

### 2.1 抓取目标与字段设计

抓取对象：豆瓣电影 Top250 列表（共 10 页，每页 25 条，总计 250 条）。

字段：

- `rank`：排名
- `title`：电影名
- `director`：导演
- `actors`：主演
- `year`：上映年份
- `country`：国家/地区
- `genre`：类型
- `rating`：评分
- `votes`：评价人数
- `quote`：短评
- `url`：详情页链接

保存方式：CSV。

### 2.2 基础版（requests 串行）

脚本：`scrape/douban_scrape.py`

实现要点：

1. 通过 `requests.get()` 逐页请求
2. 使用 `BeautifulSoup` 解析页面
3. 从列表条目中提取字段，累计 250 条记录
4. 写入 `data/douban_movies.csv`
5. 使用 `time` 记录总耗时

实测结果（本次提交数据）：

- 抓取并保存 250 部电影
- 串行耗时：**约 12.4s**

### 2.3 优化版（aiohttp + asyncio 并发）

脚本：`scrape/douban_scrape_optimized.py`

优化思路：

- 抓取分页属于 **I/O 密集型任务**，瓶颈主要是等待网络响应
- 使用 `aiohttp` 并发请求不同分页，在等待期间可处理其它请求，从而降低总耗时

实现要点：

1. 使用 `aiohttp.ClientSession` 复用连接
2. 使用 `asyncio.gather()` 并发调度分页请求
3. 使用 `asyncio.Semaphore(CONCURRENCY=5)` 控制并发，避免触发风控
4. 完成后合并数据并保存到 `data/douban_movies_optimized.csv`
5. 脚本中额外提供 `measure_serial_baseline()`，用于串行基线对比

实测结果：

- 并发耗时：**约 1.3s**
- 加速比：**约 9.6x（12.4s / 1.3s）**，**远超 50% 性能提升要求**

---

## 3. Task2：商品信息爬取

### 3.1 平台选择与字段设计

平台：Books to Scrape。

字段：

- `title`：商品名
- `price`：价格
- `stock`：库存
- `rating`：评分
- `url`：详情页链接

保存方式：CSV。

### 3.2 不同库实现

#### 方案1：requests + BeautifulSoup

脚本：`scrape/books_requests.py`  
输出：`data/books_requests.csv`

本次提交数据结果：

- 约 200 条商品
- 耗时：约 9.2s

#### 方案2：aiohttp + pyquery

脚本：`scrape/books_aiohttp.py`  
输出：`data/books_aiohttp.csv`

数据结果：

- 约 200 条商品
- 耗时：约 2.1s

#### 方案3：Scrapy

脚本：`scrape/books_scrapy.py`    
输出：`data/books_scrapy.csv`

#### 方案4：Selenium + 正则解析

脚本：`scrape/books_selenium.py`  
输出：`data/books_selenium.csv`

数据结果：

- 约 100 条商品
- 耗时：约 5.5s

---

## 4. 数据文件与提交内容

### 4.1 数据文件（data/）

- `douban_movies.csv`（250）
- `douban_movies_optimized.csv`（250）
- `books_requests.csv`（200）
- `books_aiohttp.csv`（200）
- `books_scrapy.csv`
- `books_selenium.csv`（100）

## 5. Git 版本控制说明

本项目使用 Git 记录开发过程，提交粒度按任务拆分：

- 初始化工程结构与依赖
- Task2 多方案逐步实现（requests / aiohttp / Scrapy / Selenium）
- 代码重构与稳定性修复（清理 import、补充重试、减少冗余）
- Task1 优化补充真实基准测试并更新报告
- 最后提交实际爬取生成的 CSV 数据文件

提交信息清晰描述变更内容，并使用 `.gitignore` 排除无关文件，保证仓库整洁。
