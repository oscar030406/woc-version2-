import csv
import os
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger

# Task2 - 方案一
# requests + bs4 同步爬取 books.toscrape.com
# 最基础的版本，先跑通再说

BASE_URL = 'https://books.toscrape.com/catalogue/page-{}.html'
DETAIL_BASE = 'https://books.toscrape.com/catalogue/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36'
}
RATING_MAP = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
MAX_PAGES = 10
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'books_requests.csv')


def parse_book(article):
    """
    从article标签解析一本书
    :param article: bs4 Tag
    :return: dict
    """
    h3 = article.find('h3')
    a = h3.find('a') if h3 else None
    title = a['title'] if a and a.has_attr('title') else ''
    href = a['href'] if a else ''
    url = DETAIL_BASE + href.lstrip('./')

    # 价格
    price_p = article.find('p', class_='price_color')
    price_text = price_p.get_text(strip=True) if price_p else '£0'
    price = price_text.lstrip('£Â')

    # 库存
    stock_p = article.find('p', class_='instock')
    stock = stock_p.get_text(strip=True) if stock_p else ''

    # 评分 (class="star-rating Three" -> 3)
    star_p = article.find('p', class_='star-rating')
    rating = 0
    if star_p:
        classes = star_p.get('class', [])
        for cls in classes:
            if cls in RATING_MAP:
                rating = RATING_MAP[cls]
                break

    return {
        'title': title,
        'price': price,
        'stock': stock,
        'rating': rating,
        'url': url
    }


def scrape_books(max_pages=MAX_PAGES):
    """同步爬取"""
    sess = requests.Session()
    sess.headers.update(HEADERS)
    result = []

    for page in range(1, max_pages + 1):
        url = BASE_URL.format(page)
        try:
            resp = sess.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f'page {page} request failed: {e}')
            break

        soup = BeautifulSoup(resp.text, 'lxml')
        articles = soup.find_all('article', class_='product_pod')
        for art in articles:
            result.append(parse_book(art))
        logger.info(f'page {page}: got {len(articles)} books')
        time.sleep(0.3)

    sess.close()
    return result


def save_csv(books, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['title', 'price', 'stock', 'rating', 'url'])
        w.writeheader()
        w.writerows(books)
    logger.info(f'saved {len(books)} books -> {filepath}')


def main():
    logger.info(f'requests同步爬取, 共{MAX_PAGES}页')
    t0 = time.time()
    books = scrape_books()
    elapsed = time.time() - t0
    logger.info(f'爬取完成: {len(books)} 本, 耗时 {elapsed:.2f}s')
    save_csv(books, CSV_FILE)


if __name__ == '__main__':
    main()
