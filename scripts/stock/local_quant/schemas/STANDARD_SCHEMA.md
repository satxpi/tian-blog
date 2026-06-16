# 标准数据 Schema

## 设计原则

1. 策略只读标准 schema。
2. 数据源差异全部在 adapter 层解决。
3. 字段使用英文小写 snake_case。
4. 股票代码统一为 BigQuant 风格：`600000.SH`、`000001.SZ`。
5. 时间字段统一使用北京时间，无时区字符串；落盘时使用 ISO-like 字符串。
6. 所有金额单位必须写清楚，默认人民币元。

## 1. bars：行情 K 线

用于日线、5分钟、30分钟等 OHLCV 数据。

### 路径建议

```text
data/stock_local/normalized/bars/{freq}/{instrument}.csv
```

示例：

```text
data/stock_local/normalized/bars/1d/600585.SH.csv
data/stock_local/normalized/bars/5m/600585.SH.csv
data/stock_local/normalized/bars/30m/600585.SH.csv
```

### 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `datetime` | string | 是 | K线结束时间；日线用 `YYYY-MM-DD 15:00:00` 或保留 `date` |
| `date` | string | 是 | 交易日，`YYYY-MM-DD` |
| `instrument` | string | 是 | 统一股票代码，如 `600585.SH` |
| `freq` | string | 是 | `1d` / `5m` / `30m` / `60m` |
| `open` | float | 是 | 开盘价 |
| `high` | float | 是 | 最高价 |
| `low` | float | 是 | 最低价 |
| `close` | float | 是 | 收盘价 |
| `volume` | float | 否 | 成交量，单位：股。源数据如果是手，adapter 必须乘 100 |
| `amount` | float | 否 | 成交额，单位：元 |
| `source` | string | 是 | 数据源：`tdx` / `bigquant` / `tencent` / `sina` / `eastmoney` |
| `adjust` | string | 否 | 复权类型：`none` / `qfq` / `hfq` / `unknown` |

### 排序与唯一键

```text
unique key = instrument + freq + datetime
sort = instrument, datetime
```

## 2. signals：标准信号表

用于承载缠论点位、反向信号、m30 触发器等。

### 路径建议

```text
data/stock_local/signals/{signal_name}.csv
```

示例：

```text
data/stock_local/signals/v11_d1_30m_points.csv
data/stock_local/signals/v23_m30_bullish_trigger.csv
```

### 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `signal_id` | string | 否 | 可选唯一ID |
| `date` | string | 是 | 信号交易日，`YYYY-MM-DD` |
| `datetime` | string | 否 | 分钟级信号时间 |
| `instrument` | string | 是 | 股票代码 |
| `signal_name` | string | 是 | 信号体系名，如 `v11_d1_30m` |
| `signal_type` | string | 是 | 如 `buy1` / `buy2` / `sell1` / `sell2` / `m30_bullish_trigger` |
| `side` | string | 是 | 原始方向：`buy` / `sell` / `neutral` |
| `price` | float | 否 | 信号价 |
| `score` | float | 否 | 信号强度 |
| `lag_days` | float | 否 | 信号确认滞后天数 |
| `source_freq` | string | 否 | `1d` / `30m` / `5m` |
| `source` | string | 是 | `bigquant` / `local` / `tdx` 等 |
| `meta_json` | string | 否 | 扩展信息 JSON 字符串 |

### 与 BigQuant V11 字段映射

| BigQuant V11 | 标准字段 |
|---|---|
| `date` | `date` |
| `instrument` | `instrument` |
| `point_type` | `signal_type` |
| `point_side` | `side` |
| `signal_price` | `price` |
| `signal_score` | `score` |
| `lag_days` | `lag_days` |
| `v11_reason` / `reason` | `meta_json` |

## 3. positions：目标仓位表

用于策略输出，兼容本地回测和 BigTrader 上传。

### 路径建议

```text
data/stock_local/positions/{strategy_name}_{variant}.csv
```

### 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `date` | string | 是 | 目标仓位日期 |
| `instrument` | string | 是 | 股票代码 |
| `position` | float | 是 | 目标仓位比例，0~1 |
| `strategy_name` | string | 是 | 策略名，如 `chanlun_inverse_rebound` |
| `variant` | string | 是 | 参数版本，如 `v22_hold5_60pct_amt50m_exbottom5` |
| `source` | string | 是 | `local` / `bigquant_export` |
| `meta_json` | string | 否 | 扩展字段 |

### BigTrader 导出字段

上传 BigQuant/BigTrader 时只取：

```sql
date, instrument, position
```

但本地必须保留 `strategy_name`、`variant`、`source`，避免多个版本混在一起。

## 4. trades：本地回测成交表

### 路径建议

```text
data/stock_local/backtests/{strategy_name}_{variant}_trades.csv
```

### 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `datetime` | string | 是 | 成交时间 |
| `date` | string | 是 | 成交交易日 |
| `instrument` | string | 是 | 股票代码 |
| `side` | string | 是 | `buy` / `sell` |
| `price` | float | 是 | 成交价 |
| `shares` | int | 是 | 股数 |
| `amount` | float | 是 | 成交金额，元 |
| `fee` | float | 是 | 手续费/税费，元 |
| `cash_after` | float | 否 | 成交后现金 |
| `position_after` | float | 否 | 成交后持仓市值比例 |
| `strategy_name` | string | 是 | 策略名 |
| `variant` | string | 是 | 参数版本 |

## 5. meta：数据质量与覆盖范围

每次 adapter 写数据时，应同步写 meta：

```text
data/stock_local/meta/{source}_{freq}_summary.csv
```

建议字段：

| 字段 | 说明 |
|---|---|
| `source` | 数据源 |
| `freq` | 频率 |
| `instrument` | 股票代码 |
| `rows` | 行数 |
| `start_datetime` | 起始时间 |
| `end_datetime` | 结束时间 |
| `adjust` | 复权类型 |
| `generated_at` | 生成时间 |
| `raw_path` | 原始文件路径 |
| `normalized_path` | 标准文件路径 |
| `warnings` | 数据质量警告 |

## 代码规范

adapter 输出前必须校验：

1. 必填字段存在；
2. `instrument + freq + datetime` 不重复；
3. OHLC 不为空且 `high >= low`；
4. `volume` 单位统一为股；
5. `amount` 单位统一为元；
6. 按 `instrument, datetime` 排序。
