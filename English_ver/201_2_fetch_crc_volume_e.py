#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRC China Carbon Market Daily Trading Volume Crawler (Full English Version)
Collects all trading volume records from 2026 to present from https://www.chinacrc.net.cn

Data source: China Carbon Emissions Registry and Settlement Co., Ltd. (CRC)
Output: CRC_volume_english.csv (UTF-8-BOM encoded, Excel-compatible)

Full English Changes:
  - All code comments, logs, messages in English
  - All CSV output values in English (trade types, quota labels)
  - Clean, standardized English field names
  - Fully internationalized for non-Chinese users
"""
import os
import re
import time
import csv
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.chinacrc.net.cn"
INDEX_URL = "https://www.chinacrc.net.cn/list/18.html"
DATA_DIR = "."
OUT_FILE = os.path.join(DATA_DIR, "CRC_volume_english.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.chinacrc.net.cn/",
}

# Quota type regex patterns → ENGLISH normalized names
QUOTA_PATTERNS = [
    (re.compile(r"碳排放配额\s*19-20"), "CEA 2019-2020"),
    (re.compile(r"碳排放配额\s*21"), "CEA 2021"),
    (re.compile(r"碳排放配额\s*22"), "CEA 2022"),
    (re.compile(r"碳排放配额\s*23"), "CEA 2023"),
    (re.compile(r"碳排放配额\s*24"), "CEA 2024"),
    (re.compile(r"碳排放配额\s*25"), "CEA 2025"),
]

# Chinese trade types → mapped to ENGLISH
CHINESE_TO_ENGLISH_TRADE = {
    "挂牌协议交易": "Auction Trading",
    "大宗协议交易": "Block Trading",
    "单向竞价": "One-way Bidding"
}
TRADE_TYPES = set(CHINESE_TO_ENGLISH_TRADE.keys())

# Skip rows containing these keywords (Chinese + English)
SKIP_KEYWORDS = {
    "小计", "交易合计", "Subtotal", "Total",
    "交易情况", "成交量（吨）", "成交金额（元）",
    "Trading Summary", "Volume", "Amount"
}


def clean_num(s):
    """Convert cell text to clean numeric string: remove commas, replace '-' with 0."""
    if not s or s.strip() in ("-", "", "—"):
        return "0"
    return s.strip().replace(",", "")


def fetch_page(url, retries=3):
    """Fetch URL with retry mechanism. Return HTML or None on failure."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.encoding = r.apparent_encoding if r.apparent_encoding else 'utf-8'
            if r.status_code == 200:
                return r.text
            print(f"[HTTP {r.status_code}] Error fetching page")
        except Exception as e:
            print(f"[Attempt {attempt+1}] Connection error: {type(e).__name__}")
        time.sleep(3)
    return None


def parse_date(title_text):
    """Extract date in YYYY-MM-DD format from page title."""
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title_text)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
    return None


