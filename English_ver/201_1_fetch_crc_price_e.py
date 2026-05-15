#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download China Carbon Market Trading & Settlement Data
Data Source: https://www.chinacrc.net.cn/list/101.html

~10 records per page, total 116 pages.
This script downloads all available data.

Column Structure (11 columns, no header row):
  [0] Trading Variety
  [1] Date
  [2] Close Price (CNY/Ton)
  [3] Highest Price (CNY/Ton)
  [4] Lowest Price (CNY/Ton)
  [5] Auction Volume (Ton)
  [6] Auction Amount (CNY)
  [7] Block Volume (Ton)
  [8] Block Amount (CNY)
  [9] Total Volume (Ton)
  [10] Total Amount (CNY)
"""
import os
import re
import time
import requests
import csv
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(SCRIPT_DIR, os.path.pardir))
OUT_DIR = SCRIPT_DIR
OUT_FILE = os.path.join(OUT_DIR, "CRC_price_e.csv")

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
    """Clean string and return float; return 0.0 if invalid"""
    if not s or s.strip() in ('-', '—', ''):
        return 0.0
    return float(s.strip().replace(',', ''))


def parse_page(html):
    """Parse HTML table and return list of data records"""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []

    records = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) != 11:
            continue

        try:
            variety = cols[0].get_text(strip=True)
            date_raw = cols[1].get_text(strip=True)
            close = clean_num(cols[2].get_text(strip=True))
            high = clean_num(cols[3].get_text(strip=True))
            low = clean_num(cols[4].get_text(strip=True))
            auction_vol = clean_num(cols[5].get_text(strip=True))
            auction_amt = clean_num(cols[6].get_text(strip=True))
            block_vol = clean_num(cols[7].get_text(strip=True))
            block_amt = clean_num(cols[8].get_text(strip=True))
            total_vol = clean_num(cols[9].get_text(strip=True))
            total_amt = clean_num(cols[10].get_text(strip=True))

            date = date_raw.replace('.', '-')

            records.append({
                'date': date,
                'variety': variety,
                'close_cny_ton': close,
                'high_cny_ton': high,
                'low_cny_ton': low,
                'auction_vol_ton': auction_vol,
                'auction_amt_cny': auction_amt,
                'block_vol_ton': block_vol,
                'block_amt_cny': block_amt,
                'total_vol_ton': total_vol,
                'total_amt_cny': total_amt,
            })
        except Exception as e:
            print(f"  [!] Failed to parse row: {e}")
            continue

    return records


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_records = []
    pages = range(1, 117)

    print(f"=== China Carbon Market Data Downloader ===\n")
    for page in pages:
        print(f"Downloading page {page}...", end=" ", flush=True)
        try:
            html = fetch_page(page)
            recs = parse_page(html)
            if not recs:
                print("No data, stopping")
                break

            oldest = min(r['date'] for r in recs)
            print(f"{len(recs)} records (oldest: {oldest})")
            all_records.extend(recs)

            if oldest < '2026-01-01' and page > 1:
                print(f"Reached data before 2026-01-01, enough data acquired")
                break
        except Exception as e:
            print(f"Failed: {e}")
        time.sleep(0.5)

    if not all_records:
        print("No data acquired!")
        return

    before = len(all_records)
    all_records = [r for r in all_records if (r['total_vol_ton'] or 0) > 0]
    print(f"Filter zero-volume records: {before} -> {len(all_records)}")

    before2 = len(all_records)
    all_records = [r for r in all_records if r['date'] >= '2026-01-01']
    print(f"Filter pre-2026 records: {before2} -> {len(all_records)}")

    ok = fail = 0
    for r in all_records:
        gv = r['auction_vol_ton']
        dv = r['block_vol_ton']
        tv = r['total_vol_ton']
        calc = gv + dv
        if abs(calc - tv) < 1:
            ok += 1
        else:
            fail += 1
    print(f"Data validation: {ok} passed, {fail} failed")

    stacked = []
    for r in all_records:
        base = {
            'date': r['date'],
            'trading_variety': r['variety'],
            'close_price_cny_ton': r['close_cny_ton'],
            'highest_price_cny_ton': r['high_cny_ton'],
            'lowest_price_cny_ton': r['low_cny_ton'],
        }
        if r['auction_vol_ton'] > 0:
            stacked.append({
                **base,
                'trading_type': 'Auction',
                'volume_ton': r['auction_vol_ton'],
                'amount_cny': r['auction_amt_cny'],
            })
        if r['block_vol_ton'] > 0:
            stacked.append({
                **base,
                'trading_type': 'Block',
                'volume_ton': r['block_vol_ton'],
                'amount_cny': r['block_amt_cny'],
            })
    print(f"Stacked to flat table: {len(stacked)} records")
    all_records = stacked

    def _norm(s):
        parts = s.strip().split('-')
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"

    all_records.sort(key=lambda r: _norm(r['date']))

    cols = [
        'date', 'trading_variety', 'trading_type',
        'close_price_cny_ton', 'highest_price_cny_ton', 'lowest_price_cny_ton',
        'volume_ton', 'amount_cny',
    ]

    with open(OUT_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nSaved to: {OUT_FILE}")
    print(f"Total records: {len(all_records)}")
    print(f"Date range: {all_records[0]['date']} ~ {all_records[-1]['date']}")

    print(f"\nFirst 10 records:")
    for r in all_records[:10]:
        vol = int(r['volume_ton']) if r['volume_ton'] else 0
        print(f"  {r['date']}  {r['trading_type']}  Close={r['close_price_cny_ton']}  Volume={vol:>12,}")


if __name__ == '__main__':
    main()