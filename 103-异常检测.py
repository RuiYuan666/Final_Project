# -*- coding: utf-8 -*-
# 碳市场异常检测代码【适配最新纯净表头·终版】
# 适配原始列名：日期、配额类型、开盘价、最高价、最低价、收盘价、涨幅、日成交量、日成交额、交易方式
# 算法：3σ准则 + 孤立森林
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

# 设置中文字体、图片清晰度
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

# ===================== 1、读取预处理数据集 =====================
df = pd.read_csv("carbon_preprocessed_C.csv", encoding="utf-8-sig")
print("✅ 成功读取预处理数据集")
print("交易方式种类：", df["交易方式"].unique())

# ===================== 2、按交易方式分组检测 =====================
transaction_type_list = df["交易方式"].unique()
result_list = []

# 3σ检测指标（同步最新无括号列名：收盘价、涨幅、日均价）
sigma_indicators = ["收盘价", "涨幅", "日均价"]
# 映射：中文指标名 → 英文简单名称（解决Windows非法字符报错）
indicator_map = {
    "收盘价": "ClosePrice",
    "涨幅": "ChangeRate",
    "日均价": "AvgPrice"
}
# 交易方式映射
trade_map = {
    "挂牌协议交易": "Listing",
    "大宗协议交易": "Block"
}

for trade_type in transaction_type_list:
    df_sub = df[df["交易方式"] == trade_type].copy()
    df_sub["日期"] = pd.to_datetime(df_sub["日期"])
    print(f"\n---------- 开始检测：{trade_type} , 数据量：{len(df_sub)} ----------")

    # ============== 2.1 3σ准则（三项指标分别单独检测、单独出图） ==============
    for indicator in sigma_indicators:
        mean_val = df_sub[indicator].mean()
        std_val = df_sub[indicator].std()
        upper_threshold = mean_val + 3 * std_val
        lower_threshold = mean_val - 3 * std_val

        # 异常标记
        anomaly_flag = np.where((df_sub[indicator] < lower_threshold) | (df_sub[indicator] > upper_threshold), 1, 0)
        df_sub[f"{indicator}_3σ异常"] = anomaly_flag

        # 使用英文命名图片
        simple_trade_name = trade_map[trade_type]
        simple_ind_name = indicator_map[indicator]
        save_name = f"3sigma_{simple_trade_name}_{simple_ind_name}.png"

        # 绘制单指标异常图
        plt.figure(figsize=(16, 6))
        plt.plot(df_sub["日期"], df_sub[indicator], color="#2E86AB", linewidth=1.2, label=indicator)
        plt.axhline(y=upper_threshold, color="red", linestyle="--", linewidth=1, label="上阈值(μ+3σ)")
        plt.axhline(y=lower_threshold, color="red", linestyle="--", linewidth=1, label="下阈值(μ-3σ)")
        plt.axhline(y=mean_val, color="orange", linestyle="-.", linewidth=1, label="均值μ")

        anomaly_data = df_sub[df_sub[f"{indicator}_3σ异常"] == 1]
        plt.scatter(anomaly_data["日期"], anomaly_data[indicator], color="#E63946", s=30, label="异常样本")

        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(12))
        plt.xticks(rotation=45, fontsize=8)
        plt.title(f"{trade_type} | {indicator} 3σ异常检测图", fontsize=12)
        plt.xlabel("交易日期", fontsize=10)
        plt.ylabel(indicator, fontsize=10)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(save_name, dpi=300)
        plt.close()

    # ============== 2.2 孤立森林 ==============
    # 严格7维特征
    feature_cols_scaled = [
        "开盘价_标准化",
        "收盘价_标准化",
        "最高价_标准化",
        "最低价_标准化",
        "日成交量_标准化",
        "日成交额_标准化",
        "日均价_标准化"
    ]
    X = df_sub[feature_cols_scaled]

    # 模型参数与论文一致
    model = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
    model.fit(X)
    predict_result = model.predict(X)
    isolation_anomaly = np.where(predict_result == -1, 1, 0)
    df_sub["孤立森林_异常标记"] = isolation_anomaly

    # 孤立森林图片
    simple_trade_name = trade_map[trade_type]
    save_name_forest = f"IsolationForest_{simple_trade_name}.png"

    # 绘制孤立森林异常图
    plt.figure(figsize=(16, 6))
    plt.plot(df_sub["日期"], df_sub["收盘价"], color="#2E86AB", linewidth=1.2, label="收盘价")
    forest_anomaly = df_sub[df_sub["孤立森林_异常标记"] == 1]
    plt.scatter(forest_anomaly["日期"], forest_anomaly["收盘价"],
                color="#FFB703", marker="^", s=50, label="孤立森林异常样本")

    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(12))
    plt.xticks(rotation=45, fontsize=8)
    plt.title(f"{trade_type} | 孤立森林异常检测图（7维特征）", fontsize=12)
    plt.xlabel("交易日期", fontsize=10)
    plt.ylabel("碳价(元/吨)", fontsize=10)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(save_name_forest, dpi=300)
    plt.close()

    result_list.append(df_sub)

# ===================== 3、合并数据 + 仅保存异常数据 =====================
df_all = pd.concat(result_list, ignore_index=True)
anomaly_condition = (
    (df_all['收盘价_3σ异常'] == 1) |
    (df_all['涨幅_3σ异常'] == 1) |
    (df_all['日均价_3σ异常'] == 1) |
    (df_all['孤立森林_异常标记'] == 1)
)
df_anomaly_only = df_all[anomaly_condition].copy()
df_anomaly_only.to_csv("carbon_anomaly_only_result.csv", index=False, encoding="utf-8-sig")

# ===================== 4、控制台统计输出 =====================
print("\n=============================================")
print("📊 异常检测结果（纯净表头适配终版）")
print(f"收盘价3σ异常数量：{(df_all['收盘价_3σ异常']==1).sum()}")
print(f"涨幅3σ异常数量：{(df_all['涨幅_3σ异常']==1).sum()}")
print(f"日均价3σ异常数量：{(df_all['日均价_3σ异常']==1).sum()}")
print(f"孤立森林异常数量：{(df_all['孤立森林_异常标记']==1).sum()}")
print(f"最终留存异常样本：{len(df_anomaly_only)}")
print("=============================================")
