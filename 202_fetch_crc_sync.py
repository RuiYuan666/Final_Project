#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRC 碳市场数据增量同步脚本
- 检查网站最新数据日期
- 与本地CSV对比，若网站更新则下载并追加
- 输出目录与本脚本同一文件夹
"""
import os, time, requests, csv
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE   = os.path.join(SCRIPT_DIR, "CRC_price_C.csv")
HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE_URL   = "https://www.chinacrc.net.cn/list/101.html"

def fetch_page(page):
    url = f"{BASE_URL}?page={page}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.encoding = 'utf-8'
    return r.text

def clean_num(s):
    if not s or s.strip() in ('-', '—', ''):
        return 0.0
    return float(s.strip().replace(',', ''))

def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []
    records = []
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) != 11:
            continue
        try:
            records.append({
                '日期': cols[1].get_text(strip=True).replace('.', '-'),
                '交易品种': cols[0].get_text(strip=True),
                '收盘价（元/吨）': clean_num(cols[2].get_text(strip=True)),
                '最高价（元/吨）': clean_num(cols[3].get_text(strip=True)),
                '最低价（元/吨）': clean_num(cols[4].get_text(strip=True)),
                '挂牌成交量（吨）': clean_num(cols[5].get_text(strip=True)),
                '挂牌成交额（元）': clean_num(cols[6].get_text(strip=True)),
                '大宗成交量（吨）': clean_num(cols[7].get_text(strip=True)),
                '大宗成交额（元）': clean_num(cols[8].get_text(strip=True)),
                '当日总成交量（吨）': clean_num(cols[9].get_text(strip=True)),
                '当日总成交额（元）': clean_num(cols[10].get_text(strip=True)),
            })
        except:
            continue
    return records

def get_site_latest_date():
    """获取网站最新数据日期（从第1页第1行获取）"""
    html = fetch_page(1)
    recs = parse_page(html)
    if not recs:
        return None
    return max(r['日期'] for r in recs)

def _norm(s):
    """统一日期为 YYYY-MM-DD 格式，供比较用"""
    s = s.strip()
    if not s:
        return '0000-00-00'
    parts = s.split('-')
    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"

def get_csv_latest_date():
    """获取本地CSV最新数据日期（规范化比较）"""
    if not os.path.exists(CSV_FILE):
        return None
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return None
    return max(_norm(r['日期']) for r in rows)

def need_download_since(csv_latest):
    """
    从网站下载所有数据，返回 csv_latest 日期之后的新记录（宽表格式）。
    下载到越过2026-01-01为止。
    """
    all_records = []
    for page in range(1, 117):
        recs = parse_page(fetch_page(page))
        if not recs:
            break
        oldest = min(r['日期'] for r in recs)
        print(f"  第{page}页: {len(recs)}条, 最旧={oldest}")
        all_records.extend(recs)
        if oldest < '2026-01-01' and page > 1:
            break
        time.sleep(0.3)

    # 过滤无成交 + 仅保留 csv_latest 之后的新数据
    new_recs = [r for r in all_records
                if r['当日总成交量（吨）'] > 0
                and r['日期'] > csv_latest
                and r['日期'] >= '2026-01-01']
    return new_recs

def wide_to_stacked(records):
    """宽表转一级表"""
    stacked = []
    base_keys = ['日期', '交易品种', '收盘价（元/吨）', '最高价（元/吨）', '最低价（元/吨）']
    for r in records:
        base = {k: r[k] for k in base_keys}
        if r['挂牌成交量（吨）'] > 0:
            stacked.append({**base, '交易类型': '挂牌协议',
                '成交量（吨）': r['挂牌成交量（吨）'], '成交额（元）': r['挂牌成交额（元）']})
        if r['大宗成交量（吨）'] > 0:
            stacked.append({**base, '交易类型': '大宗协议',
                '成交量（吨）': r['大宗成交量（吨）'], '成交额（元）': r['大宗成交额（元）']})
    return stacked

def verify(records):
    """核实：当日总成交量 = 挂牌 + 大宗"""
    ok = fail = 0
    for r in records:
        if abs(r['挂牌成交量（吨）'] + r['大宗成交量（吨）'] - r['当日总成交量（吨）']) < 1:
            ok += 1
        else:
            fail += 1
    return ok, fail

def main():
    print("=== CRC 碳市场数据增量同步 ===\n")

    # Step 1: 网站最新日期
    print("[步骤1] 获取网站最新日期...")
    site_latest = get_site_latest_date()
    print(f"  网站最新: {site_latest}")

    # Step 2: 本地CSV最新日期
    print("\n[步骤2] 获取本地数据最新日期...")
    csv_latest = get_csv_latest_date()
    print(f"  本地最新: {csv_latest}")

    # Step 3: 日期对比
    print("\n[步骤3] 日期对比...")
    if csv_latest is None:
        print("  本地无文件，需全量下载（从2026-01-01起）")
        csv_latest = '2025-12-31'  # 触发全量下载

    if site_latest <= csv_latest:
        print(f"  本地已是最新（{csv_latest} >= 网站 {site_latest}），无需更新")
        return

    print(f"  网站更新，需下载 {csv_latest} 之后的新数据...")

    # Step 4: 下载新数据
    print("\n[步骤4] 下载新数据...")
    new_wide = need_download_since(csv_latest)

    if not new_wide:
        print("  未找到新数据，可能网站无新增记录")
        return

    # 核实新数据
    ok, fail = verify(new_wide)
    print(f"  下载到 {len(new_wide)} 条新记录（核实: {ok}通过, {fail}失败）")

    # Step 5: 转为一级表
    new_stacked = wide_to_stacked(new_wide)
    print(f"  一级表展开: {len(new_stacked)} 条")

    # Step 6: 合并写入本地CSV
    print("\n[步骤5] 合并写入本地CSV...")

    # 读取现有数据
    existing = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            existing = [row for row in reader if row.get('日期', '').strip()]
        print(f"  现有记录: {len(existing)} 条")

    # 去重：移除与新数据日期+交易类型重复的记录
    new_keys = {(r['日期'], r['交易类型']) for r in new_stacked}
    merged = [r for r in existing if (r['日期'], r['交易类型']) not in new_keys]
    merged.extend(new_stacked)
    merged.sort(key=lambda r: _norm(r['日期']))

    # 写入
    cols = ['日期', '交易品种', '交易类型', '收盘价（元/吨）', '最高价（元/吨）',
            '最低价（元/吨）', '成交量（吨）', '成交额（元）']
    with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(merged)

    print(f"  已保存: {CSV_FILE}")
    print(f"  总记录: {len(merged)} 条 | {merged[0]['日期']} ~ {merged[-1]['日期']}")
    print(f"  新增: {len(new_stacked)} 条")

if __name__ == '__main__':
    main()
