import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ===================== 1. 读取本地数据 =====================
# 数据源：当前文件夹 CRC_price_C.csv
df = pd.read_csv("CRC_price_C.csv", parse_dates=["日期"], encoding="utf-8-sig")

# 按日期排序（必须）
df = df.sort_values("日期").reset_index(drop=True)

# ===================== 去除最高价或最低价为0的记录 =====================
print("清洗前数据行数：", len(df))
df = df[(df["最高价（元/吨）"] > 0) & (df["最低价（元/吨）"] > 0)].copy()
df = df.reset_index(drop=True)
print("清洗后数据行数：", len(df), "(已删除最高价/最低价=0的记录)")

# ===================== 2. 新增：日均价（元） =====================
df["日均价（元）"] = df["成交额（元）"] / df["成交量（吨）"]

# 处理异常值（防止除以0报错）
df["日均价（元）"] = df["日均价（元）"].replace([np.inf, -np.inf], np.nan).fillna(0)

# ===================== 3. 新增：涨跌幅 =====================
# 规则：
# 第一天：今日收盘价 / 74.63
# 之后：今日收盘价 / 前一日收盘价

close_list = df["收盘价（元/吨）"].values
change_ratio_list = []

# 第一天
prev_close = 74.63
change_ratio_list.append(close_list[0] / prev_close)

# 第2天及以后
for i in range(1, len(close_list)):
    change_ratio_list.append(close_list[i] / close_list[i-1])

df["涨跌幅"] = change_ratio_list

# ===================== 4. 6列标准化：保留原数据，新增标准化列 =====================
# 需要标准化的 6 列
cols_to_standardize = [
    "收盘价（元/吨）",
    "最高价（元/吨）",
    "最低价（元/吨）",
    "成交量（吨）",
    "成交额（元）",
    "日均价（元）"
]

# 对每一列标准化，并新增一列（不覆盖原数据）
scaler = StandardScaler()
for col in cols_to_standardize:
    df[f"{col}_标准化"] = scaler.fit_transform(df[[col]])

# ===================== 5. 保存结果 =====================
df.to_csv("CRC_price_C_processed.csv", index=False, encoding="utf-8-sig")

# ===================== 输出预览 =====================
print("\n✅ 数据处理完成！")
print("📊 原始数据全部保留")
print("📊 已删除：最高价或最低价=0的无效记录")
print("📊 新增：日均价（元）、涨跌幅")
print("📊 新增：6列标准化列（_标准化）")
print("\n预览前5行：")
print(df.head())