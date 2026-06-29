---
title: "量化数据源指南：免费的够不够用，付费的值不值"
date: 2026-06-21
tags: [AI量化, 数据源, AkShare, Tushare, Wind, 量化数据]
collection: 代码人生
summary: 做量化要花多少钱在数据上？免费数据真的够用吗？这篇文章梳理了从AkShare到Wind的主流数据源，给出不同阶段的选择建议。
---

## 数据是量化的基础

做量化研究，代码可以自己写，策略可以自己想，但数据不能自己生成。

数据的质量和丰富程度，直接决定了策略能走多远。用错数据（有未来信息泄漏、复权方式错误、停牌数据缺失），再好的模型也白搭。

这篇文章整理一下常见数据源，从免费到付费，说说各自的适用场景。

---

## 免费数据源

### AkShare

GitHub Star 超过 10000 的开源 Python 库，覆盖最广的免费数据源。

```bash
pip install akshare
```

```python
import akshare as ak

# 获取个股历史行情（前复权）
df = ak.stock_zh_a_hist(
    symbol="000001",
    period="daily",
    start_date="20240101",
    end_date="20260601",
    adjust="qfq"  # qfq=前复权, hfq=后复权
)

# 获取实时行情
realtime = ak.stock_zh_a_spot_em()

# 财务数据
income = ak.stock_financial_report_sina(stock="000001", symbol="利润表")

# ETF 数据
etf_df = ak.fund_etf_hist_em(symbol="510050")

# 北向资金
north_df = ak.stock_hsgt_north_money_sina()
```

**能拿到的数据**：
- 日线/周线/月线 OHLCV（A股、港股、美股）
- 财务报表（利润表、资产负债表、现金流量表）
- 行业板块行情
- ETF 行情和申赎数据
- 北向资金、融资融券
- 宏观经济数据（GDP、CPI、利率）

**优点**：完全免费，数据覆盖广，更新频繁

**缺点**：
- 数据来源是网页抓取，接口偶尔失效
- 没有历史 Tick 数据和分钟级数据（日线以上才有）
- 数据质量参差不齐，需要自己做清洗

**适合**：入门学习、日线低频策略研究

---

### Tushare Pro

国内老牌量化数据平台。注册获取 Token，基础功能免费，高级功能需要积分。

```bash
pip install tushare
```

```python
import tushare as ts

ts.set_token("你的token")
pro = ts.pro_api()

# 日线行情
df = pro.daily(ts_code="000001.SZ", start_date="20240101", end_date="20260601")

# 财务数据
fina = pro.income(ts_code="000001.SZ", period="20241231")

# 指数成分股
cons = pro.index_weight(index_code="000300.SH")  # CSI300成分股

# 复权因子
adj = pro.adj_factor(ts_code="000001.SZ")
```

**积分体系**：
- 普通用户（0积分）：日线、基本财务数据，访问频次低
- 600积分：分钟级数据、更多财务字段
- 2000积分：Tick 数据、完整财务数据

积分通过充值或社区贡献获取。600 积分需要充值约 300 元。

**优点**：数据质量比 AkShare 好，接口稳定，文档完整

**缺点**：免费功能受限，分钟数据要付费

**适合**：认真做量化研究，愿意花少量钱获得更好的数据质量

---

### Baostock

专注 A 股历史数据，免费无限制。

```python
import baostock as bs

lg = bs.login()
rs = bs.query_history_k_data_plus(
    "sz.000001",
    "date,code,open,high,low,close,volume,amount,adjustflag",
    start_date="2024-01-01",
    end_date="2026-06-01",
    frequency="d",
    adjustflag="2"  # 2=前复权
)

data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

bs.logout()
```

**特点**：免费、稳定、支持分钟线（5分钟、15分钟、30分钟、60分钟），但只有 A 股日线级别以上，没有 Tick。

**适合**：对分钟级 A 股数据有需求但不想付费

---

### 雅虎财经（yfinance）

海外数据的不二选择。

```python
import yfinance as yf

# 美股
aapl = yf.Ticker("AAPL")
hist = aapl.history(period="2y")

# 港股
tencent = yf.Ticker("0700.HK")

# A股（部分支持）
ping_an = yf.Ticker("601318.SS")  # 上交所
```

**优点**：完全免费，美股/港股覆盖非常全，分钟数据有

**缺点**：A 股数据质量差（很多股票缺失），不适合做 A 股量化

**适合**：做美股/港股量化研究

---

