# 本地量化项目文档

## 项目名称

本地量化内核：`local_quant`

## 项目目标

建立一套脱离 BigQuant 额度限制的本地量化研发底座。

核心目标不是立刻替代 BigQuant，而是：

1. 本地保存和标准化多数据源行情；
2. 本地复刻 V22/V23C 策略逻辑；
3. 本地完成大部分研究、调参、诊断；
4. 只有最终候选才导出到 BigQuant/BigTrader 做订单级验证。

一句话：

> BigQuant 做最终验证，本地做日常研发。

## 开发分工

### Claude Code 负责

以后实际代码实现优先交给 Claude Code，包括：

- Python 数据适配器；
- 通达信/mootdx 读取；
- 5分钟聚合30分钟；
- 本地回测引擎；
- V22/V23C 策略迁移；
- 自动化测试或样本验证脚本；
- 修改已有 Python/HTML/JS 代码。

Claude Code 启动目录应尽量小：

```bash
cd /root/.openclaw/workspace/scripts/stock/local_quant
claude
```

或针对网站：

```bash
cd /root/.openclaw/workspace/stock
claude
```

不要从 `/root/.openclaw/workspace` 根目录启动，避免上下文过大、浪费流量。

### 主助手负责

主助手负责：

- 拆任务；
- 写项目文档和规则；
- 给 Claude Code 下明确指令；
- 控制 BigQuant 额度和数据风险；
- 验收 diff、运行测试、提交；
- 与老板同步结论。

主助手默认不直接写业务代码，除非是极小的文档、配置、骨架或老板明确要求。

## 当前数据现实

### 通达信日线数据

老板反馈：通达信日线数据可以按月下载，目前已下载到 2005 年 7 月。

判断：

- 日线历史足够长；
- 可用于长期趋势、日线结构、复权/不复权口径检查；
- 后续应优先保存原始数据，再通过 adapter 转成统一 schema。

### 通达信 5分钟数据

老板反馈：通达信 5分钟数据只能下载近约 700 天，约两年。

判断：

- 对全周期 2021-2026 的 V23C 复核不够；
- 但对当前策略研发已经基本够用；
- 两年 5分钟数据可覆盖近期市场环境，足够验证：
  - 5m → 30m 聚合；
  - m30 触发器；
  - V23C 反弹失败提前退出；
  - 本地回测管线；
  - 与 BigQuant 近期数据口径对齐。

结论：

> 两年 5分钟数据够做本地内核第一阶段，不必为了全历史 30m 卡住项目。

## 数据策略

### 第一阶段：以通达信近两年 5分钟数据跑通闭环

目标：

1. 读取通达信日线和 5分钟数据；
2. 统一股票代码格式为 `600000.SH` / `000001.SZ`；
3. 标准化为 bars schema；
4. 5分钟聚合成30分钟；
5. 用近期数据验证 V23C m30 失败提前退出逻辑；
6. 输出本地回测报告。

这阶段不追求全历史，只追求流程正确。

### 第二阶段：补 BigQuant 历史 30m 缓存

等 BigQuant cell 额度恢复后，只做一次性导出：

- V22 主 variant positions；
- V11 信号表；
- 历史日线；
- 历史30m。

导出后保存到：

```text
data/stock_local/raw/bigquant/
data/stock_local/normalized/
```

后续实验不再反复 `dai.query`。

### 第三阶段：本地和 BigQuant 对齐验证

用同一批股票、同一时间段，对比：

- BigQuant 30m；
- 通达信 5m 聚合 30m；
- 腾讯/新浪公开行情。

重点检查：

- 时间戳口径；
- 前复权/不复权；
- 成交量单位：股/手；
- 成交额单位：元/万元；
- 停牌/缺失 K 线；
- 交易日对齐。

## 架构原则

### 数据源适配器必须存在

不同数据源字段、格式、表名都不同，不能让策略层直接处理。

错误方式：

```python
if source == "bigquant":
    ...
elif source == "tdx":
    ...
elif source == "sina":
    ...
```

正确方式：

```text
source raw data
  ↓
adapter
  ↓
standard schema
  ↓
strategy
```

### 策略只认标准表

策略层只读：

- `bars`；
- `signals`；
- `positions`。

标准 schema 详见：

```text
scripts/stock/local_quant/schemas/STANDARD_SCHEMA.md
```

## 当前目录

代码：

```text
scripts/stock/local_quant/
```

数据：

```text
data/stock_local/
```

## 优先任务清单

### P0：等待/接收通达信数据

老板提供通达信日线与 5分钟数据包后，先只做文件识别和样本读取，不直接批量转换。

需要确认：

- 数据文件格式；
- 是否为通达信原始 `.day` / `.lc5` 等文件；
- 是否可由 mootdx 直接解析；
- 股票代码命名规则；
- 复权口径；
- 时间覆盖范围。

### P1：Claude Code 实现 tdx adapter

交给 Claude Code 的任务：

```text
在 scripts/stock/local_quant/ 中实现通达信数据适配器。
要求：
1. 读取老板提供的日线和5分钟数据样本；
2. 输出标准 bars schema；
3. volume 统一为股，amount 统一为元；
4. instrument 统一为 600000.SH / 000001.SZ；
5. 输出 meta 质量报告；
6. 提供小样本验证命令。
```

### P2：Claude Code 实现 5m → 30m 聚合

规则：

- open = 第一根 5m open；
- high = 区间最高 high；
- low = 区间最低 low；
- close = 最后一根 5m close；
- volume = 区间求和；
- amount = 区间求和；
- datetime = 30m K 线结束时间。

需要特别检查 A 股午休和收盘时间：

```text
09:30-11:30
13:00-15:00
```

### P3：迁移 V23C 本地验证

先只做近两年验证，不追全历史。

目标：

- 复刻 `v23c_stop_pre5_990`；
- 输出年度/月度收益；
- 输出个股贡献；
- 输出提前退出触发明细；
- 与 V22 baseline 对比。

## 风险与口径

### 两年 5分钟数据的限制

限制：

- 不能完整复现 2021-2026 全周期；
- 对 2021-2024 的历史回测不足；
- 不能直接替代 BigTrader 最终验证。

但足够用于：

- 本地系统打通；
- 近期行情验证；
- m30 规则调试；
- 失败提前退出逻辑诊断；
- 数据适配器稳定性测试。

### BigQuant 仍然保留

BigQuant 不废弃。

它的角色变成：

- 历史数据补齐；
- 标准结果对照；
- BigTrader 订单级最终验证；
- 生产/模拟盘对接。

## 当前决策

1. 本地量化另起 `local_quant`，不再和 BigQuant 实验脚本混写。
2. 必须做 adapter，策略层不处理数据源差异。
3. 通达信两年 5分钟数据足够做第一阶段。
4. 后续代码实现优先交给 Claude Code。
5. 主助手负责项目文档、任务拆解和验收。
