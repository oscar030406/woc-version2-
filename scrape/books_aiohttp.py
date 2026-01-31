import asyncio
import csv
import os
import time
import aiohttp
from pyquery import PyQuery as pq
from loguru import logger

# Task2 - 方案二
# aiohttp + pyquery 异步爬取
# pyquery的选择器风格跟 jQuery 差不多，写起来比bs4顺手一点

BASE_URL = 'https://books.toscrape.com/catalogue/page-{}.html'
DETAIL_BASE = 'https://books.toscrape.com/catalogue/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36'
}
RATING_MAP = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
MAX_PAGES = 10
CONCURRENCY = 5
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'books_aiohttp.csv')


def parse_page(html):
    """pyquery解析页面"""
    doc = pq(html)
    books = []
    for item in doc('article.product_pod').items():
        a = item.find('h3 a')
        title = a.attr('title') or ''
        href = a.attr('href') or ''
        url = DETAIL_BASE + href.lstrip('./')

        price_text = item.find('p.price_color').text()
        price = price_text.lstrip('£Â') if price_text else '0'

        stock = item.find('p.instock').text().strip()

        # 评分从class里取
        star_cls = item.find('p.star-rating').attr('class') or ''
        rating = 0
        for word, val in RATING_MAP.items():
            if word in star_cls:
                rating = val
                break

        books.append({
            'title': title,
            'price': price,
            'stock': stock,
            'rating': rating,
            'url': url
        })
    return books


async def fetch(session, url, sem):
    """fetch单页"""
    async with sem:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            return await resp.text()


async def scrape_all(max_pages):
    """aiohttp并发爬全部页"""
    sem = asyncio.Semaphore(CONCURRENCY)
    books = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = []
        for page in range(1, max_pages + 1):
            url = BASE_URL.format(page)
            tasks.append(fetch(session, url, sem))
        htmls = await asyncio.gather(*tasks, return_exceptions=True)

    for i, html in enumerate(htmls):
        if isinstance(html, Exception):
            logger.error(f'page {i+1} failed: {html}')
            continue
        page_books = parse_page(html)
        books.extend(page_books)
        logger.info(f'page {i+1}: parsed {len(page_books)} books')

    return books


def save_csv(books, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['title', 'price', 'stock', 'rating', 'url'])
        w.writeheader()
        w.writerows(books)
    logger.info(f'saved {len(books)} books -> {filepath}')


def main():
    logger.info(f'aiohttp+pyquery异步爬取, 共{MAX_PAGES}页')
    t0 = time.time()
    loop = asyncio.new_event_loop()
    books = loop.run_until_complete(scrape_all(MAX_PAGES))
    loop.close()
    elapsed = time.time() - t0
    logger.info(f'爬取完成: {len(books)} 本, 耗时 {elapsed:.2f}s')
    save_csv(books, CSV_FILE)


if __name__ == '__main__':
    main()