## 付费数据源

### Wind（万得）

国内金融数据的行业标准。机构投资者用的最多。

```python
from WindPy import w

w.start()

# 日线数据
data = w.wsd("000001.SZ", "close,volume,pct_chg", "2024-01-01", "2026-06-01")

# 财务数据
fin = w.wsd("000001.SZ", "roe,eps,pe_ttm", "2024-01-01", "2026-06-01", "Period=Q")

# 实时行情
rt = w.wsq("000001.SZ", "rt_last,rt_vol,rt_chg_pct")
```

**价格**：个人版约 ¥8000-15000/年，机构版更贵。学生可通过学校申请低价或免费使用。

**优点**：数据完整、质量高、覆盖最全（包括债券、期货、期权、宏观等），接口稳定

**缺点**：贵，个人用有点难受

**适合**：专业量化研究、机构

---

### 聚宽（JoinQuant）

国内量化平台，按需付费，提供研究环境 + 数据 API。

```python
# 在聚宽研究环境中
from jqdata import *

# 日线
df = get_price("000001.XSHE", start_date="2024-01-01", end_date="2026-06-01", frequency="daily")

# 分钟
min_df = get_price("000001.XSHE", start_date="2026-06-01", end_date="2026-06-28", frequency="minute")

# 因子数据
factor = get_factor_values(["000001.XSHE", "000002.XSHE"], ["pe_ratio", "ps_ratio"])
```

**价格**：¥299/月起，按 CPU 时长计费

**优点**：提供完整的研究环境（Jupyter + 数据），分钟数据、Tick 数据都有，有 QA 社区

**缺点**：价格不低，数据下载到本地有限制

**适合**：中等预算、需要分钟数据、喜欢在线研究环境

---

## 不同阶段的数据选择建议

**阶段一：入门学习**（预算 0）

```
主力：AkShare（日线行情 + 财务数据）
辅助：Baostock（分钟线）
美股：yfinance
```

这个组合做日线低频策略完全够用。用 Qlib 的免费数据工具也可以。

**阶段二：认真研究**（预算 ¥300-600/年）

```
主力：Tushare Pro 600积分（分钟数据、稳定接口）
辅助：AkShare（补充特色数据）
```

**阶段三：正式实盘**（预算 ¥3000-8000/年）

```
主力：聚宽 or 天勤量化（完整分钟+Tick数据）
实盘接口：VeighNa + 券商API
备用：AkShare（宏观数据）
```

**阶段四：机构级**（预算 > ¥10000/年）

```
主力：Wind
数据库：自建 ClickHouse 历史数据库
另类数据：视具体策略需求购买
```

---

## 自建数据库

当数据量大了（几千只股票 × 分钟级 × 几年），每次分析都实时拉接口会很慢。建议自建本地数据库：

```python
# 用 ClickHouse 存储分钟级行情
# 写入速度极快，查询性能好

import clickhouse_connect

client = clickhouse_connect.get_client(host="localhost")

client.command("""
CREATE TABLE IF NOT EXISTS stock_minute (
    date       Date,
    datetime   DateTime,
    code       String,
    open       Float32,
    high       Float32,
    low        Float32,
    close      Float32,
    volume     UInt64,
    amount     Float64
) ENGINE = MergeTree()
ORDER BY (code, datetime)
""")

# 批量写入
client.insert("stock_minute", df.values.tolist(), column_names=df.columns.tolist())
```

CSI500 成分股 5 年分钟数据大约 50GB，ClickHouse 查询一年的数据只需几秒。

---

## 数据清洗是绕不开的

不管用哪个数据源，都需要自己做清洗：

1. **复权处理**：一定要用复权后的价格计算收益，否则遇到分红送股数据就乱了
2. **停牌处理**：停牌期间的数据要填充或者剔除
3. **退市处理**：历史数据里要包含已退市股票，避免幸存者偏差
4. **涨跌停标记**：涨停买不进、跌停卖不出，这些状态需要明确标记

```python
def clean_stock_data(df: pd.DataFrame) -> pd.DataFrame:
    # 删除停牌（成交量为0）
    df = df[df['volume'] > 0]
    # 标记涨跌停
    df['limit_up'] = df['close'] >= df['prev_close'] * 1.099
    df['limit_down'] = df['close'] <= df['prev_close'] * 0.901
    return df
```

数据清洗花的时间，往往比写策略本身还多。但这是绕不过的基础工作，没有干净的数据，什么模型都跑不出好结果。
