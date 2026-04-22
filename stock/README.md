# 股票日记 (Stock Diary)

> 个人 A 股投资日记工具，支持早报、盘后总结、周报自动采集，带潜力股筛选功能。

---

## 快速启动

```powershell
# 以管理员身份打开 PowerShell（80端口需要管理员权限）
cd C:\Users\abc\WorkBuddy\Claw\stock-diary
python server.py
```

访问地址：`http://127.0.0.1` 或局域网 `http://内网IP`

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python `http.server` + SQLite（无外部依赖）|
| 前端 | 原生 HTML5 + CSS3 + JavaScript（无框架）|
| 数据 | 腾讯财经行情 + 东方财富 API（实时）|

---

## 文件结构

```
stock-diary/
├── server.py        后端服务 + REST API + 自动采集逻辑
├── index.html       前端页面入口
├── app.js           前端交互逻辑
├── style.css        暗色主题样式
├── stock_diary.db   SQLite 数据库（自动创建）
└── README.md        项目文档（本文件）
```

---

## 功能模块

### 日报

| 功能 | 说明 |
|------|------|
| 早盘报道 | 外围市场（美股/港股/黄金/原油）、财经大事、关注方向、操作建议、今日计划 |
| 盘后总结 | 各大指数数据、市场分析（趋势/资金/情绪）、板块涨跌前三、个股回顾、次日计划 |
| 自动刷新 | 点击刷新按钮 → 先查 DB → 无则网络抓取 → 存 DB → 展示 |
| 定时采集 | 工作日 8:30 自动采集早报，15:30 自动采集盘后 |

### 周报

| 功能 | 说明 |
|------|------|
| 本周指数 | 四大指数（上证/深证/创业板/北证）收盘数据 |
| 本周市场 | 趋势判断、北向资金、主力净流入、周成交量 |
| 板块表现 | 本周领涨前三 + 领跌前三（自动从东方财富抓取） |
| 下周潜力股 | **自动筛选5只**（见选股策略） |
| 下周计划 | 目标方向、买入计划、减仓计划、风险提示 |
| 定时采集 | 每周五 16:00 自动触发周总结采集 |

### 关注板块

| 功能 | 说明 |
|------|------|
| 本周推荐 | 展示本周推荐股票，带实时报价（开/高/低/涨跌幅）|
| 持仓管理 | CRUD 操作，刷新实时报价，统计总盈亏 |

---

## 选股策略（下周潜力股）

自动从东方财富 A 股全市场按主力净流入排序，过滤条件如下：

| 条件 | 说明 |
|------|------|
| 价格 ≤ 20 元 | 低价股，弹性空间大 |
| 价格 ≥ 2 元 | 排除垃圾低价股 |
| 主力净流入 > 0 | 资金在持续流入，非主力出逃 |
| 今日涨幅 −3% ~ +7% | 排除暴涨追高和跌停个股 |
| 换手率 > 1% | 保证有足够市场活跃度 |
| 流通市值 ≥ 10 亿 | 排除超小盘、ST 股票 |

每只股票自动输出**四维分析**：
- 🏛️ **政策面**：行业政策支持方向
- 📈 **技术面**：现价、涨幅、换手率
- 😊 **情绪面**：市场参与情绪判断
- 💰 **资金面**：主力净流入金额

> ⚠️ **免责声明**：以上为系统基于技术指标自动筛选，仅供参考，不构成投资建议。

---

## REST API

### 日报

```
GET  /api/daily?date=YYYY-MM-DD                查询某日日报
POST /api/daily                                保存日报
     body: {date, type, title, content, sentiment, time, structured_data}
GET  /api/daily/list?limit=10                  日报历史列表
```

### 周报

```
GET  /api/weekly?week=YYYY-MM-DD               查询周报（周一日期）
POST /api/weekly/summary                        保存周总结
POST /api/weekly/recommend                      保存推荐股票
GET  /api/weekly/list?limit=8                  周报历史列表
```

