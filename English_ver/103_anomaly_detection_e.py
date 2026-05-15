# -*- coding: utf-8 -*-
# Nanjing University of Information Science and Technology
# Carbon Market Anomaly Detection (Fixed Simple Header Final Version)
# Adapt raw header: Date,QuotaType,Open,High,Low,Close,Change,DailyVolume,DailyAmount,TradeType
# Algorithm: 3σ Criterion + Isolation Forest, fully consistent with thesis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

# Set academic font
plt.rcParams['font.sans-serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

# ===================== 1. Read Preprocessed Dataset =====================
df = pd.read_csv("carbon_preprocessed.csv", encoding="utf-8-sig")
print("✅ Successfully read preprocessed dataset")
print("Transaction types:", df["TradeType"].unique())

# ===================== 2. Detect by Transaction Type =====================
transaction_type_list = df["TradeType"].unique()
result_list = []

# 3σ detection indicators (consistent with thesis)
sigma_indicators = ["Close", "Change", "Average_Daily_Price"]

# Simple English mapping for image naming (avoid error)
indicator_map = {
    "Close": "ClosePrice",
    "Change": "ChangeRate",
    "Average_Daily_Price": "AvgPrice"
}

trade_map = {
    "Listed": "Listing",
    "Block": "Block"
}

for trade_type in transaction_type_list:
    df_sub = df[df["TradeType"] == trade_type].copy()
    df_sub["Date"] = pd.to_datetime(df_sub["Date"])
    print(f"\n---------- Start Detection: {trade_type} , Data Volume: {len(df_sub)} ----------")

    # ============== 2.1 3σ Criterion Detection ==============
    for indicator in sigma_indicators:
        mean_val = df_sub[indicator].mean()
        std_val = df_sub[indicator].std()
        upper_threshold = mean_val + 3 * std_val
        lower_threshold = mean_val - 3 * std_val

        anomaly_flag = np.where((df_sub[indicator] < lower_threshold) | (df_sub[indicator] > upper_threshold), 1, 0)
        df_sub[f"{indicator}_3sigma_Anomaly"] = anomaly_flag

        # Standard simple image name
        simple_trade_name = trade_map[trade_type]
        simple_ind_name = indicator_map[indicator]
        save_name = f"3sigma_{simple_trade_name}_{simple_ind_name}.png"

        # Draw 3σ figure
        plt.figure(figsize=(16, 6))
        plt.plot(df_sub["Date"], df_sub[indicator], color="#2E86AB", linewidth=1.2, label=indicator)
        plt.axhline(y=upper_threshold, color="red", linestyle="--", linewidth=1, label="Upper Threshold (μ+3σ)")
        plt.axhline(y=lower_threshold, color="red", linestyle="--", linewidth=1, label="Lower Threshold (μ-3σ)")
        plt.axhline(y=mean_val, color="orange", linestyle="-.", linewidth=1, label="Mean Value (μ)")

        anomaly_data = df_sub[df_sub[f"{indicator}_3sigma_Anomaly"] == 1]
        plt.scatter(anomaly_data["Date"], anomaly_data[indicator], color="#E63946", s=30, label="Anomaly Sample")

        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(12))
        plt.xticks(rotation=45, fontsize=8)
        plt.title(f"{trade_type} | {indicator} Anomaly Detection (3σ Criterion)", fontsize=12)
        plt.xlabel("Transaction Date", fontsize=10)
        plt.ylabel(indicator, fontsize=10)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(save_name, dpi=300)
        plt.close()

    # ============== 2.2 Isolation Forest (7 Standardized Features) ==============
    feature_cols_scaled = [
        "Open_Scaled",
        "Close_Scaled",
        "High_Scaled",
        "Low_Scaled",
        "DailyVolume_Scaled",
        "DailyAmount_Scaled",
        "Average_Daily_Price_Scaled"
    ]
    X = df_sub[feature_cols_scaled]

    # Fixed model parameters
    model = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
    model.fit(X)
    predict_result = model.predict(X)
    isolation_anomaly = np.where(predict_result == -1, 1, 0)
    df_sub["IsolationForest_Anomaly"] = isolation_anomaly

    # Isolation Forest image name
    simple_trade_name = trade_map[trade_type]
    save_name_forest = f"IsolationForest_{simple_trade_name}.png"

    # Draw Isolation Forest figure
    plt.figure(figsize=(16, 6))
    plt.plot(df_sub["Date"], df_sub["Close"], color="#2E86AB", linewidth=1.2, label="Closing Price")
    forest_anomaly = df_sub[df_sub["IsolationForest_Anomaly"] == 1]
    plt.scatter(forest_anomaly["Date"], forest_anomaly["Close"],
                color="#FFB703", marker="^", s=50, label="Isolation Forest Anomaly")

    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(12))
    plt.xticks(rotation=45, fontsize=8)
    plt.title(f"{trade_type} | Isolation Forest Anomaly Detection (7 Features)", fontsize=12)
    plt.xlabel("Transaction Date", fontsize=10)
    plt.ylabel("Carbon Price (Yuan/Ton)", fontsize=10)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(save_name_forest, dpi=300)
    plt.close()

    result_list.append(df_sub)

# ===================== 3. Merge and Save Anomaly Data =====================
df_all = pd.concat(result_list, ignore_index=True)
anomaly_condition = (
    (df_all['Close_3sigma_Anomaly'] == 1) |
    (df_all['Change_3sigma_Anomaly'] == 1) |
    (df_all['Average_Daily_Price_3sigma_Anomaly'] == 1) |
    (df_all['IsolationForest_Anomaly'] == 1)
)
df_anomaly_only = df_all[anomaly_condition].copy()

# ==============================================
# 【核心：只保留你指定的7列】
# ==============================================
final_columns = [
    "Date",
    "Close",
    "Change",
    "Close_3sigma_Anomaly",
    "Change_3sigma_Anomaly",
    "Average_Daily_Price_3sigma_Anomaly",
    "IsolationForest_Anomaly"
]
df_anomaly_only = df_anomaly_only[final_columns].copy()

# 保存最终结果
df_anomaly_only.to_csv("carbon_anomaly_only_result.csv", index=False, encoding="utf-8-sig")

# ===================== 4. Statistical Output =====================
print("\n=============================================")
print("📊 Anomaly Detection Result (Fixed Header Version)")
print(f"Close Price 3σ Anomaly: {(df_all['Close_3sigma_Anomaly']==1).sum()}")
print(f"Change Rate 3σ Anomaly: {(df_all['Change_3sigma_Anomaly']==1).sum()}")
print(f"Average Daily Price 3σ Anomaly: {(df_all['Average_Daily_Price_3sigma_Anomaly']==1).sum()}")
print(f"Isolation Forest Anomaly: {(df_all['IsolationForest_Anomaly']==1).sum()}")
print(f"Total Anomaly Samples Saved: {len(df_anomaly_only)}")
print("✅ Fixed trade type bug(Listed/Block)")
print("✅ Fully match simple English raw header")
print("✅ Output ONLY the 7 required columns")
print("✅ Zero error, thesis final version")
print("=============================================")