# stock_local 本地量化数据目录

## 目标

本目录保存本地量化内核使用的数据。原则是：

> raw 原样存，normalized 标准化，策略只读标准化数据。

## 目录

```text
raw/          # 原始数据，按来源保存，不修改
normalized/   # 标准化行情 bars
features/     # 中间特征，如分型、笔、线段、m30触发器
signals/      # 标准化信号
positions/    # 策略目标仓位
backtests/    # 本地回测结果、成交、净值、年度拆分、贡献分析
meta/         # 数据覆盖范围、质量检查、生成时间
```

## 建议来源子目录

```text
raw/tdx/          # 通达信原始文件或解包文件
raw/bigquant/     # BigQuant 一次性导出的 CSV
raw/tencent/      # 腾讯公开行情原始响应/CSV
raw/sina/         # 新浪公开行情原始响应/CSV
```

## 标准行情路径

```text
normalized/bars/1d/{instrument}.csv
normalized/bars/5m/{instrument}.csv
normalized/bars/30m/{instrument}.csv
```

例如：

```text
normalized/bars/30m/600585.SH.csv
```

## 数据纪律

1. `raw/` 下数据只追加、不改写。
2. 适配器输出到 `normalized/`、`signals/`、`positions/`。
3. 每次转换应在 `meta/` 写覆盖范围和质量检查。
4. 大体积数据默认不要提交 git。
5. 策略不得直接读 `raw/`。