### 自动采集（查DB → 无则网络抓取 → 存DB → 返回）

```
GET  /api/auto/morning?date=YYYY-MM-DD         自动获取早报
GET  /api/auto/afternoon?date=YYYY-MM-DD       自动获取盘后总结
GET  /api/auto/weekly?week=YYYY-MM-DD          自动获取周总结 + 潜力股筛选
GET  /api/auto/status                           定时采集状态
```

### 持仓

```
GET    /api/holdings                            获取所有持仓
POST   /api/holdings                            添加持仓
PUT    /api/holdings/:id                        更新持仓
DELETE /api/holdings/:id                        删除持仓
```

### 行情代理（解决浏览器跨域）

```
GET  /api/quote/index                           沪深三大指数
GET  /api/quote/stock?codes=sh600519            个股实时报价（腾讯行情）
GET  /api/quote/sector                          板块资金流向（东方财富）
GET  /api/quote/news                            市场快讯（东方财富）
GET  /api/search/stock?q=关键词                  股票搜索自动补全
```

---

## 数据库结构

```sql
-- 日报表（早报 morning / 盘后 afternoon）
daily_reports (id, date, type, title, content, sentiment, time, structured_data, updated_at)

-- 周报总结表
weekly_summary (id, week, title, content, sentiment, time, structured_data, updated_at)

-- 周报推荐股票表
weekly_recommend (id, week, rank, code, name, market, reason)

-- 持仓表
holdings (id, code, name, market, cost, shares, current_price, note, created_at, updated_at)
```

`structured_data` 字段为 JSON，存储各板块结构化内容：

**盘后总结 structured_data 结构：**
```json
{
  "section1_indices":  [{ "name", "close", "change", "change_pct", "vol" }],
  "section2_market":   { "trend", "trend_detail", "fund_north", "fund_main", "volume", "advance", "decline" },
  "section3_sectors":  { "top_sectors": [...], "bottom_sectors": [...] },
  "section4_stocks":   [{ "code", "name", "minute_analysis", "kline_analysis", "news_analysis" }],
  "section5_plan":     { "target_sectors", "buy_plan", "sell_plan", "risk_warning" }
}
```

**周报 structured_data 结构：**
```json
{
  "section1_indices":   [...],
  "section2_market":    { "trend", "fund_north", "fund_main", "volume", ... },
  "section3_sectors":   { "top_sectors": [...], "bottom_sectors": [...] },
  "section4_stocks":    [...],
  "section5_plan":      { "target_sectors", "buy_plan", ... },
  "section6_recommend": [{ "code", "name", "market", "price", "chg", "inflow", "reason" }]
}
```

---

## 数据来源

| 数据 | 来源 |
|------|------|
| A 股指数 / 个股实时报价 | 腾讯行情 `qt.gtimg.cn` |
| 板块资金流向 | 东方财富 `push2.eastmoney.com` |
| 市场快讯 | 东方财富 `np-anotice-stock.eastmoney.com` |
| 股票搜索 | 东方财富 `searchapi.eastmoney.com` |
| 北向资金 | 东方财富 `push2.eastmoney.com/api/qt/kamt.rtmin` |

---

## 颜色约定

遵循中国 A 股市场惯例：

- 🔴 **红色** = 上涨（涨）
- 🟢 **绿色** = 下跌（跌）

---

## 注意事项

1. **管理员权限**：80 端口绑定需要管理员权限，启动前右键 PowerShell「以管理员身份运行」
2. **局域网访问**：服务监听 `0.0.0.0:80`，局域网其他设备可直接通过内网 IP 访问
3. **数据防覆盖**：自动采集不会覆盖已手动编辑的日报/周报内容（`CASE WHEN` 保护）
4. **潜力股免责**：自动选股基于资金流数据，不保证准确性，请自行判断
