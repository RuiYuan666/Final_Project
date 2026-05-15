import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ===================== 1. Load Local Data =====================
# Data source: CRC_price_C.csv in current folder
df = pd.read_csv("CRC_price_e.csv", parse_dates=["date"], encoding="utf-8-sig")

# Sort by date (required)
df = df.sort_values("date").reset_index(drop=True)

# ===================== 2. Add Daily Average Price =====================
df["daily_avg_price_cny"] = df["amount_cny"] / df["volume_ton"]

# Handle outliers (avoid division by zero error)
df["daily_avg_price_cny"] = df["daily_avg_price_cny"].replace([np.inf, -np.inf], np.nan).fillna(0)

# ===================== 3. Add Price Change Ratio =====================
# Rules:
# Day 1: Today's Close / 74.63
# After Day 1: Today's Close / Previous Day's Close

close_list = df["close_price_cny_ton"].values
change_ratio_list = []

# First day
prev_close = 74.63
change_ratio_list.append(close_list[0] / prev_close)

# From day 2 onwards
for i in range(1, len(close_list)):
    change_ratio_list.append(close_list[i] / close_list[i-1])

df["price_change_ratio"] = change_ratio_list

# ===================== 4. Standardize 6 Columns: Keep Original Data =====================
# Columns to standardize
cols_to_standardize = [
    "close_price_cny_ton",
    "highest_price_cny_ton",
    "lowest_price_cny_ton",
    "volume_ton",
    "amount_cny",
    "daily_avg_price_cny"
]

# Standardize each column and add new column (no overwrite)
scaler = StandardScaler()
for col in cols_to_standardize:
    df[f"{col}_standardized"] = scaler.fit_transform(df[[col]])

# ===================== 5. Save Result =====================
df.to_csv("CRC_price_e_processed.csv", index=False, encoding="utf-8-sig")

# ===================== Output Preview =====================
print("✅ Data processing completed!")
print("📊 All original data preserved")
print("📊 Added: daily_avg_price_cny, price_change_ratio")
print("📊 Added: 6 standardized columns (_standardized)")
print("\nPreview first 5 rows:")
print(df.head())