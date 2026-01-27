import argparse
import asyncio
import csv
import os
import re
import time
import aiohttp
import requests
from bs4 import BeautifulSoup
from loguru import logger

# 豆瓣Top250优化爬虫 - aiohttp并发版本
# 跑完async之后可以选择性跑一次串行做对比

BASE_URL = 'https://movie.douban.com/top250'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://movie.douban.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
CONCURRENCY = 5  # 并发数，别太高不然直接被ban
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'douban_movies_optimized.csv')
CSV_FIELDS = ['rank', 'title', 'director', 'actors', 'year', 'country',
              'genre', 'rating', 'votes', 'quote', 'url']


def parse_item(item):
    """
    解析单个电影条目，和基础版一样的逻辑
    :param item: BeautifulSoup Tag
    :return: dict
    """
    hd = item.find('div', class_='hd')
    bd = item.find('div', class_='bd')

    pic = item.find('div', class_='pic')
    rank_em = pic.find('em') if pic else None
    rank = rank_em.get_text(strip=True) if rank_em else ''

    link = hd.find('a') if hd else None
    url = link['href'] if link else ''
    title_span = hd.find('span', class_='title') if hd else None
    title = title_span.get_text(strip=True) if title_span else ''

    info_p = bd.find('p') if bd else None
    info_text = info_p.get_text('\n', strip=True) if info_p else ''
    lines = [l.strip() for l in info_text.split('\n') if l.strip()]

    director = actors = year = country = genre = ''
    if lines:
        first = lines[0]
        m = re.search(r'导演:\s*(.+?)(?:\s+主演:|$)', first)
        if m:
            director = m.group(1).strip().rstrip('...')
        m2 = re.search(r'主演:\s*(.+)', first)
        if m2:
            actors = m2.group(1).strip().rstrip('...')

    if len(lines) > 1:
        parts = [p.strip() for p in lines[-1].split('/')]
        if parts:
            year = re.sub(r'[^\d]', '', parts[0])
        if len(parts) > 1:
            country = parts[1].strip()
        if len(parts) > 2:
            genre = parts[2].strip()

    star_div = bd.find('div', class_='star') if bd else None
    rating_span = star_div.find('span', class_='rating_num') if star_div else None
    rating = rating_span.get_text(strip=True) if rating_span else ''

    votes = ''
    if star_div:
        spans = star_div.find_all('span')
        if spans:
            vote_text = spans[-1].get_text(strip=True)
            votes = vote_text.replace('人评价', '').strip()

    quote_span = bd.find('span', class_='inq') if bd else None
    quote = quote_span.get_text(strip=True) if quote_span else ''

    return {
        'rank': rank, 'title': title, 'director': director,
        'actors': actors, 'year': year, 'country': country,
        'genre': genre, 'rating': rating, 'votes': votes,
        'quote': quote, 'url': url
    }


async def fetch_page(session, start, sem):
    """
    异步抓取单页
    :param session: aiohttp.ClientSession
    :param start: 偏移量
    :param sem: asyncio.Semaphore
    :return: list[dict]
    """
    url = f'{BASE_URL}?start={start}'
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')
                items = soup.find_all('div', class_='item')
                logger.info(f'[async] start={start} got {len(items)} items')
                # 加个小延迟，每个协程之间错开
                await asyncio.sleep(0.3)
                return [parse_item(it) for it in items]
        except Exception as e:
            logger.error(f'[async] start={start} failed: {e}')
            return []


async def scrape_all():
    """
    并发抓取全部10页
    :return: list[dict]
    """
    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [fetch_page(session, start, sem) for start in range(0, 250, 25)]
        results = await asyncio.gather(*tasks)

    # 合并结果
    movies = []
    for page_movies in results:
        movies.extend(page_movies)

    # 按rank排序
    movies.sort(key=lambda x: int(x['rank']) if x['rank'].isdigit() else 999)
    return movies


def save_csv(movies, filepath):
    """
    保存csv
    :param movies: list[dict]
    :param filepath: str
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(movies)
    logger.info(f'saved {len(movies)} records -> {filepath}')


def measure_serial_baseline():
    """
    跑一次真实的串行请求，拿到基准耗时
    不写文件，只计时
    :return: (耗时秒数, 电影数量)
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update(HEADERS)

    count = 0
    t0 = time.time()
    for start in range(0, 250, 25):
        try:
            resp = session.get(BASE_URL, params={'start': start}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            items = soup.find_all('div', class_='item')
            count += len(items)
            time.sleep(1)
        except Exception as e:
            logger.warning(f'[serial baseline] start={start} failed: {e}')
    elapsed = time.time() - t0
    session.close()
    return elapsed, count


def main():
    ap = argparse.ArgumentParser(description='豆瓣Top250 aiohttp优化爬虫')
    ap.add_argument('--skip-benchmark', action='store_true',
                    help='跳过串行基准测试，只跑并发')
    args = ap.parse_args()

    # === 并发爬取 ===
    logger.info('豆瓣Top250 优化版 (aiohttp并发) 开始...')
    t_start = time.time()

    loop = asyncio.new_event_loop()
    movies = loop.run_until_complete(scrape_all())
    loop.close()

    async_elapsed = time.time() - t_start
    logger.info(f'并发抓取完成: {len(movies)} 部, 耗时 {async_elapsed:.2f}s')

    save_csv(movies, CSV_FILE)

    # === 串行基准对比 ===
    if not args.skip_benchmark:
        logger.info('开始串行基准测试 (用于对比加速比)...')
        serial_elapsed, serial_count = measure_serial_baseline()
        logger.info(f'串行基准: {serial_count} 部, 耗时 {serial_elapsed:.2f}s')
        speedup = serial_elapsed / async_elapsed if async_elapsed > 0 else 0
        logger.info(f'加速比: {speedup:.1f}x  ({serial_elapsed:.2f}s -> {async_elapsed:.2f}s)')
    else:
        logger.info(f'跳过benchmark, 并发耗时 {async_elapsed:.2f}s')


if __name__ == '__main__':
    main()
