# 本地量化内核 local_quant

## 目标

把本地量化从 BigQuant 脚本里拆出来，形成独立的本地研究/回测内核。

核心原则：

> 数据源可以很多，策略只能面对一种统一格式。

BigQuant、通达信、腾讯、新浪、东方财富都只是数据源；策略代码不直接绑定任何一个平台的表名、列名或接口。

## 为什么要另起一块

原先 `v21_small_capital_5000/` 是 BigQuant 研究链的一部分，里面天然混着：

- BigQuant 表名；
- `dai.query`；
- AIStudio 执行顺序；
- BigTrader 回测口径；
- V20/V21/V22/V23 历史实验脚本。

这对复盘 BigQuant 版本很有用，但不适合长期本地化。

本地化后需要支持：

- 通达信日线 / 5分钟数据；
- mootdx 解析；
- 腾讯/新浪公开行情；
- BigQuant 一次性导出缓存；
- 统一字段；
- 本地策略和本地回测。

所以必须独立成 `scripts/stock/local_quant/`。

## 分层架构

```text
外部数据源
  ├─ BigQuant tables / exported csv
  ├─ 通达信本地文件 / mootdx
  ├─ 腾讯 fqkline
  ├─ 新浪 30m
  └─ 东方财富/其他
        ↓
adapters/ 数据源适配器
        ↓
schemas/ 统一字段规范
        ↓
data/stock_local/normalized/ 标准化数据
        ↓
engine/ 特征、信号、仓位、回测公共逻辑
        ↓
strategies/ 策略实现，例如 V22/V23C
        ↓
backtests/ 本地回测与诊断
        ↓
导出：报告 / 图表 / BigQuant positions variant
```

## 目录说明

```text
scripts/stock/local_quant/
├── adapters/     # 各数据源读取与标准化：tdx, bigquant_export, tencent, sina...
├── schemas/      # 统一 schema 定义、字段校验、交易日/股票代码规范
├── engine/       # 数据加载、复权、重采样、信号/仓位/费用/回测公共组件
├── strategies/   # 策略逻辑，只读统一 schema，不关心数据源
├── backtests/    # 回测入口、年度拆分、个股贡献、订单审计
└── utils/        # 通用工具

data/stock_local/
├── raw/          # 原始数据，不改动，按数据源分目录
├── normalized/   # 标准化后的 bars/signals/positions
├── features/     # 中间特征，例如缠论结构、30m触发器
├── signals/      # 标准化信号
├── positions/    # 标准化目标仓位
├── backtests/    # 本地回测结果
└── meta/         # 数据源、更新时间、覆盖范围、质量检查
```

## 统一 schema

详见：

```text
schemas/STANDARD_SCHEMA.md
```

最重要的三类表：

- `bars`：行情 K 线；
- `signals`：策略/缠论信号；
- `positions`：目标仓位；

策略只允许依赖这些标准表，不允许直接依赖外部源字段。

## 数据源适配器原则

每个适配器只做三件事：

1. 读取某个数据源原始格式；
2. 转成标准 schema；
3. 输出到 `data/stock_local/normalized/` 或对应标准目录。

适配器不要写策略逻辑。

例如：

```text
adapters/tdx_adapter.py              # 通达信/mootdx → 标准 bars
adapters/bigquant_export_adapter.py  # BigQuant 导出 CSV → 标准 bars/signals/positions
adapters/tencent_adapter.py          # 腾讯 fqkline → 标准 bars
adapters/sina_adapter.py             # 新浪 30m → 标准 bars
```

## 策略层原则

策略文件只接收标准数据：

```python
bars = load_bars(freq="30m", source="normalized")
signals = load_signals(name="v11_d1_30m")
positions = strategy.generate_positions(bars, signals, params)
```

禁止在策略里写：

```python
# ❌ 不要这样
if source == "bigquant":
    use column xxx
elif source == "tdx":
    use column yyy
```

数据源差异必须在 adapter 层解决。

## 与 BigQuant 目录的关系

- `v21_small_capital_5000/`：保留为 BigQuant 研究链和历史实验复盘目录。
- `local_quant/`：新本地内核，用于后续通达信/mootdx、本地 V23C 复核、本地回测。
- 最终如果本地策略验证通过，再从 `local_quant` 导出 BigQuant 需要的 positions 表格式，回写/上传到 BigQuant。

## 当前优先任务

1. 等老板提供通达信日线和 5分钟数据包。
2. 写 `tdx_adapter.py`，把通达信数据转为标准 bars。
3. 写 5m → 30m 聚合器。
4. 迁移/复刻 V22/V23C 策略逻辑，让它们读标准 schema。
5. 本地复核 V23C `v23c_stop_pre5_990`。

## 红线

- 不要把 BigQuant 和本地源继续混写在同一策略脚本里。
- 不要在策略层处理字段兼容。
- 不要删除历史 BigQuant 脚本。
- 不要在 BigQuant 额度不足时运行密集读取。
- 本地 raw 数据只读保存，转换后的数据另存 normalized。
