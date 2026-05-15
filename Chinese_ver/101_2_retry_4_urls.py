"""
重试脚本：补采4条失败的CNEEEX文章
"""
import requests
import re
import csv
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.cneeex.com/',
}

OUTPUT_DIR = '.'

FAILED_URLS = [
    'https://www.cneeex.com/c/2023-06-30/494294.shtml',
    'https://www.cneeex.com/c/2023-07-06/494304.shtml',
    'https://www.cneeex.com/c/2023-07-17/494330.shtml',
    'https://www.cneeex.com/c/2023-08-10/494414.shtml',
]

TARGET_CSV = os.path.join(OUTPUT_DIR, 'ChinaCarbon_2023_C.csv')


def fetch_with_retry(url, retries=5, timeout=45):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.encoding = 'utf-8'
            return r.text, r.status_code
        except Exception as e:
            print(f'  [重试 {attempt+1}/{retries}] {e}')
            import time
            time.sleep(5)
    return None, 0


def parse_article(html, url):
    date_m = re.search(r'/(\d{4})-(\d{2})-(\d{2})/', url)
    if not date_m:
        return None
    date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}"

    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)

    close_m = re.search(r'收盘价(\d+\.\d{2})元/吨', text)
    if not close_m:
        print(f'  [{date_str}] 收盘价未找到')
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
    if not body_m:
        print(f'  [{date_str}] 正文章节未找到')
        return None
    seg_end = text.find('。', body_m.start())
    if seg_end < 0:
        seg_end = len(text)
    body_seg = text[body_m.start():seg_end + 1]
    prices = re.findall(r'(\d+\.\d{2})元/吨', body_seg)

    if len(prices) >= 4:
        open_p, high_p, low_p = map(float, prices[:3])
    elif len(prices) == 3:
        open_p, high_p, low_p = map(float, prices[:3])
    elif len(prices) <= 2:
        open_p = round(close_p / (1 + change / 100), 2) if change != 0 else close_p
        high_p = low_p = close_p
    else:
        open_p = high_p = low_p = close_p

    listed_m = re.search(r'挂牌协议交易成交量([\d,.]+)吨', text)
    block_m  = re.search(r'大宗协议交易成交量([\d,.]+)吨', text)
    listed_amt_m = re.search(r'挂牌协议交易成交量[\d,.]+吨，成交额([\d,.]+)元', text)
    block_amt_m  = re.search(r'大宗协议交易成交量[\d,.]+吨，成交额([\d,.]+)元', text)

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


def load_existing_csv(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader, None)
        return set(row[0] for row in reader)


def main():
    print('开始重试4条失败记录...\n')

    for url in FAILED_URLS:
        date_m = re.search(r'/(\d{4}-\d{2}-\d{2})/', url)
        date_str = date_m.group(1) if date_m else 'unknown'

        print(f'处理: {date_str}')
        html, status = fetch_with_retry(url)
        if not html or status != 200:
            print(f'  -> HTTP {status}, 跳过')
            continue

        data = parse_article(html, url)
        if not data:
            print(f'  -> 解析失败, 跳过')
            continue

        records = []
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

        if not records:
            print(f'  -> 无成交量, 跳过')
            continue

        # 追加到CSV
        HEADER = ['日期', '配额类型', '开盘价', '最高价', '最低价', '收盘价',
                  '涨幅', '日成交量', '日成交额', '交易方式']
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 读取已有数据，去重
        existing_dates = load_existing_csv(TARGET_CSV)
        new_records = [r for r in records if r[0] not in existing_dates]

        if not new_records:
            print(f'  -> 已存在, 跳过')
            continue

        # 追加写
        with open(TARGET_CSV, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if os.path.getsize(TARGET_CSV) == 0:
                writer.writerow(HEADER)
            writer.writerows(new_records)

        for r in new_records:
            print(f'  -> 成功写入: {r[0]} {r[9]} 开={r[2]} 收={r[5]} 挂={r[7]:.0f} 大={r[8]}')

    print('\n完成!')


if __name__ == '__main__':
    main()
