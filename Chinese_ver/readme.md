# 全国碳市场数据采集与异常检测分析系统

> 南京信息工程大学 · 毕业论文项目  
> 数据来源：上海环境能源交易所（CNEEEX）、中国碳排放权注册登记结算有限责任公司（CRC）

---

## 📁 项目结构

```
Final_Project/
│
├── 📥 数据采集模块
│   │
│   ├── 🔹 第一部分：CNEEEX 全国碳市场数据
│   │   ├── 101_1_fetch_2021_2023_cneeex_year.py   # 采集 2021-2023 年度数据（双系统兼容）
│   │   └── 101_2_retry_4_urls.py                  # 失败 URL 重试采集
│   │
│   └── 🔹 第二部分：CRC 碳市场结算数据
│       ├── 201_1_fetch_crc_price.py                # 采集 CRC 每日交易价格（挂牌/大宗）
│       ├── 201_2_fetch_crc_volume.py                # 采集 CRC 每日成交量明细（按配额类型）
│       └── 202_fetch_crc_sync.py                    # CRC 数据增量同步（对比本地/网站自动更新）
│
├── 🔧 数据预处理模块
│   │
│   ├── 102-Data_Standardization-C.py                # CNEEEX 数据标准化（Z-Score + 衍生指标）
│   ├── 203_数据标准化.py                            # CRC 数据标准化（Z-Score + 衍生指标）
│   │
│   └── 📊 中间数据文件
│       ├── ChinaCarbon_2021_C.csv                    # CNEEEX 2021 年原始数据
│       ├── CRC_price_C.csv / .xlsx                  # CRC 价格数据（原始）
│       ├── CRC_price_C_processed.csv                 # CRC 价格数据（标准化处理后）
│       ├── CRC_volume_C.csv / .xlsx                 # CRC 成交量数据（按配额类型）
│       └── carbon_preprocessed_C.csv                # CNEEEX 标准化后数据（异常检测输入）
│
└── 🔍 异常检测模块
    │
    ├── 103-异常检测.py                               # CNEEEX 异常检测（3σ + 孤立森林）
    ├── 204_anomaly_detection_c.py                    # CRC 异常检测（3σ + 孤立森林）
    │
    └── 📊 异常检测输出
        └── carbon_anomaly_final_cn_10.csv           # 最终异常记录（合并输出）
```

---

