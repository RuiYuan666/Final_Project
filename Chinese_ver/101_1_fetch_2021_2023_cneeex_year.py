"""
CNEEEX 2021-2023年度全国碳市场数据采集（分年存储版本）
索引页:
  旧系统: https://www.cneeex.com/qgtpfqjy/mrgk/{年份}n/index.shtml (pages 1-10)
  新系统: https://www.cneeex.com/zcms/ui/catalog/15369/pc/index_11.shtml (pages 11+)
输出: 每年单独CSV文件
"""

import requests
import re
import csv
import os
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.cneeex.com/',
}

OUTPUT_DIR = '.'
HEADER = ['日期', '配额类型', '开盘价', '最高价', '最低价', '收盘价',
          '涨幅', '日成交量', '日成交额', '交易方式']


def fetch_with_retry(url, retries=3, timeout=20):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            # 强制使用 UTF-8 解码，避免 requests 误用 ISO-8859-1 导致中文乱码
            html_bytes = r.content
            html = html_bytes.decode('utf-8', errors='replace')
            return html, r.status_code
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError):
            print(f"    [重试 {attempt+1}/{retries}]")
            time.sleep(3)
    return None, 0


def parse_article(html, url):
    date_m = re.search(r'/(\d{4})-(\d{2})-(\d{2})/', url)
    if not date_m:
        return None
    date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}"

    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)

    # 允许 元 / 吨 之间有空格
    close_m = re.search(r'收盘价\s*(\d+\.\d{2})\s*元\s*/?\s*吨', text)
    if not close_m:
        return None
    close_p = float(close_m.group(1))

    change = 0.0
    cm = re.search(r'收盘价较前?一日(上涨|下跌)(\d+\.\d+)%', text)
    if cm:
        change = float(cm.group(2))
        if cm.group(1) == '下跌':
            change = -change
    else:
        cm2 = re.search(r'较开盘价(上涨|下跌)(\d+\.\d+)%', text)
        if cm2:
            change = float(cm2.group(2))
            if cm2.group(1) == '下跌':
                change = -change

    body_m = re.search(r'全国碳市场每日成交数据\d+ 发布时间', text)
    if body_m:
        seg_end = text.find('。', body_m.start())
        if seg_end < 0:
            seg_end = len(text)
        body_seg = text[body_m.start():seg_end + 1]
        prices = re.findall(r'(\d+\.\d{2})\s*元\s*/?\s*吨', body_seg)
    else:
        # Fallback: 找不到锚点时，用全文搜索价格
        prices = re.findall(r'(\d+\.\d{2})\s*元\s*/?\s*吨', text)

    if len(prices) >= 4:
        open_p, high_p, low_p = map(float, prices[:3])
    elif len(prices) == 3:
        open_p, high_p, low_p = map(float, prices[:3])
    elif len(prices) <= 2:
        open_p = round(close_p / (1 + change / 100), 2) if change != 0 else close_p
        high_p = low_p = close_p
    else:
        open_p = high_p = low_p = close_p

    # 成交量锚点
    listed_m = re.search(r'挂牌协议交易成交量\s*([\d,.]+)\s*吨', text)
    block_m  = re.search(r'大宗协议交易成交量\s*([\d,.]+)\s*吨', text)
    # 成交额锚点：挂牌的成交额用全文首次匹配；大宗的成交额必须在"大宗协议"之后
    listed_amt_m = re.search(r'成交额\s*([\d,.]+)\s*元', text)
    # 大宗成交额：从大宗成交量位置之后开始搜索
    if block_m:
        block_section = text[block_m.start():]
        block_amt_m = re.search(r'成交额\s*([\d,.]+)\s*元', block_section)
    else:
        block_amt_m = None

    def to_f(s):
        return float(s.replace(',', ''))

    return {
        'date': date_str,
        'open': open_p, 'high': high_p, 'low': low_p, 'close': close_p,
        'change': change,
        'listed_vol': to_f(listed_m.group(1)) if listed_m else 0.0,
        'listed_amt': to_f(listed_amt_m.group(1)) if listed_amt_m else 0.0,
        'block_vol': to_f(block_m.group(1)) if block_m else 0.0,
        'block_amt': to_f(block_amt_m.group(1)) if block_amt_m else 0.0,
    }