def parse_article(html, url):
    """
    Parse trading data table and return ENGLISH formatted records.
    Only records with daily volume > 0 are saved.
    Returns: (date_str, list_of_english_records)
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Get trading date
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    date_str = parse_date(title_text)
    if not date_str:
        url_match = re.search(r"/(\d{4})(\d{2})(\d{2})/", url)
        if url_match:
            date_str = f"{url_match.group(1)}-{url_match.group(2)}-{url_match.group(3)}"
    if not date_str:
        return None, []

    records = []
    current_quota_en = None

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue

            cell0 = cells[0]

            # Skip headers, totals, subtitles
            if cell0 in SKIP_KEYWORDS or cell0.startswith(("成交量", "成交金", "Volume")):
                continue

            # --------------------------
            # Row 1: Quota type row (6 columns)
            # --------------------------
            quota_match = None
            for pattern, quota_en in QUOTA_PATTERNS:
                if pattern.search(cell0):
                    quota_match = quota_en
                    break

            if quota_match:
                current_quota_en = quota_match
                if len(cells) >= 6:
                    cn_trade = cells[1]
                    if cn_trade not in TRADE_TYPES:
                        continue
                    trade_en = CHINESE_TO_ENGLISH_TRADE[cn_trade]
                    vol_d = clean_num(cells[2])
                    amt_d = clean_num(cells[3])
                    vol_c = clean_num(cells[4])
                    amt_c = clean_num(cells[5])

                    if float(vol_d) > 0:
                        records.append({
                            "date": date_str,
                            "quota_type": current_quota_en,
                            "trade_type": trade_en,
                            "daily_volume_tons": vol_d,
                            "daily_amount_cny": amt_d,
                            "cumulative_volume_tons": vol_c,
                            "cumulative_amount_cny": amt_c
                        })
                continue

            # --------------------------
            # Row 2: Trade type row (5 columns)
            # --------------------------
            cn_trade = cells[0]
            if cn_trade not in TRADE_TYPES or not current_quota_en:
                continue

            trade_en = CHINESE_TO_ENGLISH_TRADE[cn_trade]
            if len(cells) >= 5:
                vol_d = clean_num(cells[1])
                amt_d = clean_num(cells[2])
                vol_c = clean_num(cells[3])
                amt_c = clean_num(cells[4])

                if float(vol_d) > 0:
                    records.append({
                        "date": date_str,
                        "quota_type": current_quota_en,
                        "trade_type": trade_en,
                        "daily_volume_tons": vol_d,
                        "daily_amount_cny": amt_d,
                        "cumulative_volume_tons": vol_c,
                        "cumulative_amount_cny": amt_c
                    })

    return date_str, records


def get_article_urls(max_pages=200):
    """Crawl list pages and return all 2026 daily report URLs."""
    seen_urls = set()
    result_urls = []

    html = fetch_page(INDEX_URL)
    if not html:
        print("[Error] Failed to load index page")
        return []

    soup = BeautifulSoup(html, 'html.parser')

    # Get total pagination count
    total_pages = 1
    for a in soup.find_all("a", href=re.compile(r"page=\d+")):
        page_num = re.search(r"page=(\d+)", a.get("href", ""))
        if page_num:
            total_pages = max(total_pages, int(page_num.group(1)))
    print(f"Total index pages detected: {total_pages}")

    for page in range(1, total_pages + 1):
        print(f"Fetching index page {page}/{total_pages} ...", end=" ", flush=True)
        page_url = f"{INDEX_URL}?page={page}"
        html = fetch_page(page_url)

        if not html:
            print("FAILED")
            time.sleep(2)
            continue

        soup = BeautifulSoup(html, 'html.parser')
        added = 0

        for a in soup.find_all("a", href=re.compile(r"/view/\d+\.html")):
            href = a.get("href", "")
            title = a.get("title") or a.get_text(strip=True)

            # Only keep 2026 daily reports
            if not re.search(r"2026年\d+月\d+日", title):
                continue

            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                result_urls.append(full_url)
                added += 1

        print(f"Added {added} 2026 URLs | Total: {len(result_urls)}")

        # Early stop if no data in first 10 pages
        if page > 10 and len(result_urls) == 0:
            print("No 2026 articles found in first 10 pages — stopping pagination")
            break
        time.sleep(0.8)

    return result_urls


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load existing dates to avoid duplicates
    existing_dates = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dt = row.get("date", "").strip()
                if dt:
                    existing_dates.add(dt)

    if existing_dates:
        print(f"Loaded existing data: {len(existing_dates)} days | Range: {min(existing_dates)} to {max(existing_dates)}")

    # Get all daily report URLs
    article_urls = get_article_urls()
    if not article_urls:
        print("No 2026 trading reports found — program exited")
        return

    print(f"\nTotal reports to crawl: {len(article_urls)}")
    new_records = []
    skipped_duplicates = 0

    # Crawl each report
    for idx, url in enumerate(article_urls):
        print(f"[{idx+1}/{len(article_urls)}] Processing: {url}", end=" ... ")

        html = fetch_page(url)
        if not html:
            print("FETCH FAILED")
            time.sleep(2)
            continue

        date_str, records = parse_article(html, url)

        if not date_str:
            print("DATE PARSE FAILED — skipped")
            time.sleep(1)
            continue

        if date_str in existing_dates:
            print(f"ALREADY EXISTS ({date_str}) — skipped")
            skipped_duplicates += 1
            time.sleep(0.5)
            continue

        if records:
            new_records.extend(records)
            print(f"{date_str}: Added {len(records)} valid records")
        else:
            print(f"{date_str}: No valid trading data")

        time.sleep(1)

    # Summary
    print(f"\n=== Crawling Finished ===")
    print(f"New articles processed: {len(article_urls) - skipped_duplicates}")
    print(f"New trading records saved: {len(new_records)}")

    # Save to CSV
    if new_records:
        file_exists = os.path.exists(OUT_FILE)
        with open(OUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
            fieldnames = [
                "date", "quota_type", "trade_type",
                "daily_volume_tons", "daily_amount_cny",
                "cumulative_volume_tons", "cumulative_amount_cny"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_records)

        print(f"\nData successfully saved to: {OUT_FILE}")
        with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
            total_lines = len(f.readlines())
        print(f"Total lines in CSV (including header): {total_lines}")

        # Show sample
        print("\n=== Preview: First 5 English Records ===")
        with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                print(
                    f"{row['date']} | {row['quota_type']} | {row['trade_type']} | "
                    f"Daily Vol: {row['daily_volume_tons']} tons"
                )
    else:
        print("\nNo new trading data to save.")


if __name__ == "__main__":
    main()