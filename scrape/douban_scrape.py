import csv
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger

# 豆瓣Top250基础爬虫 - 串行版本

BASE_URL = 'https://movie.douban.com/top250'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://movie.douban.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'douban_movies.csv')
CSV_FIELDS = ['rank', 'title', 'director', 'actors', 'year', 'country',
              'genre', 'rating', 'votes', 'quote', 'url']


def get_session():
    """
    创建带重试的session
    :return: requests.Session
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.headers.update(HEADERS)
    return session


def parse_item(item):
    """
    解析单个电影条目
    :param item: BeautifulSoup Tag
    :return: dict
    """
    hd = item.find('div', class_='hd')
    bd = item.find('div', class_='bd')

    # 排名
    pic = item.find('div', class_='pic')
    rank_em = pic.find('em') if pic else None
    rank = rank_em.get_text(strip=True) if rank_em else ''

    # 标题 & 链接
    link = hd.find('a') if hd else None
    url = link['href'] if link else ''
    title_span = hd.find('span', class_='title') if hd else None
    title = title_span.get_text(strip=True) if title_span else ''

    # 导演、主演、年份、地区、类型
    info_p = bd.find('p') if bd else None
    info_text = info_p.get_text('\n', strip=True) if info_p else ''
    lines = [l.strip() for l in info_text.split('\n') if l.strip()]

    director = actors = year = country = genre = ''
    if lines:
        first = lines[0]
        # 导演
        m = re.search(r'导演:\s*(.+?)(?:\s+主演:|$)', first)
        if m:
            director = m.group(1).strip().rstrip('...')
        # 主演
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

    # 评分
    star_div = bd.find('div', class_='star') if bd else None
    rating_span = star_div.find('span', class_='rating_num') if star_div else None
    rating = rating_span.get_text(strip=True) if rating_span else ''

    # 评价人数
    votes = ''
    if star_div:
        spans = star_div.find_all('span')
        if spans:
            vote_text = spans[-1].get_text(strip=True)
            votes = vote_text.replace('人评价', '').strip()

    # 一句话短评
    quote_span = bd.find('span', class_='inq') if bd else None
    quote = quote_span.get_text(strip=True) if quote_span else ''

    return {
        'rank': rank, 'title': title, 'director': director,
        'actors': actors, 'year': year, 'country': country,
        'genre': genre, 'rating': rating, 'votes': votes,
        'quote': quote, 'url': url
    }


def scrape_page(session, start):
    """
    抓取单页25部电影
    :param session: requests.Session
    :param start: 起始偏移量
    :return: list[dict]
    """
    resp = session.get(BASE_URL, params={'start': start}, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    items = soup.find_all('div', class_='item')
    logger.info(f'page start={start} got {len(items)} items')
    return [parse_item(it) for it in items]


def save_csv(movies, filepath):
    """
    保存到csv
    :param movies: list[dict]
    :param filepath: 文件路径
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(movies)
    logger.info(f'saved {len(movies)} records -> {filepath}')


def main():
    session = get_session()
    all_movies = []
    t_start = time.time()

    for start in range(0, 250, 25):
        try:
            page_data = scrape_page(session, start)
            all_movies.extend(page_data)
            # 别太快，豆瓣会ban
            time.sleep(1)
        except Exception as e:
            logger.error(f'page start={start} failed: {e}')
            continue

    t_fetch = time.time() - t_start
    logger.info(f'串行抓取完成: {len(all_movies)} 部, 爬取耗时 {t_fetch:.2f}s')

    save_csv(all_movies, CSV_FILE)
    t_total = time.time() - t_start
    logger.info(f'总耗时(含写入): {t_total:.2f}s')


if __name__ == '__main__':
    main()
