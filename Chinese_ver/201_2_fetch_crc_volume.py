#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRC全国碳市场交易结算信息日报
从 https://www.chinacrc.net.cn 采集2026年至今所有有成交量的记录
"""
import os, re, time, csv, requests
from bs4 import BeautifulSoup

BASE_URL  = "https://www.chinacrc.net.cn"
INDEX_URL = "https://www.chinacrc.net.cn/list/18.html"
DATA_DIR  = "."
OUT_FILE  = os.path.join(DATA_DIR, "CRC_volume_C.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.chinacrc.net.cn/",
}

QUOTA_PATTERNS = [
    (re.compile(r"碳排放配额\s*19-20"), "CEA19-20"),
    (re.compile(r"碳排放配额\s*21"),    "CEA21"),
    (re.compile(r"碳排放配额\s*22"),    "CEA22"),
    (re.compile(r"碳排放配额\s*23"),    "CEA23"),
    (re.compile(r"碳排放配额\s*24"),    "CEA24"),
    (re.compile(r"碳排放配额\s*25"),    "CEA25"),
]

TX_TYPES = {"挂牌协议交易", "大宗协议交易", "单向竞价"}

def clean_num(s):
    if not s or s.strip() in ("-", "", "—"):
        return "0"
    return s.strip().replace(",", "")

def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.encoding = "utf-8"
            if r.status_code == 200:
                return r.text
            print(f"  [HTTP {r.status_code}]")
        except Exception as e:
            print(f"  [Error {attempt+1}] {type(e).__name__}")
            time.sleep(3)
    return None

def parse_date(title_text):
    """从页面标题提取日期"""
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title_text)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return None

def parse_article(html, url):
    """
    返回: (date_str, [record_dict, ...])
    record_dict: {日期, 配额类型, 交易方式, 本日成交量_吨, 本日成交额_元, 累计成交量_吨, 累计成交额_元}
    """
    soup = BeautifulSoup(html, "html.parser")

    # 提取日期
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    date_str = parse_date(title_text)
    if not date_str:
        # 备用：从URL
        m = re.search(r"/(\d{4})(\d{2})(\d{2})/", url)
        if m:
            date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if not date_str:
        return None, []

    records = []
    current_quota = None

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue

            cell0 = cells[0]

            # ---- 跳过汇总行 ----
            if cell0 in ("小计", "交易合计", "合计"):
                continue

            # ---- 检测配额类型行（6列，且第一列匹配配额模式）----
            quota_match = None
            for pat, name in QUOTA_PATTERNS:
                if pat.search(cell0):
                    quota_match = name
                    break

            if quota_match:
                current_quota = quota_match
                # 6列行: [配额类型, 交易方式, 本日vol, 本日amt, 累计vol, 累计amt]
                if len(cells) >= 6 and cells[2].strip() not in ("-", "", "—"):
                    tx_type = cells[1]
                    if tx_type in TX_TYPES:
                        vol_t = clean_num(cells[2])
                        amt_t = clean_num(cells[3])
                        vol_c = clean_num(cells[4])
                        amt_c = clean_num(cells[5])
                        if float(vol_t) > 0:
                            records.append({
                                "日期": date_str,
                                "配额类型": current_quota,
                                "交易方式": tx_type,
                                "本日成交量_吨": vol_t,
                                "本日成交额_元": amt_t,
                                "累计成交量_吨": vol_c,
                                "累计成交额_元": amt_c,
                            })
                continue

            # ---- 交易方式行（5列，当前配额继承自上一行）----
            if current_quota and len(cells) >= 5:
                tx_type = cells[0]
                if tx_type not in TX_TYPES:
                    continue

                # 交易方式行格式（6列或5列）：
                # 6列: [交易方式, -, vol_t, amt_t, vol_c, amt_c] - 本日数据在col[2]
                # 5列A: [交易方式, -, -, vol_c, amt_c] - 本日全为-
                # 5列B: [交易方式, vol_t, amt_t, vol_c, amt_c] - 本日数据在col[1]
                if len(cells) >= 6:
                    vol_t = clean_num(cells[2])
                    amt_t = clean_num(cells[3])
                    vol_c = clean_num(cells[4])
                    amt_c = clean_num(cells[5])
                elif len(cells) == 5:
                    # 判断是5列A还是5列B：看第二列是否为"-"
                    if cells[1].strip() in ("-", "", "—"):
                        # 5列A: [tx, -, -, vol_c, amt_c]
                        vol_t = "0"
                        amt_t = "0"
                        vol_c = clean_num(cells[3])
                        amt_c = clean_num(cells[4])
                    else:
                        # 5列B: [tx, vol_t, amt_t, vol_c, amt_c]
                        vol_t = clean_num(cells[1])
                        amt_t = clean_num(cells[2])
                        vol_c = clean_num(cells[3])
                        amt_c = clean_num(cells[4])
                else:
                    continue

                # 保留本日有成交量的记录（排除历史累计行）
                if float(vol_t) > 0:
                    records.append({
                        "日期": date_str,
                        "配额类型": current_quota,
                        "交易方式": tx_type,
                        "本日成交量_吨": vol_t,
                        "本日成交额_元": amt_t,
                        "累计成交量_吨": vol_c,
                        "累计成交额_元": amt_c,
                    })

    return date_str, records


def get_article_urls(max_pages=200):
    """
    抓取所有分页索引，收集2026年起的文章URL（遇到2025年停止）
    返回: [url, ...]  去重，保持顺序
    """
    seen = set()
    result = []

    # 先获取总页数
    html = fetch_page(INDEX_URL)
    if not html:
        print("[Error] 无法访问索引页")
        return []

    soup = BeautifulSoup(html, "html.parser")
    page_count = 1
    for a in soup.find_all("a", href=re.compile(r"/list/18\.html\?page=\d+")):
        m = re.search(r"page=(\d+)", a.get("href", ""))
        if m:
            page_count = max(page_count, int(m.group(1)))

    print(f"索引页总数: {page_count}")

    # 从第1页往后翻，遇到2025年文章则停止
    for page in range(1, page_count + 1):
        print(f"  抓取索引页 {page}/{page_count} ...", end=" ", flush=True)
        url = f"{INDEX_URL}?page={page}"
        html = fetch_page(url)
        if not html:
            print("失败")
            time.sleep(2)
            continue

        soup = BeautifulSoup(html, "html.parser")
        new_count = 0

        for a in soup.find_all("a", href=re.compile(r"/view/\d+\.html")):
            href = a.get("href", "")
            title = a.get("title", "") or a.get_text(strip=True)

            # 只收录2026年起的文章
            if not re.search(r"2026年\d+月\d+日", title):
                continue
            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url in seen:
                continue
            seen.add(full_url)
            result.append(full_url)
            new_count += 1

        print(f"新增{new_count}个2026年URL (累计{len(result)})")

        # 如果已经翻到很后面还没看到2026，说明页面是旧的
        if page > 10 and len(result) == 0:
            print("  前10页无2026年文章，可能网站日期排序不同，改为抓取全部页面")
        time.sleep(0.8)

    return result


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 读取已有日期，避免重复抓取
    existing_dates = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                d = row.get("日期", "").strip()
                if d:
                    existing_dates.add(d)
        if existing_dates:
            print(f"已有数据: {len(existing_dates)} 天，"
                  f"{min(existing_dates)} ~ {max(existing_dates)}")

    # 获取所有2026年文章URL
    article_urls = get_article_urls()
    if not article_urls:
        print("未找到2026年文章，退出")
        return

    print(f"待抓取文章: {len(article_urls)} 篇")

    all_new = []
    skipped_already = 0

    for i, url in enumerate(article_urls):
        print(f"  [{i+1}/{len(article_urls)}] {url}", end=" ... ")

        html = fetch_page(url)
        if not html:
            print("抓取失败")
            time.sleep(2)
            continue

        date_str, records = parse_article(html, url)

        if not date_str:
            print("无法解析日期，跳过")
            time.sleep(1)
            continue

        if date_str in existing_dates:
            print(f"已存在({date_str})，跳过")
            skipped_already += 1
            time.sleep(0.5)
            continue

        if records:
            all_new.extend(records)
            print(f"{date_str}: +{len(records)} 条")
        else:
            print(f"{date_str}: 无有效数据")

        time.sleep(1)

    print(f"\n抓取完成: 新增文章 {len(article_urls)-skipped_already} 篇，"
          f"新增记录 {len(all_new)} 条")

    if all_new:
        file_exists = os.path.exists(OUT_FILE)
        with open(OUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
            fields = ["日期", "配额类型", "交易方式",
                      "本日成交量_吨", "本日成交额_元",
                      "累计成交量_吨", "累计成交额_元"]
            writer = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                writer.writeheader()
            writer.writerows(all_new)
        print(f"已写入: {OUT_FILE}")

        # 验证
        with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        print(f"文件总行数（含表头）: {len(lines)}")

        # 显示样本
        print("\n=== 样本数据（前5条）===")
        with open(OUT_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                print(f"  {row['日期']} | {row['配额类型']} | {row['交易方式']} | "
                      f"本日vol={row['本日成交量_吨']} | 本日amt={row['本日成交额_元']}")
    else:
        print("无新数据")


if __name__ == "__main__":
    main()
