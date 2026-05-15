"""
CNEEEX 2021-2023 National Carbon Market Data Collection
Index pages:
  Old system: https://www.cneeex.com/qgtpfqjy/mrgk/{year}n/index.shtml (pages 1-10)
  New system: https://www.cneeex.com/zcms/ui/catalog/15369/pc/index_11.shtml (pages 11+)
Output: Separate CSV per year
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
HEADER = ['Date', 'QuotaType', 'Open', 'High', 'Low', 'Close',
          'Change', 'DailyVolume', 'DailyAmount', 'TradeType']


def fetch_with_retry(url, retries=3, timeout=20):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            html_bytes = r.content
            html = html_bytes.decode('utf-8', errors='replace')
            return html, r.status_code
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError):
            print(f"    [Retry {attempt+1}/{retries}]")
            time.sleep(3)
    return None, 0


def parse_article(html, url):
    date_m = re.search(r'/(\d{4})-(\d{2})-(\d{2})/', url)
    if not date_m:
        return None
    date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}"

    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)

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

    listed_m = re.search(r'挂牌协议交易成交量\s*([\d,.]+)\s*吨', text)
    block_m  = re.search(r'大宗协议交易成交量\s*([\d,.]+)\s*吨', text)
    listed_amt_m = re.search(r'成交额\s*([\d,.]+)\s*元', text)
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
    """Old pagination: /qgtpfqjy/mrgk/{year}n/index_N.shtml"""
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
    """New pagination: /zcms/ui/catalog/{catalog_id}/pc/index_N.shtml"""
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
        '2021': ('ChinaCarbon_2021.csv', None),
        '2022': ('ChinaCarbon_2022.csv', '2022-12-31'),
        '2023': ('ChinaCarbon_2023.csv', '2023-08-25'),
    }

    print("=" * 60)
    print("CNEEEX 2021-2023 National Carbon Market Data Collection")
    print("=" * 60)

    total_records = 0

    for year, (filename, end_date) in YEAR_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Processing year {year}...")

        old_urls = get_article_urls_old_system(year)
        print(f"  Old system: {len(old_urls)} URLs")

        new_urls = get_article_urls_new_system(year, catalog_id='15416' if year == '2023' else '15369')
        print(f"  New system: {len(new_urls)} URLs")

        seen = set(old_urls)
        all_urls = list(old_urls)
        for u in new_urls:
            if u not in seen:
                seen.add(u)
                all_urls.append(u)
        all_urls.sort(key=lambda u: re.search(r'/(\d{4}-\d{2}-\d{2})/', u).group(1))
        print(f"  After dedup: {len(all_urls)} URLs")

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
                errors.append((url, 'Parse failed'))
                continue

            if data['listed_vol'] > 0:
                records.append([
                    data['date'], 'CEA',
                    data['open'], data['high'], data['low'], data['close'],
                    data['change'],
                    data['listed_vol'], data['listed_amt'],
                    'Listed'
                ])
            if data['block_vol'] > 0:
                records.append([
                    data['date'], 'CEA',
                    data['open'], data['high'], data['low'], data['close'],
                    data['change'],
                    data['block_vol'], data['block_amt'],
                    'Block'
                ])

            print(f"    [{i+1}/{len(all_urls)}] {data['date']} "
                  f"O={data['open']} C={data['close']} "
                  f"L={data['listed_vol']:.0f} B={data['block_vol']:.0f}")
            time.sleep(0.3)

        out_path = os.path.join(OUTPUT_DIR, filename)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        records.sort(key=lambda r: r[0])
        with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            writer.writerows(records)

        dates = set(r[0] for r in records)
        print(f"\n  {year}: {len(records)} records, {len(dates)} trading days, {len(errors)} failures")
        print(f"  Saved: {out_path}")
        total_records += len(records)

        if errors:
            print(f"  Failures ({len(errors)}):")
            for url, reason in errors[:5]:
                print(f"    {url} -> {reason}")

    print(f"\n{'='*60}")
    print(f"Done! Total {total_records} records")


if __name__ == '__main__':
    main()
