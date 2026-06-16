# CLAUDE.md - local_quant 本地量化内核

## 定位

这是股票策略的本地量化内核，不是 BigQuant 脚本目录。

目标：通过数据适配器统一 BigQuant、通达信、腾讯、新浪等来源，让策略只依赖标准 schema。

## 核心原则

1. 数据源多样，策略接口唯一。
2. adapter 负责字段映射、单位转换、代码格式、复权标记、时间格式。
3. strategy 不允许直接处理 BigQuant/通达信/腾讯/新浪的原始字段差异。
4. raw 数据只读保存，normalized 数据才给策略使用。
5. 不要把 BigQuant 额度密集读取逻辑写进这里；BigQuant 只作为导出 CSV/缓存来源。
6. 实际 Python 代码实现优先由 Claude Code 完成；主助手负责拆任务、验收和提交。

## 开发分工

- Claude Code：写 adapter、resample、strategy、backtest、测试脚本等代码。
- 主助手：写项目文档、拆解任务、给 Claude Code 下指令、检查 diff、运行验收、控制风险。
- 若任务只是文档、目录骨架、规则沉淀，主助手可以直接处理。

## 目录

```text
adapters/     # 数据源适配器
schemas/      # 标准 schema 和校验
engine/       # 公共数据加载、重采样、回测、费用、仓位逻辑
strategies/   # 策略逻辑，只读标准 schema
backtests/    # 本地回测入口和诊断
utils/        # 通用工具
```

对应数据目录：

```text
data/stock_local/raw/
data/stock_local/normalized/
data/stock_local/features/
data/stock_local/signals/
data/stock_local/positions/
data/stock_local/backtests/
data/stock_local/meta/
```

## 必读文档

修改本目录前先读：

```text
README.md
schemas/STANDARD_SCHEMA.md
```

如果涉及 V22/V23C 逻辑，再读：

```text
../v21_small_capital_5000/CLAUDE.md
../v21_small_capital_5000/V22_FINAL_STRATEGY.md
../v21_small_capital_5000/V23C_M30_FAILURE_EXIT.md
```

## 当前优先方向

老板将提供通达信日线和 5分钟数据。当前信息：

- 日线可按月下载，已下载到 2005 年 7 月，历史长度足够。
- 5分钟数据只能下载近约 700 天，约两年。
- 两年 5分钟数据不够完整复现 2021-2026，但足够打通本地内核第一阶段，验证 5m→30m 聚合、m30 触发器、V23C 失败提前退出和近期回测。

优先做：

1. `adapters/tdx_adapter.py`：读取通达信/mootdx 数据，输出标准 bars。
2. `engine/resample.py`：5m 聚合成 30m。
3. `strategies/v22_inverse_rebound.py`：迁移 V22 逻辑，读取标准 signals/bars。
4. `strategies/v23c_failure_exit.py`：迁移 V23C 失败提前退出逻辑。
5. `backtests/run_local_backtest.py`：本地回测和年度/贡献诊断。

详细计划见：

```text
PROJECT_PLAN.md
```

## 标准字段

以 `schemas/STANDARD_SCHEMA.md` 为准。最重要三类：

- `bars`: `datetime,date,instrument,freq,open,high,low,close,volume,amount,source,adjust`
- `signals`: `date,datetime,instrument,signal_name,signal_type,side,price,score,lag_days,source_freq,source,meta_json`
- `positions`: `date,instrument,position,strategy_name,variant,source,meta_json`

## 禁止事项

- 不要在 strategy 里写数据源分支：`if source == "bigquant" ...`。
- 不要修改或删除 `data/stock_local/raw/` 原始数据。
- 不要直接运行 BigQuant 读取脚本。
- 不要删除历史 BigQuant 实验目录。
- 不要把中文写成 Unicode 转义。
- 不要提交大体积行情数据，除非老板明确要求。

## 验收

Python 文件修改后至少运行：

```bash
python3 -m py_compile <changed_python_file>
```

适配器应支持小样本验证，输出行数、日期范围、重复键数量、字段缺失情况。

完成后展示：

```bash
git diff --stat
git diff -- <changed-files>
```
