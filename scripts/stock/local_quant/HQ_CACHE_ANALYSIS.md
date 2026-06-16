# 通达信 hq_cache.zip 分析报告

## 文件位置

```text
data/stock_local/raw/sample/hq_cache.zip
```

## 基本统计

```text
压缩包大小：约 10.8 MB
文件数量：93
解压后大小：约 83.2 MB
```

这是通达信行情缓存目录，不是单一名称表。里面包含证券代码名称、行业、板块、财务/股本、期权、基金/ETF、可转债、港股/北交所等多类缓存。

## 关键文件清单

### 1. A股/指数/基金/债券代码名称主表：`*.tnf`

```text
hq_cache/shs.tnf   # 上海市场，约 27,267 条
hq_cache/szs.tnf   # 深圳市场，约 23,452 条
hq_cache/bjs.tnf   # 北交所，约 345 条
```

这是当前最有用的文件，可以生成：

```text
data/stock_local/meta/instruments.csv
```

已验证样例：

| instrument | name | source |
|---|---|---|
| `000001.SZ` | 平安银行 | `szs.tnf` |
| `000002.SZ` | 万 科Ａ | `szs.tnf` |
| `000004.SZ` | *ST国华 | `szs.tnf` |
| `000006.SZ` | 深振业Ａ | `szs.tnf` |
| `600000.SH` | 浦发银行 | `shs.tnf` |
| `600585.SH` | 海螺水泥 | `shs.tnf` |
| `000001.SH` | 上证指数 | `shs.tnf` |
| `399001.SZ` | 深证成指 | `szs.tnf` |

### `.tnf` 格式结论

当前样本可按以下方式解析：

```text
文件头：50 字节
记录长度：360 字节
记录起点：offset = 50 + n * 360
代码字段：record[0:31]，GB18030/零结尾字符串
名称字段：record[31:80]，GB18030/零结尾字符串
```

示例：

```python
code = record[0:31].split(b'\0', 1)[0].decode('gb18030')
name = record[31:80].split(b'\0', 1)[0].decode('gb18030')
```

粗略统计：

```text
总记录：51,064
SH：27,267
SZ：23,452
BJ：345
```

粗略类型估计：

```text
A股股票：约 5,209
指数：约 789
基金/ETF：约 7,782
债券/可转债：约 2,766
其他：约 34,175
```

类型估计只是按代码段粗分，正式字段后续还需要更细口径。

---

### 2. 行业分类：`tdxhy.cfg`

```text
hq_cache/tdxhy.cfg
```

编码：UTF-8。

示例：

```text
0|000001|T1001|||X500102
1|600585|T020602|||X150101
```

用途：

- 可给股票补通达信行业代码；
- 字段含义需要后续解析字典，但已经能做到 code → industry_code。

建议输出：

```text
data/stock_local/meta/tdx_industry_map.csv
```

字段建议：

```text
market_flag,code,instrument,tdx_industry_code,tdx_industry_ext_code,source_file
```

---

### 3. 主营/业务扩展：`specgpext.txt`

```text
hq_cache/specgpext.txt
```

编码：GB18030。

示例：

```text
0|000001|零售金融业务|95|10||||238.22|14.63|
1|600585|建材行业（自产品销售）-42.5级水泥|95|12||||-18.84|-19.63|
```

用途：

- 可补主营业务/业务描述；
- 对策略本身暂时不是必须，但对看板展示、股票解释有用。

建议输出：

```text
data/stock_local/meta/tdx_business_profile.csv
```

---

### 4. 财务/股本基础表：`base.dbf`

```text
hq_cache/base.dbf
```

DBF 结构已识别：

```text
DBF version: 3
记录数：7,792
字段数：40
记录长度：481
更新时间：2026-06-16 附近
```

字段包括：

