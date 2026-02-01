import csv
import os
import time
from loguru import logger

# Task2 - 方案三: Scrapy
# 企业级框架，自带很多特性，写起来也麻烦一点

try:
    import scrapy
    from scrapy.crawler import CrawlerProcess
    from scrapy import signals
    HAS_SCRAPY = True
except ImportError:
    HAS_SCRAPY = False
    logger.warning('scrapy未安装, 执行 pip install scrapy')

RATING_MAP = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
MAX_PAGES = 10
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'books_scrapy.csv')


if HAS_SCRAPY:
    class BooksSpider(scrapy.Spider):
        """books.toscrape.com 爬虫"""
        name = 'books'
        allowed_domains = ['books.toscrape.com']
        custom_settings = {
            'ROBOTSTXT_OBEY': False,
            'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/122.0.0.0 Safari/537.36',
            'CONCURRENT_REQUESTS': 4,
            'DOWNLOAD_DELAY': 0.5,
            'LOG_LEVEL': 'WARNING',
        }

        def __init__(self, max_pages=10, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.max_pages = int(max_pages)

        def start_requests(self):
            for page in range(1, self.max_pages + 1):
                url = f'https://books.toscrape.com/catalogue/page-{page}.html'
                yield scrapy.Request(url, callback=self.parse_page)

        def parse_page(self, response):
            for article in response.css('article.product_pod'):
                a = article.css('h3 a')
                title = a.attrib.get('title', '')
                href = a.attrib.get('href', '')
                url = 'https://books.toscrape.com/catalogue/' + href.lstrip('./')

                price_text = article.css('p.price_color::text').get('').lstrip('£Â')
                stock = article.css('p.instock.availability::text').getall()
                stock = ' '.join(s.strip() for s in stock).strip()

                star_cls = article.css('p.star-rating').attrib.get('class', '')
                rating = 0
                for word, val in RATING_MAP.items():
                    if word in star_cls:
                        rating = val
                        break

                yield {
                    'title': title,
                    'price': price_text,
                    'stock': stock,
                    'rating': rating,
                    'url': url
                }


class ItemCollector(object):
    """item收集器，通过signals拿到spider yield的数据"""
    def __init__(self):
        self.items = []

    def collect(self, item, response, spider):
        self.items.append(dict(item))


def run_scrapy(max_pages=MAX_PAGES):
    """启动Scrapy爬虫并收集结果"""
    if not HAS_SCRAPY:
        raise ImportError('scrapy not installed')

    collector = ItemCollector()
    process = CrawlerProcess(settings={
        'LOG_LEVEL': 'WARNING',
    })

    crawler = process.create_crawler(BooksSpider)
    crawler.signals.connect(collector.collect, signal=signals.item_scraped)
    process.crawl(crawler, max_pages=max_pages)
    process.start()

    return collector.items


def save_csv(books, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['title', 'price', 'stock', 'rating', 'url'])
        w.writeheader()
        w.writerows(books)
    logger.info(f'saved {len(books)} books -> {filepath}')


def main():
    logger.info(f'Scrapy爬取, 共{MAX_PAGES}页')
    t0 = time.time()

    try:
        books = run_scrapy(MAX_PAGES)
    except Exception as e:
        logger.error(f'Scrapy爬取失败: {e}')
        return

    elapsed = time.time() - t0
    logger.info(f'Scrapy完成: {len(books)} 本, 耗时 {elapsed:.2f}s')
    save_csv(books, CSV_FILE)


if __name__ == '__main__':
    main()
