#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载中国碳排放权注册登记结算有限责任公司（CRC）全国碳市场交易结算信息
数据来源：https://www.chinacrc.net.cn/list/101.html

每页约10条记录，共116页。本脚本下载前5页（共约50条）。

列结构（共11列，无表头行）：
  [0] 交易品种
  [1] 日期
  [2] 收盘价（元/吨）
  [3] 最高价（元/吨）
  [4] 最低价（元/吨）
  [5] 挂牌成交量（吨）
  [6] 挂牌成交额（元）
  [7] 大宗成交量（吨）
  [8] 大宗成交额（元）
  [9] 当日总成交量（吨）
  [10] 当日总成交额（元）
"""
import os, re, time, requests, csv
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT    = os.path.normpath(os.path.join(SCRIPT_DIR, os.path.pardir))
OUT_DIR    = SCRIPT_DIR  # 与py文件同一目录
OUT_FILE   = os.path.join(OUT_DIR, "CRC_price_C.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
BASE_URL = "https://www.chinacrc.net.cn/list/101.html"

def fetch_page(page):
    url = f"{BASE_URL}?page={page}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.encoding = 'utf-8'
    return r.text

def clean_num(s):
    """清理数字字符串，返回浮点数；无效返回0.0"""
    if not s or s.strip() in ('-', '—', ''):
        return 0.0
    return float(s.strip().replace(',', ''))

def parse_page(html):
    """解析CRC页面HTML表格（无表头行），返回记录列表"""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []

    records = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) != 11:
            continue  # 跳过非数据行

        try:
            variety  = cols[0].get_text(strip=True)
            date_raw = cols[1].get_text(strip=True)  # "2026.04.30"
            close    = clean_num(cols[2].get_text(strip=True))
            high     = clean_num(cols[3].get_text(strip=True))
            low      = clean_num(cols[4].get_text(strip=True))
            gua_vol  = clean_num(cols[5].get_text(strip=True))
            gua_amt  = clean_num(cols[6].get_text(strip=True))
            da_vol   = clean_num(cols[7].get_text(strip=True))
            da_amt   = clean_num(cols[8].get_text(strip=True))
            total_vol = clean_num(cols[9].get_text(strip=True))
            total_amt = clean_num(cols[10].get_text(strip=True))

            # 转换日期格式 2026.04.30 -> 2026-04-30
            date = date_raw.replace('.', '-')

            records.append({
                '日期': date,
                '交易品种': variety,
                '收盘价（元/吨）': close,
                '最高价（元/吨）': high,
                '最低价（元/吨）': low,
                '挂牌成交量（吨）': gua_vol,
                '挂牌成交额（元）': gua_amt,
                '大宗成交量（吨）': da_vol,
                '大宗成交额（元）': da_amt,
                '当日总成交量（吨）': total_vol,
                '当日总成交额（元）': total_amt,
            })
        except Exception as e:
            print(f"  [!] 解析行失败: {e}")
            continue

    return records

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    all_records = []
    pages = range(1, 117)  # 全量下载（116页）

    print(f"=== CRC 碳市场交易结算信息下载 ===\n")
    for page in pages:
        print(f"下载第 {page} 页...", end=" ", flush=True)
        try:
            html = fetch_page(page)
            recs = parse_page(html)
            if not recs:
                print("无数据，停止")
                break
            # 若最早记录已早于2026-01-01，且当前页有数据则可停止
            oldest = min(r['日期'] for r in recs)
            print(f"{len(recs)} 条（最旧:{oldest}）")
            all_records.extend(recs)
            # 跨过2026-01-01后继续多拿一页作为保险，然后停止
            if oldest < '2026-01-01' and page > 1:
                print(f"已越过2026-01-01，获取足够数据")
                break
        except Exception as e:
            print(f"失败: {e}")
        time.sleep(0.5)

    if not all_records:
        print("未获取到任何数据！")
        return

    # 过滤：剔除当日总成交量=0的记录（无交易）
    before = len(all_records)
    all_records = [r for r in all_records if (r['当日总成交量（吨）'] or 0) > 0]
    print(f"过滤无成交记录: {before} -> {len(all_records)} 条")

    # 过滤：仅保留2026-01-01及以后的数据
    before2 = len(all_records)
    all_records = [r for r in all_records if r['日期'] >= '2026-01-01']
    print(f"过滤2026年前数据: {before2} -> {len(all_records)} 条")

    # 核实：当日总成交量 = 挂牌成交量 + 大宗成交量
    ok = fail = 0
    for r in all_records:
        gv = r['挂牌成交量（吨）']
        dv = r['大宗成交量（吨）']
        tv = r['当日总成交量（吨）']
        calc = gv + dv
        if abs(calc - tv) < 1:
            ok += 1
        else:
            fail += 1
    print(f"数据核实: {ok}通过, {fail}失败")

    # 转为一级表：每条记录含一种交易类型
    stacked = []
    for r in all_records:
        base = {
            '日期': r['日期'],
            '交易品种': r['交易品种'],
            '收盘价（元/吨）': r['收盘价（元/吨）'],
            '最高价（元/吨）': r['最高价（元/吨）'],
            '最低价（元/吨）': r['最低价（元/吨）'],
        }
        if r['挂牌成交量（吨）'] > 0:
            stacked.append({
                **base,
                '交易类型': '挂牌协议',
                '成交量（吨）': r['挂牌成交量（吨）'],
                '成交额（元）': r['挂牌成交额（元）'],
            })
        if r['大宗成交量（吨）'] > 0:
            stacked.append({
                **base,
                '交易类型': '大宗协议',
                '成交量（吨）': r['大宗成交量（吨）'],
                '成交额（元）': r['大宗成交额（元）'],
            })
    print(f"一级表展开: {len(stacked)} 条")
    all_records = stacked

    # 按日期升序排列
       def _norm(s):
        parts = s.strip().split('-')
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    all_records.sort(key=lambda r: _norm(r['日期']))

    # 写入一级表CSV（UTF-8-BOM）
    cols = [
        '日期', '交易品种', '交易类型',
        '收盘价（元/吨）', '最高价（元/吨）', '最低价（元/吨）',
        '成交量（吨）', '成交额（元）',
    ]
    with open(OUT_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n已保存: {OUT_FILE}")
    print(f"总记录: {len(all_records)} 条（一级表）")
    print(f"日期范围: {all_records[0]['日期']} ~ {all_records[-1]['日期']}")
    print(f"\n前10条:")
    for r in all_records[:10]:
        vol = int(r['成交量（吨）']) if r['成交量（吨）'] else 0
        print(f"  {r['日期']}  {r['交易类型']}  收={r['收盘价（元/吨）']}  成交量={vol:>12,}")

if __name__ == '__main__':
    main()