```text
SC        市场标记
GPDM      股票代码
GXRQ      更新日期
ZGB       总股本
GJG       国家股
FQRFRG    发起人法人股
FRG       法人股
BG        B股
HG        H股
LTAG      流通A股
ZGG       职工股
ZPG       转配股
ZZC       总资产
LDZC      流动资产
GDZC      固定资产
WXZC      无形资产
CQTZ      长期投资
LDFZ      流动负债
CQFZ      长期负债
ZBGJJ     资本公积金
JZC       净资产
ZYSY      主营收入
ZYLY      主营利润
QTLY      其他利润
YYLY      营业利润
TZSY      投资收益
BTSY      补贴收入
YYWSZ     营业外收支
SNSYTZ    上年损益调整
LYZE      利润总额
SHLY      税后利润
JLY       净利润
WFPLY     未分配利润
TZMGJZ    每股净资产
DY        地域
HY        行业
ZBNB      资本内部?
SSDATE    上市日期
MODIDATE  修改日期
GDRS      股东人数
```

用途：

- 可作为基本面/股本/上市日期元信息；
- 本地短线策略第一阶段不是必须；
- 后续做过滤条件或看板补充时有用。

---

### 5. 指数/统计扩展：`tdxzsbase*.cfg`, `tdxstat*.cfg`

```text
hq_cache/tdxzsbase.cfg
hq_cache/tdxzsbase2.cfg
hq_cache/tdxstat.cfg
hq_cache/tdxstat2.cfg
```

这些是通达信统计指标/指数基础数据，包含日期、成交、估值或统计字段。字段较多，当前不建议先接入策略层。

用途：

- 市场宽度/指数看板；
- 估值/统计展示；
- 后续单独研究。

---

### 6. ETF/基金/可转债/期权扩展

```text
specetfdata.txt
specjjdata.txt
speckzzdata.txt
ggqqcode.txt
szqqcode.txt
code2name.ini
code2name_hk.ini
code2name_qq.ini
```

用途：

- ETF、基金、可转债、期权信息；
- 当前 V22/V23C 股票策略暂不需要；
- 可作为未来扩展。

---

### 7. 板块/概念/行业块

```text
tdxbk.cfg
spblock.dat
csiblock.dat
jjblock.dat
mgblock.dat
hkblock.dat
infoharbor_block.dat
relation.dat
```

用途：

- 概念板块；
- 行业板块；
- 关系/分类映射；
- 后续可以做板块过滤、归因、看板展示。

当前不建议第一阶段解析太深，先把代码名称表落地。

---

## 对 local_quant 的直接价值

### P0：先做 instruments 元信息表

最先应该实现：

```text
adapters/tdx_hq_cache_adapter.py
```

输入：

```text
hq_cache.zip 或解压后的 hq_cache/ 目录
```

输出：

```text
data/stock_local/meta/instruments.csv
```

字段建议：

```text
instrument,code,tdx_symbol,market,name,type_guess,source_file,updated_at
```

可选输出 Parquet：

```text
data/stock_local/meta/instruments.parquet
```

### P1：把名称补进 bars meta / 看板

行情 bars 仍然只保留：

```text
instrument
```

不要把 name 冗余写进每一行 K 线，否则分钟线数据膨胀。

显示层或诊断层需要名称时，通过 `instruments.csv/parquet` join：

```text
bars.instrument -> instruments.instrument -> name
```

### P2：行业/主营后续再接

等 `instruments` 稳定后，再考虑：

```text
tdxhy.cfg -> industry map
specgpext.txt -> business profile
base.dbf -> fundamental/basic info
```

---

## 注意事项

1. `hq_cache.zip` 是用户上传原始缓存，不应直接提交 git。
2. `shs.tnf/szs.tnf/bjs.tnf` 里不只有 A股股票，还有指数、基金、债券、ETF、回购等，必须加类型过滤。
3. `.tnf` 名称字段为 GB18030 编码，不能用 UTF-8 硬解。
4. 代码相同但市场不同必须保留市场后缀，例如：
   - `000001.SH` = 上证指数
   - `000001.SZ` = 平安银行
5. bars 主数据里不建议存 name，名称应作为维表 join。

## 结论

`hq_cache.zip` 很有用。第一优先级是从：

```text
shs.tnf
szs.tnf
bjs.tnf
```

生成证券基础信息表：

```text
data/stock_local/meta/instruments.csv
```

这能解决当前“通达信行情文件只有代码，没有名称”的问题。
