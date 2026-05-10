import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

# ===================== 全局设置 =====================
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
pd.set_option("display.max_columns", None)

# ===================== 1. 读取数据 =====================
df = pd.read_csv("CRC_price_C_processed.csv", parse_dates=["日期"], encoding="utf-8-sig")
df = df.sort_values("日期").reset_index(drop=True)

# 3σ 检测字段
sigma_columns = [
    "收盘价（元/吨）",
    "日均价（元）",
    "涨跌幅"
]

# 图片安全名称映射
fig_name_map = {
    "收盘价（元/吨）": "close_price",
    "日均价（元）": "daily_avg_price",
    "涨跌幅": "price_change_ratio"
}

# 孤立森林使用的标准化列
standard_cols = [
    "收盘价（元/吨）_标准化",
    "最高价（元/吨）_标准化",
    "最低价（元/吨）_标准化",
    "成交量（吨）_标准化",
    "成交额（元）_标准化",
    "日均价（元）_标准化"
]

# ===================== 按交易类型分组处理 =====================
all_results = []
trade_types = df["交易类型"].unique()

for trade in trade_types:
    sub = df[df["交易类型"] == trade].copy().sort_values("日期").reset_index(drop=True)
    prefix = "auction" if "挂牌" in trade else "block"
    print(f"\n===== 处理交易类型：{trade} =====")

    # ---------------------- 3σ 异常检测（输出 1/0） ----------------------
    for col in sigma_columns:
        mean_val = sub[col].mean()
        std_val = sub[col].std()
        upper = mean_val + 3 * std_val
        lower = mean_val - 3 * std_val
        sub[f"{col}_3σ异常"] = ((sub[col] > upper) | (sub[col] < lower)).astype(int)

        # 绘图
        plt.figure(figsize=(14, 5))
        plt.plot(sub["日期"], sub[col], label=col, linewidth=1.2)
        anomaly = sub[sub[f"{col}_3σ异常"] == 1]
        plt.scatter(anomaly["日期"], anomaly[col], color="red", s=50, label="3σ异常点")
        plt.axhline(upper, color="orange", linestyle="--", label="3σ上限")
        plt.axhline(lower, color="green", linestyle="--", label="3σ下限")
        plt.title(f"【{trade}】3σ异常检测：{col}")
        plt.xlabel("日期")
        plt.ylabel(col)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"3σ_{prefix}_{fig_name_map[col]}.png", dpi=300)
        plt.close()

    # 3σ综合异常
    sub["3σ综合异常"] = sub[[f"{c}_3σ异常" for c in sigma_columns]].any(axis=1).astype(int)

    # ---------------------- 孤立森林异常检测（输出 1/0） ----------------------
    X = sub[standard_cols].fillna(0)
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    sub["孤立森林异常"] = model.fit_predict(X)
    sub["孤立森林异常"] = sub["孤立森林异常"].map({1: 0, -1: 1})

    # 孤立森林绘图
    plt.figure(figsize=(14, 5))
    plt.plot(sub["日期"], sub["收盘价（元/吨）"], linewidth=1.2, label="收盘价")
    if_anom = sub[sub["孤立森林异常"] == 1]
    plt.scatter(if_anom["日期"], if_anom["收盘价（元/吨）"], color="purple", s=60, label="孤立森林异常")
    plt.title(f"【{trade}】孤立森林异常检测（6维特征）")
    plt.xlabel("日期")
    plt.ylabel("收盘价（元/吨）")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"isolation_forest_{prefix}.png", dpi=300)
    plt.close()

    # 最终异常标记
    sub["最终异常"] = (sub["3σ综合异常"] | sub["孤立森林异常"]).astype(int)
    all_results.append(sub)

# ===================== 合并并清理 =====================
df_out = pd.concat(all_results, ignore_index=True).sort_values("日期")

# 只保留异常行（3σ 或 孤立森林）
df_out = df_out[df_out["最终异常"] == 1].copy()

# 删除：日均价、涨跌幅
df_out = df_out.drop(columns=["日均价（元）", "涨跌幅"], errors="ignore")

# 删除所有标准化列
df_out = df_out.drop(columns=[c for c in df_out.columns if "标准化" in c], errors="ignore")

# ===================== 保存最终结果 =====================
df_out.to_csv("carbon_anomaly_final_cn_10.csv", index=False, encoding="utf-8-sig")

# ===================== 输出信息 =====================
print("\n✅ 全部处理完成！")
print(f"📊 最终异常记录数：{len(df_out)} 条")
print("📁 输出文件：carbon_anomaly_final_cn_10.csv")
print("✅ 异常值：1=异常，0=正常")
print("✅ 已删除：日均价、涨跌幅")
print("✅ 图表：3σ×6张 + 孤立森林×2张")