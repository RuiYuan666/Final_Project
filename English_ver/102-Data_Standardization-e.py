# -*- coding: utf-8 -*-
# Nanjing University of Information Science and Technology
# Carbon Market Data Preprocessing (Final Fixed Header Version)
# Raw English Header: Date,QuotaType,Open,High,Low,Close,Change,DailyVolume,DailyAmount,TradeType
# Fixed simple header, no redundant brackets, pure concise English for thesis
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ===================== 1. Read Raw Dataset (Fixed Simple English Header) =====================
df = pd.read_csv("ChinaCarbon_2021.csv", encoding="utf-8-sig")
print("✅ Successfully read raw carbon dataset")

# ===================== 2. Basic Data Cleaning =====================
# Convert date format
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Batch convert to numeric type
numeric_cols = ["Open", "High", "Low", "Close", "Change", "DailyVolume", "DailyAmount"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ===================== 3. Feature Engineering (Only One Derived Indicator) =====================
# Derived indicator: Average_Daily_Price = DailyAmount / DailyVolume
# Permanently delete invalid turnover index
df["Average_Daily_Price"] = df["DailyAmount"] / df["DailyVolume"]

# Clean infinite value and null value
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(inplace=True)

# ===================== 4. Seven-Dimensional Feature Selection =====================
# 6 original features + 1 derived feature
feature_cols = [
    "Open",
    "Close",
    "High",
    "Low",
    "DailyVolume",
    "DailyAmount",
    "Average_Daily_Price"
]

# ===================== 5. Z-Score Standardization =====================
scaler = StandardScaler()
scaled_data = scaler.fit_transform(df[feature_cols])
for idx, col_name in enumerate(feature_cols):
    df[f"{col_name}_Scaled"] = scaled_data[:, idx]

# ===================== 6. Export Preprocessed Dataset =====================
df.to_csv("carbon_preprocessed.csv", index=False, encoding="utf-8-sig")

# ===================== 7. Console Output =====================
print("\n=============================================")
print("📊 Data Preprocessing Completed (Fixed Header Version)")
print(f"Valid Cleaned Samples: {len(df)}")
print(f"Isolation Forest Feature Dimension: 7")
print("✅ Adapt fixed simple English header(TradeType)")
print("✅ Only retain Average_Daily_Price derived indicator")
print("✅ No redundant translation, concise for thesis")
print("=============================================")
