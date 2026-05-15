import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

# ===================== GLOBAL SETTINGS =====================
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
pd.set_option("display.max_columns", None)

# ===================== 1. LOAD DATA =====================
df = pd.read_csv("CRC_price_e_processed_fix.csv", parse_dates=["date"], encoding="utf-8-sig")
df = df.sort_values("date").reset_index(drop=True)

# 3σ detection fields (match your real column names)
sigma_columns = [
    "close_price_cny_ton",
    "daily_avg_price_cny",
    "price_change_ratio"
]

# Safe figure name mapping
fig_name_map = {
    "close_price_cny_ton": "close_price",
    "daily_avg_price_cny": "daily_avg_price",
    "price_change_ratio": "price_change_ratio"
}

# Standardized columns for Isolation Forest (match your data)
standard_cols = [
    "close_price_cny_ton_standardized",
    "highest_price_cny_ton_standardized",
    "lowest_price_cny_ton_standardized",
    "volume_ton_standardized",
    "amount_cny_standardized",
    "daily_avg_price_cny_standardized"
]

# ===================== PROCESS BY TRADE TYPE =====================
all_results = []
trade_types = df["trading_type"].unique()

for trade in trade_types:
    sub = df[df["trading_type"] == trade].copy().sort_values("date").reset_index(drop=True)
    prefix = "auction" if "Auction" in trade else "block"
    print(f"\n===== Processing Trade Type: {trade} =====")

    # ---------------------- 3σ Anomaly Detection (1/0 output) ----------------------
    for col in sigma_columns:
        mean_val = sub[col].mean()
        std_val = sub[col].std()
        upper = mean_val + 3 * std_val
        lower = mean_val - 3 * std_val
        sub[f"{col}_3sigma_anomaly"] = ((sub[col] > upper) | (sub[col] < lower)).astype(int)

        # Plot
        plt.figure(figsize=(14, 5))
        plt.plot(sub["date"], sub[col], label=col, linewidth=1.2)
        anomaly = sub[sub[f"{col}_3sigma_anomaly"] == 1]
        plt.scatter(anomaly["date"], anomaly[col], color="red", s=50, label="3σ Anomaly")
        plt.axhline(upper, color="orange", linestyle="--", label="Upper 3σ")
        plt.axhline(lower, color="green", linestyle="--", label="Lower 3σ")
        plt.title(f"[{trade}] 3σ Anomaly Detection: {col}")
        plt.xlabel("Date")
        plt.ylabel(col)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"3sigma_{prefix}_{fig_name_map[col]}.png", dpi=300)
        plt.close()

    # Combined 3σ anomaly
    sub["combined_3sigma_anomaly"] = sub[[f"{c}_3sigma_anomaly" for c in sigma_columns]].any(axis=1).astype(int)

    # ---------------------- Isolation Forest Anomaly Detection (1/0 output) ----------------------
    X = sub[standard_cols].fillna(0)
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    sub["isolation_forest_anomaly"] = model.fit_predict(X)
    sub["isolation_forest_anomaly"] = sub["isolation_forest_anomaly"].map({1: 0, -1: 1})

    # Plot Isolation Forest
    plt.figure(figsize=(14, 5))
    plt.plot(sub["date"], sub["close_price_cny_ton"], linewidth=1.2, label="Close Price")
    if_anom = sub[sub["isolation_forest_anomaly"] == 1]
    plt.scatter(if_anom["date"], if_anom["close_price_cny_ton"], color="purple", s=60, label="Isolation Forest Anomaly")
    plt.title(f"[{trade}] Isolation Forest Anomaly Detection (6 Features)")
    plt.xlabel("Date")
    plt.ylabel("Close Price (CNY/Ton)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"isolation_forest_{prefix}.png", dpi=300)
    plt.close()

    # Final anomaly flag
    sub["final_anomaly"] = (sub["combined_3sigma_anomaly"] | sub["isolation_forest_anomaly"]).astype(int)
    all_results.append(sub)

# ===================== COMBINE AND CLEAN =====================
df_out = pd.concat(all_results, ignore_index=True).sort_values("date")

# Keep only anomaly records
df_out = df_out[df_out["final_anomaly"] == 1].copy()

# Drop unused columns
df_out = df_out.drop(columns=["daily_avg_price_cny", "price_change_ratio"], errors="ignore")

# Drop all standardized columns
df_out = df_out.drop(columns=[c for c in df_out.columns if "standardized" in c], errors="ignore")

# ===================== SAVE RESULTS =====================
df_out.to_csv("carbon_anomaly_final_english_fix.csv", index=False, encoding="utf-8-sig")

# ===================== OUTPUT SUMMARY =====================
print("\n✅ Processing completed successfully!")
print(f"📊 Total anomaly records detected: {len(df_out)}")
print("📁 Output file: carbon_anomaly_final_english.csv")
print("✅ Anomaly flag: 1 = Anomaly, 0 = Normal")
print("✅ Removed columns: daily_avg_price_cny, price_change_ratio")
print("✅ Generated charts: 3σ × 6 | Isolation Forest × 2")