def get_article_urls_old_system(year):
    """旧分页系统: /qgtpfqjy/mrgk/{year}n/index_N.shtml"""
    base = f'https://www.cneeex.com/qgtpfqjy/mrgk/{year}n/'
    urls = []
    for page in range(1, 100):
        page_url = base + ('index.shtml' if page == 1 else f'index_{page}.shtml')
        html, status = fetch_with_retry(page_url, retries=3, timeout=30)
        if not html or status != 200:
            break
        found = re.findall(r'href="(/c/(\d{4})-\d{2}-\d{2}/\d+\.shtml)"', html)
        page_urls = []
        for url, y in found:
            if y == year:
                page_urls.append('https://www.cneeex.com' + url)
        if not page_urls:
            break
        urls.extend(page_urls)
        time.sleep(0.5)
    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def get_article_urls_new_system(year, catalog_id='15369'):
    """新分页系统: /zcms/ui/catalog/{catalog_id}/pc/index_N.shtml"""
    urls = []
    for page in range(11, 200):
        page_url = (f'https://www.cneeex.com/zcms/ui/catalog/{catalog_id}/pc/index_11.shtml'
                    if page == 11 else
                    f'https://www.cneeex.com/zcms/ui/catalog/{catalog_id}/pc/index_{page}.shtml')
        html, status = fetch_with_retry(page_url, retries=3, timeout=30)
        if not html or status != 200:
            break
        found = re.findall(r'href="(https://www\.cneeex\.com/c/\d{4}-\d{2}-\d{2}/\d+\.shtml)"', html)
        page_urls = []
        for url in found:
            m = re.search(r'/c/(\d{4})-\d{2}-\d{2}/', url)
            if m and m.group(1) == year:
                page_urls.append(url)
        if not page_urls:
            break
        urls.extend(page_urls)
        time.sleep(0.5)
    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def main():
    YEAR_CONFIG = {
        '2021': ('ChinaCarbon_2021_C.csv', None),
        '2022': ('ChinaCarbon_2022_C.csv', '2022-12-31'),
        '2023': ('ChinaCarbon_2023_C.csv', '2023-08-25'),
    }

    print("=" * 60)
    print("CNEEEX 2021-2023年度碳市场数据采集")
    print("=" * 60)

    total_records = 0

    for year, (filename, end_date) in YEAR_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"处理 {year} 年数据...")

        old_urls = get_article_urls_old_system(year)
        print(f"  旧系统: {len(old_urls)} 条URL")

        new_urls = get_article_urls_new_system(year, catalog_id='15416' if year == '2023' else '15369')
        print(f"  新系统: {len(new_urls)} 条URL")

        seen = set(old_urls)
        all_urls = list(old_urls)
        for u in new_urls:
            if u not in seen:
                seen.add(u)
                all_urls.append(u)
        all_urls.sort(key=lambda u: re.search(r'/(\d{4}-\d{2}-\d{2})/', u).group(1))
        print(f"  合并去重后: {len(all_urls)} 条")

        records = []
        errors = []

        for i, url in enumerate(all_urls):
            date_m = re.search(r'/(\d{4}-\d{2}-\d{2})/', url)
            if date_m and end_date and date_m.group(1) > end_date:
                continue

            html, status = fetch_with_retry(url, retries=3, timeout=30)
            if not html or status != 200:
                errors.append((url, f'HTTP {status}'))
                continue

            data = parse_article(html, url)
            if not data:
                errors.append((url, '解析失败'))
                continue

            if data['listed_vol'] > 0:
                records.append([
                    data['date'], 'CEA',
                    data['open'], data['high'], data['low'], data['close'],
                    data['change'],
                    data['listed_vol'], data['listed_amt'],
                    '挂牌协议交易'
                ])
            if data['block_vol'] > 0:
                records.append([
                    data['date'], 'CEA',
                    data['open'], data['high'], data['low'], data['close'],
                    data['change'],
                    data['block_vol'], data['block_amt'],
                    '大宗协议交易'
                ])

            print(f"    [{i+1}/{len(all_urls)}] {data['date']} "
                  f"开={data['open']} 收={data['close']} "
                  f"挂={data['listed_vol']:.0f} 大={data['block_vol']:.0f}")
            time.sleep(0.3)

        out_path = os.path.join(OUTPUT_DIR, filename)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        records.sort(key=lambda r: r[0])
        with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            writer.writerows(records)

        dates = set(r[0] for r in records)
        print(f"\n  {year}年: {len(records)} 条记录, {len(dates)} 个交易日, {len(errors)} 失败")
        print(f"  已保存: {out_path}")
        total_records += len(records)

        if errors:
            print(f"  失败 ({len(errors)} 条):")
            for url, reason in errors[:5]:
                print(f"    {url} -> {reason}")

    print(f"\n{'='*60}")
    print(f"全部完成! 共 {total_records} 条记录")


if __name__ == '__main__':
    main()
