# China Carbon Market Data Collection and Anomaly Detection

A data engineering project for collecting, cleaning, and analyzing China's national carbon market trading data from two authoritative sources. Designed to support academic research with reproducible scripts and structured datasets.

---

## 📁 Project Structure

```
English_ver/
├── 101_1_fetch_2021_2023_cneeex_year.py   # CNEEEX data fetcher (index pages)
├── 101_2_fetch_2021_2023_cneeex.py        # CNEEEX data fetcher (detail pages)
├── 102-Data_Standardization-e.py           # CNEEEX data cleaning & standardization
├── 103_anomaly_detection_e.py              # CNEEEX anomaly detection
│
├── 201_1_fetch_crc_price_e.py             # CRC price data fetcher
├── 201_2_fetch_crc_volume_e.py           # CRC volume data fetcher
├── 202_fetch_crc_sync_e.py               # CRC sync data fetcher
├── 203_1_Data_Standardization-e.py       # CRC price data standardization
├── 203_2_Data_Standardization-e.py       # CRC volume data standardization
├── 204_anomaly_detection_e.py             # CRC anomaly detection
│
├── ChinaCarbon_2021.csv                   # Raw CNEEEX data 2021
├── ChinaCarbon_2022.csv                   # Raw CNEEEX data 2022
├── ChinaCarbon_2023.csv                   # Raw CNEEEX data 2023
├── CNEEEX_National_Carbon_Data_2021_2023.csv
├── CNEEEX_National_Carbon_Data_2021_2023.xlsx
│
├── carbon_preprocessed.csv                # CNEEEX preprocessed data
├── carbon_anomaly_final_english.csv       # CNEEEX anomaly results
├── carbon_anomaly_final_english_fix.csv
├── carbon_anomaly_only_result.csv
│
├── CRC_price_e.csv                        # Raw CRC price data
├── CRC_price_e_processed.csv              # CRC price processed
├── CRC_price_e_processed_fix.csv
├── CRC_price_e.xlsx
├── CRC_volume_english.csv                 # Raw CRC volume data
├── CRC_volume_english.xlsx
├── TF.xlsx                               # Transfer Function analysis results
└── README.md
```

---

## 🔗 Data Sources

### 1. CNEEEX — Shanghai Environment Energy Exchange
- **URL**: https://www.cneeex.com/qgtpfqjy/mrgk/
- **Coverage**: Daily trading data from July 2021 to present
- **Fields**: Date, Quota Type, Open, High, Low, Close, Change, Daily Volume, Daily Amount, Trade Type
- **Trade Types**: Listed (挂牌协议), Block (大宗协议)

### 2. CRC — China Carbon Market Trading & Settlement System
- **URL**: https://www.chinacrc.net.cn/list/101.html
- **Coverage**: ~116 pages of auction and block trading records
- **Fields**: Date, Trading Variety, Trading Type, Close/Highest/Lowest Price, Volume, Amount

---

## ⚙️ Workflow

### CNEEEX Data Pipeline (Series 101–103)

```
101_1_fetch_2021_2023_cneeex_year.py
101_2_fetch_2021_2023_cneeex.py
         ↓
  ChinaCarbon_2021.csv
  ChinaCarbon_2022.csv
  ChinaCarbon_2023.csv
  CNEEEX_National_Carbon_Data_2021_2023.csv
  CNEEEX_National_Carbon_Data_2021_2023.xlsx
         ↓
102-Data_Standardization-e.py
         ↓
  carbon_preprocessed.csv
         ↓
103_anomaly_detection_e.py
         ↓
  carbon_anomaly_final_english.csv
  carbon_anomaly_final_english_fix.csv
  carbon_anomaly_only_result.csv
```

### CRC Data Pipeline (Series 201–204)

```
201_1_fetch_crc_price_e.py
201_2_fetch_crc_volume_e.py
202_fetch_crc_sync_e.py
         ↓
  CRC_price_e.csv
  CRC_volume_english.csv
         ↓
203_1_Data_Standardization-e.py
203_2_Data_Standardization-e.py
         ↓
  CRC_price_e_processed.csv / _fix.csv
         ↓
204_anomaly_detection_e.py
         ↓
  TF.xlsx (Transfer Function analysis)
```

---

## 🚀 Usage

### Prerequisites

```bash
pip install pandas numpy matplotlib scikit-learn requests beautifulsoup4 openpyxl
```

### Data Collection

```bash
# Fetch CNEEEX data (2021–2023)
python 101_1_fetch_2021_2023_cneeex_year.py
python 101_2_fetch_2021_2023_cneeex.py

# Fetch CRC data
python 201_1_fetch_crc_price_e.py
python 201_2_fetch_crc_volume_e.py
python 202_fetch_crc_sync_e.py
```

### Data Cleaning

```bash
# Standardize CNEEEX data
python 102-Data_Standardization-e.py

# Standardize CRC data
python 203_1_Data_Standardization-e.py
python 203_2_Data_Standardization-e.py
```

### Anomaly Detection

```bash
# CNEEEX anomaly detection (3σ + Isolation Forest)
python 103_anomaly_detection_e.py

# CRC anomaly detection
python 204_anomaly_detection_e.py
```

---

## 📊 Key Algorithms

### 3σ Criterion
Detects outliers where data points exceed 3 standard deviations from the mean. Applied to:
- Close Price
- Change (daily price change)
- Average Daily Price

### Isolation Forest
Unsupervised anomaly detection that isolates anomalies by random partitioning. Applied after 3σ screening for enhanced precision.

---

## 📝 Data Schema

### CNEEEX Raw Data (ChinaCarbon_*.csv)

| Column | Type | Description |
|--------|------|-------------|
| Date | YYYY-MM-DD | Trading date |
| QuotaType | String | Carbon quota type (CEA) |
| Open | Float | Opening price (CNY/Ton) |
| High | Float | Highest price (CNY/Ton) |
| Low | Float | Lowest price (CNY/Ton) |
| Close | Float | Closing price (CNY/Ton) |
| Change | Float | Daily price change (%) |
| DailyVolume | Integer | Trading volume (Ton) |
| DailyAmount | Float | Trading amount (CNY) |
| TradeType | String | Listed / Block |

### CRC Raw Data (CRC_*.csv)

| Column | Type | Description |
|--------|------|-------------|
| date | YYYY-MM-DD | Trading date |
| trading_variety | String | Trading variety (CEA) |
| trading_type | String | Auction / Block |
| close_price_cny_ton | Float | Closing price (CNY/Ton) |
| highest_price_cny_ton | Float | Highest price (CNY/Ton) |
| lowest_price_cny_ton | Float | Lowest price (CNY/Ton) |
| volume_ton | Integer | Volume (Ton) |
| amount_cny | Float | Amount (CNY) |

---

## 📌 Notes

- All CSV files use **UTF-8-BOM** encoding for Chinese character compatibility
- Scripts use retry logic and rate limiting to avoid server overload
- CNEEEX data starts from July 16, 2021 (national market launch date)
- CRC data covers historical auction and block trading records
- Anomaly detection outputs include visualization charts saved as PNG files

---

## 🎓 Academic Context

This project was developed for carbon market research at **Nanjing University of Information Science and Technology**, supporting thesis work on carbon market anomaly detection using statistical methods (3σ criterion) and machine learning (Isolation Forest).

---

*Last updated: 2026-05-16*