## 🏗️ 系统架构

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌───────────────┐
│  数据采集层   │────▶│  数据预处理层  │────▶│  异常检测层 │────▶│  分析结果输出  │
│ (CNEEEX/CRC) │     │  标准化/清洗  │     │  3σ/IForest│     │  CSV/可视化图 │
└─────────────┘     └──────────────┘     └────────────┘     └───────────────┘
```

**数据来源：**

| 数据源 | 网站 | 主要字段 | 时间范围 |
|--------|------|----------|----------|
| CNEEEX | www.cneeex.com | 开盘/最高/最低/收盘价、成交量、成交额、交易方式 | 2021–2023 |
| CRC | www.chinacrc.net.cn | 挂牌/大宗成交量与成交额、收盘价 | 2026 年至今 |

---

## 🔧 环境依赖

```bash
pip install requests pandas numpy scikit-learn matplotlib beautifulsoup4
```

- `requests` / `beautifulsoup4` — 网络请求与 HTML 解析
- `pandas` — 数据处理与 CSV 操作
- `numpy` — 数值计算
- `scikit-learn` — 孤立森林异常检测算法
- `matplotlib` — 异常检测可视化图表

> ⚠️ 图表中文显示需系统已安装 `SimHei`（黑体）字体，Windows 用户可从 C:\Windows\Fonts 复制到 Python 目录。

---

## 🚀 快速开始

### 第一步：数据采集

**采集 CNEEEX 历史数据（2021–2023）：**
```bash
python 101_1_fetch_2021_2023_cneeex_year.py
```

**采集 CRC 每日价格数据（2026 至今）：**
```bash
python 201_1_fetch_crc_price.py
```

**采集 CRC 每日成交量明细：**
```bash
python 201_2_fetch_crc_volume.py
```

**增量同步 CRC 最新数据（自动对比本地 CSV）：**
```bash
python 202_fetch_crc_sync.py
```

---

### 第二步：数据预处理

**CNEEEX 数据标准化（生成 7 维建模特征）：**
```bash
python 102-Data_Standardization-C.py
```
输出：`carbon_preprocessed_C.csv`（含 Z-Score 标准化列 + 日均价衍生指标）

**CRC 数据标准化：**
```bash
python 203_数据标准化.py
```
输出：`CRC_price_C_processed.csv`

---

### 第三步：异常检测

**CNEEEX 异常检测：**
```bash
python 103-异常检测.py
```
- 算法：3σ准则（收盘价/涨幅/日均价）+ 孤立森林（7 维特征）
- 输出图表：`3sigma_*_*.png`（3σ 异常图）+ `IsolationForest_*.png`（孤立森林图）
- 输出数据：`carbon_anomaly_final_cn_10.csv`

**CRC 异常检测：**
```bash
python 204_anomaly_detection_c.py
```
- 算法：3σ准则（收盘价/日均价/涨跌幅）+ 孤立森林（6 维特征）
- 输出图表：`3σ_*_*.png` + `isolation_forest_*.png`
- 输出数据：`carbon_anomaly_final_cn_10.csv`

---

## 📊 数据字段说明

### CNEEEX 原始数据（ChinaCarbon_2021_C.csv）
| 字段 | 说明 |
|------|------|
| 日期 | 交易日期 |
| 配额类型 | 碳排放配额年份 |
| 开盘价/最高价/最低价/收盘价 | 元/吨 |
| 涨幅 | % |
| 日成交量 | 吨 |
| 日成交额 | 元 |
| 交易方式 | 挂牌协议交易 / 大宗协议交易 |

### CRC 原始数据（CRC_price_C.csv）
| 字段 | 说明 |
|------|------|
| 日期 | 交易日期 |
| 交易品种 | 碳排放配额类型 |
| 收盘价/最高价/最低价 | 元/吨 |
| 挂牌成交量/成交额 | 吨 / 元 |
| 大宗成交量/成交额 | 吨 / 元 |
| 当日总成交量/总成交额 | 吨 / 元 |

### 标准化特征列（预处理后）
| 衍生字段 | 说明 |
|----------|------|
| 日均价 | 日成交额 / 日成交量 |
| 开盘价_标准化 ~ 日均价_标准化 | Z-Score 标准化（均值=0，标准差=1）|

---

## 🔬 异常检测算法说明

### 3σ 准则
- 适用于近似正态分布的价格/成交量指标
- 阈值：μ ± 3σ，超出范围标记为异常
- 检测指标：收盘价、涨幅（CNEEEX）/ 收盘价、日均价、涨跌幅（CRC）

### 孤立森林（Isolation Forest）
- 无监督异常检测，适用于多维特征联合判断
- 建模特征：7 维标准化特征（CNEEEX）/ 6 维标准化特征（CRC）
- 参数：`n_estimators=100`，`contamination=0.08`（CNEEEX）/ `0.05`（CRC）

### 异常标记
- `1` = 异常
- `0` = 正常

---

## 📌 注意事项

1. **编码格式**：所有 CSV 文件使用 `utf-8-sig`（UTF-8 BOM）编码，避免 Excel 打开中文乱码
2. **图表中文显示**：需确保 matplotlib 可访问中文字体（SimHei）
3. **网络超时**：数据采集脚本内置 3 次重试机制，多次失败可手动重跑
4. **CRC 增量同步**：首次运行前确保 `CRC_price_C.csv` 已存在，否则自动全量下载
5. **失败 URL 重试**：`101_2_retry_4_urls.py` 仅重试指定的历史失败 URL，定期检查遗漏数据

---

## 📄 许可证

本项目仅供学术研究使用，数据版权归各数据来源机构所有。
