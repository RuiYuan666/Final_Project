# -*- coding: utf-8 -*-
# 碳市场数据预处理【固定列名·纯净终版】
# 适配固定表头：日期、配额类型、开盘价、最高价、最低价、收盘价、涨幅、日成交量、日成交额、交易方式
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ===================== 1、读取原始数据（固定表头） =====================
# 原始文件固定10列：日期、配额类型、开盘价、最高价、最低价、收盘价、涨幅、日成交量、日成交额、交易方式
df = pd.read_csv("ChinaCarbon_2021_C.csv", encoding="utf-8-sig")
print("✅ 原始碳交易数据读取成功")

# ===================== 2、基础数据清洗 =====================
# 规范日期格式
df["日期"] = pd.to_datetime(df["日期"], errors="coerce")

# 批量转为数值型
numeric_cols = ["开盘价","最高价","最低价","收盘价","涨幅","日成交量","日成交额"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ===================== 3、特征工程（论文固定衍生指标） =====================
# 衍生指标：日均价 = 日成交额 / 日成交量
df["日均价"] = df["日成交额"] / df["日成交量"]

# 清洗无穷值、空值、异常行
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(inplace=True)

# ===================== 4、筛选7维建模特征 =====================
# 6项原始交易特征 + 1项衍生日均价特征
feature_cols = [
    "开盘价",
    "收盘价",
    "最高价",
    "最低价",
    "日成交量",
    "日成交额",
    "日均价"
]

# ===================== 5、Z-Score标准化 =====================
scaler = StandardScaler()
scaled_data = scaler.fit_transform(df[feature_cols])
for idx, col_name in enumerate(feature_cols):
    df[f"{col_name}_标准化"] = scaled_data[:, idx]

# ===================== 6、输出预处理数据集 =====================
df.to_csv("carbon_preprocessed_C.csv", index=False, encoding="utf-8-sig")

# ===================== 7、运行日志输出 =====================
print("\n=============================================")
print("📊 数据预处理完成（固定表头稳定版）")
print(f"有效清洗样本数量：{len(df)} 行")
print(f"孤立森林建模特征：7维")
print("✅ 适配真实原始表头，无多余匹配逻辑")
print("=============================================")