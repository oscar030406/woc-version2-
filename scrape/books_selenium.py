import csv
import os
import re
import time
from loguru import logger

# Task2 方案4: 逆向分析 + Selenium
# 思路: 用selenium加载页面，拦截/分析network请求，
#       然后直接用requests构造请求拿数据
# 这里演示两种逆向手段:
#   1. selenium渲染页面后提取 (适用于JS动态渲染的站点)
#   2. 分析页面接口，直接requests请求 (真正的逆向)
# books.toscrape.com是静态站，为了演示逆向流程,
# 我们先用selenium获取完整DOM，再提取数据

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    logger.warning('selenium未安装, 执行 pip install selenium')

import requests

BASE_URL = 'https://books.toscrape.com/catalogue/page-{}.html'
DETAIL_BASE = 'https://books.toscrape.com/catalogue/'
RATING_MAP = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
MAX_PAGES = 10
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'books_selenium.csv')


def get_browser():
    """
    创建headless Chrome
    :return: webdriver.Chrome
    """
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/122.0.0.0 Safari/537.36')
    # 禁用图片加载，加快速度
    prefs = {'profile.managed_default_content_settings.images': 2}
    opts.add_experimental_option('prefs', prefs)
    browser = webdriver.Chrome(options=opts)
    browser.implicitly_wait(5)
    return browser


def parse_page_selenium(browser, url):
    """
    逆向思路1: 用selenium渲染页面后，通过DOM直接提取
    对于JS渲染的电商站，这种方式可以拿到动态加载的数据
    :param browser: webdriver
    :param url: 页面url
    :return: list[dict]
    """
    browser.get(url)
    books = []

    articles = browser.find_elements(By.CSS_SELECTOR, 'article.product_pod')
    for art in articles:
        try:
            a = art.find_element(By.CSS_SELECTOR, 'h3 a')
            title = a.get_attribute('title') or ''
            href = a.get_attribute('href') or ''

            price_el = art.find_element(By.CSS_SELECTOR, 'p.price_color')
            price = price_el.text.lstrip('£Â') if price_el else '0'

            stock_el = art.find_element(By.CSS_SELECTOR, 'p.instock')
            stock = stock_el.text.strip() if stock_el else ''

            star_el = art.find_element(By.CSS_SELECTOR, 'p.star-rating')
            star_cls = star_el.get_attribute('class') or ''
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
                'url': href
            })
        except Exception as e:
            logger.debug(f'parse element error: {e}')
            continue

    return books


def scrape_with_selenium(max_pages=MAX_PAGES):
    """
    selenium爬取方案
    :param max_pages: 页数
    :return: list[dict]
    """
    browser = get_browser()
    all_books = []
    try:
        for page in range(1, max_pages + 1):
            url = BASE_URL.format(page)
            books = parse_page_selenium(browser, url)
            all_books.extend(books)
            logger.info(f'[selenium] page {page}: {len(books)} books')
    finally:
        browser.quit()
    return all_books


def reverse_analysis():
    """
    逆向思路2: 分析站点结构，找到数据接口或规律
    用requests + 正则提取，不依赖任何HTML解析库
    :return: list[dict]
    """
    logger.info('正则逆向方案: 分析HTML结构后直接正则匹配')

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 Chrome/122.0.0.0'
    })

    books = []
    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL.format(page)
        resp = session.get(url, timeout=10)
        html = resp.text

        # 用正则直接匹配，不依赖任何解析库
        # 这就是逆向的核心 - 理解数据在HTML中的位置
        pattern = re.compile(
            r'<article class="product_pod">.*?'
            r'<a href="(?P<href>[^"]+)".*?title="(?P<title>[^"]*)".*?'
            r'<p class="price_color">(?P<price>[^<]+)</p>.*?'
            r'<p class="star-rating (?P<star>\w+)"',
            re.DOTALL
        )

        for m in pattern.finditer(html):
            title = m.group('title')
            href = m.group('href')
            price = m.group('price').strip().lstrip('£Â')
            star_word = m.group('star')
            rating = RATING_MAP.get(star_word, 0)

            books.append({
                'title': title,
                'price': price,
                'stock': 'In stock',
                'rating': rating,
                'url': DETAIL_BASE + href.lstrip('./')
            })

        logger.info(f'[regex] page {page}: total {len(books)} books so far')

    session.close()
    return books


def save_csv(books, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['title', 'price', 'stock', 'rating', 'url'])
        w.writeheader()
        w.writerows(books)
    logger.info(f'saved {len(books)} books -> {filepath}')


def main():
    logger.info('Task2 方案4: 逆向分析')
    t0 = time.time()

    if HAS_SELENIUM:
        # 有selenium就用selenium方案
        logger.info('Selenium headless browser 爬取开始...')
        try:
            books = scrape_with_selenium(MAX_PAGES)
            elapsed = time.time() - t0
            logger.info(f'Selenium完成: {len(books)} 本, 耗时 {elapsed:.2f}s')
            save_csv(books, CSV_FILE)
            return
        except Exception as e:
            logger.error(f'Selenium爬取失败: {e}')
            logger.info('fallback到正则逆向方案...')

    # 没selenium或selenium失败，fallback到正则方案
    books = reverse_analysis()
    elapsed = time.time() - t0
    logger.info(f'正则逆向完成: {len(books)} 本, 耗时 {elapsed:.2f}s')
    save_csv(books, CSV_FILE)


if __name__ == '__main__':
    main()
