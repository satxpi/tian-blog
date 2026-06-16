# CLAUDE.md - BigQuant 缠论小资金策略研究

## 项目定位

这是老板的 BigQuant 缠论策略研究目录，核心是从 V21/V22/V23 演进出适合 5000 元小资金真实成交的策略。请在本目录内工作，不要默认扫描整个 workspace。

## 当前主结论

- 当前主版本：V22-5000「缠论 sell 信号反向短线反弹策略」。
- 主 variant：`v22_hold5_60pct_amt50m_exbottom5`。
- 表：复用 `chanlun_v21_small_capital_5000_positions`，不要轻易新建表。
- V23C 候选：`v23c_stop_pre5_990`，只是候选，尚未完成年度拆分、个股贡献、BigTrader 订单级复核。

## BigQuant 额度纪律

当前 BigQuant 每周 cell 额度接近耗尽，近期记录约：`99,971,706 / 100,000,000`。

除非老板明确批准，否则：

1. 不要运行密集 `dai.query`。
2. 不要全量读取 `cn_stock_bar30m`。
3. 不要运行 `21_bigquant_export_to_local_cache.py`。
4. 不要上传 V23 variant。
5. 不要新建 BigQuant 表。

优先使用本地缓存：

```text
data/stock_cache/daily/
data/stock_cache/m30/
data/stock_cache/positions/
data/stock_cache/signals/
data/stock_cache/*_bq/
```

## 通达信 / mootdx 路线

老板准备提供通达信日线和 5 分钟数据，并提到可用第三方 `mootdx` 解析。

拿到数据后的优先目标：

1. 读取通达信日线与 5 分钟数据。
2. 转成统一 CSV/Parquet 格式，对齐 BigQuant 字段：`date, instrument, open, high, low, close, volume, amount`。
3. 用 5 分钟聚合生成 30 分钟数据。
4. 本地复跑 V23C `v23c_stop_pre5_990`，避免继续消耗 BigQuant 额度。

## 关键脚本顺序

- `01_build_small_capital_positions_v21.py`：V21 小资金 positions。
- `05_v22_readonly_sweep.py`：V22 只读参数扫描。
- `08_append_v22_positions_to_existing_table.py`：把 V22 variant 追加到既有 positions 表。
- `09_v22_annual_return_check.py` / `10_v22_stock_contribution_check.py`：V22 年度与个股贡献。
- `11_v22_signal_audit.py`：V22 信号审计。
- `12`~`17`：V23A/V23B m30-first/filter 只读实验。
- `18_v23c_m30_failure_exit.py`：V23C 30m 失败提前退出扫描。
- `19_v23c_best_diagnostics.py`：V23C 候选诊断，当前因额度不足不应继续跑。
- `20_local_market_cache.py`：公开行情本地缓存，可用。
- `21_bigquant_export_to_local_cache.py`：BigQuant 一次性导出脚本，等待额度恢复后才运行。
- `24_make_static_600585_execution_from_cache.py`：用本地缓存生成 600585 执行图。

## 策略事实

V22 不是传统缠论 buy 买、sell 卖，而是：

> 原始缠论 sell 类信号出现后，反向买入，持有约 5 天，吃短线反弹。

V22 5000 元 BigTrader 结果：

- 累计收益率：161.31%
- 年化收益率：21.73%
- 最大回撤：14.06%
- 夏普：1.33
- 胜率：58.76%
- 盈亏比：1.48

V23A/V23B 当前不优于 V22；V23C 只是微弱候选。

## 修改纪律

1. 先读相关 README/报告，不要凭文件名乱猜。
2. 新实验优先只读、本地、CSV/Parquet，不上传、不建表。
3. 每个脚本要有明确输入、输出、variant、是否消耗 BigQuant 额度。
4. 涉及 BigQuant 写表/读全量数据前必须先提醒并等待确认。
5. 不要删除旧脚本和旧报告。
6. 不要把中文转成 Unicode 转义。
7. 文件名尽量带顺序号，便于 AIStudio/本地复跑。

## 验收命令

修改 Python 后至少运行语法检查：

```bash
python3 -m py_compile <script.py>
```

如果脚本不依赖 BigQuant，可跑最小样本或 `--help`。如果会消耗 BigQuant 额度，只做静态检查并说明未运行原因。

完成后展示：

```bash
git diff --stat
git diff -- <changed-files>
```

## 推荐 Claude Code 工作方式

- 从本目录启动 Claude Code。
- 大改前先 `/plan`。
- 每次只做一个小目标：比如“写通达信转换器”“本地聚合5m到30m”“生成V23C本地诊断”。
- 长会话用 `/compact`；换任务用 `/clear`。
