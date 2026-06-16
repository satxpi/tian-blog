# 通达信样本数据分析报告

## 样本位置

```text
data/stock_local/raw/sample/
```

## 样本文件

当前实际检测到 16 个文件，8 组日线 + 5分钟配对：

```text
sh000001.day / sh000001.lc5
sh000002.day / sh000002.lc5
sh000003.day / sh000003.lc5
sh000009.day / sh000009.lc5
sz000001.day / sz000001.lc5
sz000002.day / sz000002.lc5
sz000004.day / sz000004.lc5
sz000006.day / sz000006.lc5
```

备注：老板说“上海5个、深圳5个”，但当前目录实际只有上海4组、深圳4组。可能还有文件没放上来，或这批只是随手样本。

## 总结论

样本可以稳定解析。

`.day` 和 `.lc5` 都是标准通达信二进制结构：

```text
每条记录 32 字节
文件大小 % 32 == 0
```

这意味着后续可以直接写 adapter，不必依赖复杂反推。

## .day 日线格式

推定结构：

```python
struct format: <IIIIIfII
```

字段：

| 顺序 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 1 | date | uint32 | YYYYMMDD，例如 20240716 |
| 2 | open | uint32 | 开盘价 * 100 |
| 3 | high | uint32 | 最高价 * 100 |
| 4 | low | uint32 | 最低价 * 100 |
| 5 | close | uint32 | 收盘价 * 100 |
| 6 | amount | float32 | 成交额，单位基本为元 |
| 7 | volume | uint32 | 成交量，个股样本看起来为股；指数样本口径需谨慎 |
| 8 | reserved | uint32 | 保留字段/指数扩展字段 |

价格换算：

```text
price = raw_price / 100
```

## .lc5 5分钟格式

推定结构：

```python
struct format: <HHfffffII
```

字段：

| 顺序 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 1 | date_code | uint16 | 通达信压缩日期 |
| 2 | time_code | uint16 | 分钟数，如 575 = 09:35 |
| 3 | open | float32 | 开盘价 |
| 4 | high | float32 | 最高价 |
| 5 | low | float32 | 最低价 |
| 6 | close | float32 | 收盘价 |
| 7 | amount | float32 | 成交额，单位基本为元 |
| 8 | volume | uint32 | 成交量，个股样本看起来为股 |
| 9 | reserved | uint32 | 保留字段/指数扩展字段 |

日期解码：

```python
year = date_code // 2048 + 2004
rem = date_code % 2048
month = rem // 100
day = rem % 100
```

时间解码：

```python
hour = time_code // 60
minute = time_code % 60
```

示例：

```text
date_code=41767 -> 2024-08-07
time_code=575 -> 09:35:00
```

## 时间范围

### 日线 `.day`

大部分样本：

```text
2024-07-16 -> 2026-06-16
464 条记录
```

例外：

```text
sz000004.day: 2024-07-16 -> 2026-04-27，430 条记录
```

### 5分钟 `.lc5`

大部分样本：

```text
2024-08-07 -> 2025-07-30
237 个交易日
11376 条记录
```

例外：

```text
sh000001.lc5: 2024-08-07 -> 2025-07-08，221 个交易日，10608 条记录
sz000004.lc5: 2024-08-07 -> 2025-07-30，236 个交易日，11328 条记录
```

## 5分钟 K 线日内结构

每个完整交易日有 48 根 5分钟 K 线。

首根：

```text
09:35:00
```

末根：

```text
15:00:00
```

这符合 A 股 4 小时交易时长：

```text
240 分钟 / 5 = 48 根
```

日内交易段应按：

```text
09:35, 09:40, ..., 11:30
13:05, 13:10, ..., 15:00
```

注意：通达信 5分钟 K 线时间戳是“区间结束时间”，不是开始时间。

## 5分钟聚合日线校验

把 `.lc5` 按交易日聚合成日线后，OHLC 与 `.day` 完全对齐：

```text
open  = 当日第一根5m open
high  = 当日5m high最大值
low   = 当日5m low最小值
close = 当日最后一根5m close
```

抽样校验结果：

```text
price_ok = True
amount_ratio = 1.0
```

说明：

- 5分钟价格口径与日线一致；
- 成交额口径与日线一致；
- 可以用 5分钟稳定聚合 30分钟/日线。

## 成交量口径

深圳个股样本：

```text
5m volume 求和 / day volume = 1.0
```

说明深圳个股样本中 volume 基本可视为“股”。

上海样本当前都是 `sh000001/sh000002/sh000003/sh000009` 这类指数，不是普通 `sh600xxx` 个股。指数样本出现：

```text
5m volume 求和 / day volume != 1.0
```

但 amount 仍为 1.0。

判断：

- 指数文件的 volume/reserved 字段可能有特殊口径；
- 不能用指数样本反推上海个股 volume 规则；
- 后续最好补一个 `sh600xxx.day + sh600xxx.lc5` 样本确认上海 A 股个股成交量单位。

## 股票代码映射

文件名规则：

```text
sh000001 -> 000001.SH
sz000001 -> 000001.SZ
```

adapter 应统一输出：

```text
instrument = code + .SH/.SZ
```

## 后续 adapter 输出 schema

`.day` 输出：

```text
datetime = YYYY-MM-DD 15:00:00
date = YYYY-MM-DD
instrument = 000001.SZ / 600000.SH
freq = 1d
open/high/low/close
volume
amount
source = tdx
adjust = unknown 或 none
```

`.lc5` 输出：

```text
datetime = YYYY-MM-DD HH:MM:SS
date = YYYY-MM-DD
instrument
freq = 5m
open/high/low/close
volume
amount
source = tdx
adjust = unknown 或 none
```

## 建议 Parquet 输出路径

```text
data/stock_local/normalized/bars_1d/instrument=000001.SZ/part-000.parquet
data/stock_local/normalized/bars_5m/instrument=000001.SZ/part-000.parquet
data/stock_local/normalized/bars_30m/instrument=000001.SZ/part-000.parquet
```

## 30分钟聚合规则

从 5分钟聚合 30分钟时：

```text
open = 第一根5m open
high = 6根5m high最大值
low = 6根5m low最小值
close = 最后一根5m close
volume = 6根5m volume求和
amount = 6根5m amount求和
datetime = 30分钟区间结束时间
```

日内 30分钟结束时间建议：

```text
10:00
10:30
11:00
11:30
13:30
14:00
14:30
15:00
```

每个完整交易日 8 根 30分钟 K 线。

## 风险与待确认

1. 当前没有 `sh600xxx` 个股样本，上海个股 volume 口径需补样本确认。
2. 当前样本 5分钟只覆盖到 2025-07-30，不是最新两年完整样本；可能是下载进度或随手样本。
3. 复权口径未知，需要后续和通达信设置确认：不复权 / 前复权 / 后复权。
4. `.lc5` 时间戳为区间结束时间，后续和 BigQuant 30m 对齐时必须注意。
5. 指数样本可以解析，但策略股票池主要应使用个股样本验证成交量。

## 结论

通达信样本质量足够进入下一步：

```text
让 Claude Code 编写 tdx_adapter.py 和 5m→30m resample.py
```

但在正式全量转换前，建议老板再补一个上海普通股票样本，例如：

```text
sh600000.day
sh600000.lc5
```

用于确认上海个股成交量单位。
