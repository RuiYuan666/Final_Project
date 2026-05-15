#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRC Carbon Market Data Incremental Sync Script
- Check latest data date on the website
- Compare with local CSV, download and append if updated
- Output directory: same folder as this script
"""
import os
import time
import requests
import csv
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE   = os.path.join(SCRIPT_DIR, "CRC_price_e.csv")
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
                'date': cols[1].get_text(strip=True).replace('.', '-'),
                'trading_product': cols[0].get_text(strip=True),
                'close_price_cny_per_ton': clean_num(cols[2].get_text(strip=True)),
                'highest_price_cny_per_ton': clean_num(cols[3].get_text(strip=True)),
                'lowest_price_cny_per_ton': clean_num(cols[4].get_text(strip=True)),
                'auction_volume_tons': clean_num(cols[5].get_text(strip=True)),
                'auction_amount_cny': clean_num(cols[6].get_text(strip=True)),
                'block_volume_tons': clean_num(cols[7].get_text(strip=True)),
                'block_amount_cny': clean_num(cols[8].get_text(strip=True)),
                'total_volume_tons': clean_num(cols[9].get_text(strip=True)),
                'total_amount_cny': clean_num(cols[10].get_text(strip=True)),
            })
        except:
            continue
    return records

def get_site_latest_date():
    """Get latest data date from the website (first row of page 1)"""
    html = fetch_page(1)
    recs = parse_page(html)
    if not recs:
        return None
    return max(r['date'] for r in recs)

def _norm(s):
    """Normalize date to YYYY-MM-DD format for comparison"""
    s = s.strip()
    if not s:
        return '0000-00-00'
    parts = s.split('-')
    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"

def get_csv_latest_date():
    """Get latest data date from local CSV (normalized comparison)"""
    if not os.path.exists(CSV_FILE):
        return None
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return None
    return max(_norm(r['date']) for r in rows)

def need_download_since(csv_latest):
    """
    Download all data from the website, return new records after csv_latest date (wide format).
    Stop when data before 2026-01-01 is reached.
    """
    all_records = []
    for page in range(1, 117):
        recs = parse_page(fetch_page(page))
        if not recs:
            break
        oldest = min(r['date'] for r in recs)
        print(f"  Page {page}: {len(recs)} records, oldest={oldest}")
        all_records.extend(recs)
        if oldest < '2026-01-01' and page > 1:
            break
        time.sleep(0.3)

    # Filter non-zero volume + new data after csv_latest
    new_recs = [r for r in all_records
                if r['total_volume_tons'] > 0
                and r['date'] > csv_latest
                and r['date'] >= '2026-01-01']
    return new_recs

def wide_to_stacked(records):
    """Convert wide table to stacked (long) format"""
    stacked = []
    base_keys = ['date', 'trading_product', 'close_price_cny_per_ton',
                 'highest_price_cny_per_ton', 'lowest_price_cny_per_ton']
    for r in records:
        base = {k: r[k] for k in base_keys}
        if r['auction_volume_tons'] > 0:
            stacked.append({
                **base, 'trading_type': 'Auction Agreement',
                'volume_tons': r['auction_volume_tons'], 'amount_cny': r['auction_amount_cny']
            })
        if r['block_volume_tons'] > 0:
            stacked.append({
                **base, 'trading_type': 'Block Agreement',
                'volume_tons': r['block_volume_tons'], 'amount_cny': r['block_amount_cny']
            })
    return stacked

def verify(records):
    """Verify: total daily volume = auction volume + block volume"""
    ok = fail = 0
    for r in records:
        if abs(r['auction_volume_tons'] + r['block_volume_tons'] - r['total_volume_tons']) < 1:
            ok += 1
        else:
            fail += 1
    return ok, fail

def main():
    print("=== CRC Carbon Market Data Incremental Sync ===\n")

    # Step 1: Get latest date from website
    print("[Step 1] Fetching latest date from website...")
    site_latest = get_site_latest_date()
    print(f"  Website latest: {site_latest}")

    # Step 2: Get latest date from local CSV
    print("\n[Step 2] Fetching latest date from local CSV...")
    csv_latest = get_csv_latest_date()
    print(f"  Local latest: {csv_latest}")

    # Step 3: Date comparison
    print("\n[Step 3] Comparing dates...")
    if csv_latest is None:
        print("  No local file found, full download required (from 2026-01-01)")
        csv_latest = '2025-12-31'

    if site_latest <= csv_latest:
        print(f"  Local data is up to date ({csv_latest} >= Website {site_latest}), no update needed")
        return

    print(f"  Website updated, downloading new data after {csv_latest}...")

    # Step 4: Download new data
    print("\n[Step 4] Downloading new data...")
    new_wide = need_download_since(csv_latest)

    if not new_wide:
        print("  No new data found, no new records on website")
        return

    # Validate new data
    ok, fail = verify(new_wide)
    print(f"  Downloaded {len(new_wide)} new records (Validation: {ok} passed, {fail} failed)")

    # Step 5: Convert to stacked format
    new_stacked = wide_to_stacked(new_wide)
    print(f"  Expanded to stacked table: {len(new_stacked)} records")

    # Step 6: Merge and write to local CSV
    print("\n[Step 5] Merging and writing to local CSV...")

    # Read existing data
    existing = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            existing = [row for row in reader if row.get('date', '').strip()]
        print(f"  Existing records: {len(existing)}")

    # Deduplicate
    new_keys = {(r['date'], r['trading_type']) for r in new_stacked}
    merged = [r for r in existing if (r['date'], r['trading_type']) not in new_keys]
    merged.extend(new_stacked)
    merged.sort(key=lambda r: _norm(r['date']))

    # Write final CSV
    cols = [
        'date', 'trading_product', 'trading_type',
        'close_price_cny_per_ton', 'highest_price_cny_per_ton', 'lowest_price_cny_per_ton',
        'volume_tons', 'amount_cny'
    ]
    with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(merged)

    print(f"  Saved to: {CSV_FILE}")
    print(f"  Total records: {len(merged)} | {merged[0]['date']} ~ {merged[-1]['date']}")
    print(f"  New records added: {len(new_stacked)}")

if __name__ == '__main__':
    main()