---
title: "量化策略流派大扫描：趋势、均值回归、套利、选股，怎么选适合自己的"
date: 2026-06-25
tags: [AI量化, 量化策略, 趋势跟踪, 均值回归, 套利, 选股]
collection: 代码人生
summary: 量化不是只有"选股"一种玩法。这篇文章梳理主要的量化策略流派，比较各自的逻辑、适用环境、优劣势，帮你找到适合自己情况的方向。
---

## 量化策略不止选股

很多人刚接触量化，默认想法是"用 AI 选出会涨的股票"。这是量化的一种玩法，但不是全部。

量化策略的分类，更本质的是**盈利逻辑**：你靠什么赚钱？

---

## 一、趋势跟踪（Trend Following）

**核心逻辑**：价格有惯性，一旦形成趋势，往往会延续一段时间。

最简单的例子是双均线策略：短期均线上穿长期均线就买入，下穿就卖出。

```python
def ma_crossover_signal(close: pd.Series, fast: int = 20, slow: int = 60) -> pd.Series:
    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    signal = pd.Series(0, index=close.index)
    signal[fast_ma > slow_ma] = 1   # 多头
    signal[fast_ma < slow_ma] = -1  # 空头（需要融券）
    return signal
```

**在哪些市场有效**：

趋势跟踪在期货市场效果好（大宗商品、外汇、利率），因为这些市场经常出现持续性的宏观趋势。

A 股股票趋势跟踪的结果相对复杂。大盘指数有一定趋势性，但个股因为市值效应、情绪轮动，趋势持续时间往往不长，而且 A 股有涨跌停限制，趋势跟踪的进出场成本较高。

**优势**：
- 逻辑简单，易于理解和实现
- 在单边行情里表现很好
- 不需要预测具体的行情时间，只是跟随

**劣势**：
- 震荡市频繁假突破，手续费损耗大
- 滞后性——趋势形成了才买，顶部和底部必然错过
- A 股 T+1 限制了部分反应速度

---

## 二、均值回归（Mean Reversion）

**核心逻辑**：价格偏离均值之后，往往会回归。

直觉上很符合"低买高卖"的思维。

```python
def mean_reversion_signal(close: pd.Series, window: int = 20, n_std: float = 2.0) -> pd.Series:
    mean = close.rolling(window).mean()
    std = close.rolling(window).std()
    z_score = (close - mean) / std
    
    signal = pd.Series(0, index=close.index)
    signal[z_score < -n_std] = 1   # 超跌，买入
    signal[z_score > n_std] = -1   # 超涨，卖出（或减仓）
    return signal
```

**变体**：

- **对冲套利版**：两只高度相关的股票（同行业龙头），价差超过历史均值时买低卖高
- **板块轮动**：某板块相对大盘跌多了，均值回归买入
- **日内短线**：开盘跳空后的价格回填

**A 股的短期反转效应**：

实测数据支持 A 股存在显著的短期（1-5日）反转效应。今天跌多的股票，明天往往有反弹。IC 均值约 0.04-0.06，比大多数因子强。

**优势**：
- 震荡市里效果好，反过来跟趋势策略互补
- 有统计基础，不是玄学

**劣势**：
- 单边大跌时，均值一直没法回归，持续亏损（"接飞刀"）
- 需要严格止损

---

## 三、套利（Arbitrage）

**核心逻辑**：同一资产在不同市场/不同形态的价格不一致，买低卖高锁定无风险利润。

套利在理论上是"免费的午餐"，但实际上需要技术优势。

### ETF 套利

沪深 300 ETF 的市价和净值之间存在溢价/折价，可以套利：

```python
# ETF 折价时：买 ETF + 赎回 → 获得一篮子股票 → 卖出股票
# ETF 溢价时：买入一篮子股票 → 申购 ETF → 卖出 ETF

def etf_arbitrage_signal(etf_price: float, nav: float, threshold: float = 0.003) -> str:
    premium = etf_price / nav - 1
    if premium > threshold:
        return "sell_etf_buy_basket"   # 溢价套利
    elif premium < -threshold:
        return "buy_etf_sell_basket"   # 折价套利
    return "no_signal"
```

**现实**：大型机构已经把 ETF 套利的空间压缩得很小，个人投资者进场时往往已经没利润了。

### 可转债套利

可转债可以转换成正股。当可转债价格 < 理论转换价值时，买入可转债 + 转股 + 卖出正股，锁定套利收益。

```python
# 转换价值 = 正股价格 / 转股价 × 100
def cb_arbitrage_signal(cb_price: float, stock_price: float, convert_price: float) -> float:
    conversion_value = stock_price / convert_price * 100
    premium = cb_price / conversion_value - 1
    return premium  # 负值意味着套利机会
```

**可转债套利**是个人量化里相对可行的方向，机构参与度没有 ETF 套利那么高，偶尔会出现 1-3% 的折价。

### 跨期套利

期货市场的近月合约和远月合约之间的价差，理论上应该等于持仓成本。价差偏离时可以套利。

---

## 四、多因子选股

**核心逻辑**：股票的预期收益由多个系统性因素（因子）驱动，找到这些因子并组合起来预测未来收益。

这是机构量化基金用得最多的方法，也是 Qlib 最擅长的场景。

```python
# 典型流程
def multifactor_signal(df: pd.DataFrame, factor_weights: dict) -> pd.Series:
    """
    df: 每只股票的因子矩阵
    factor_weights: 各因子权重
    """
    composite_score = sum(df[f] * w for f, w in factor_weights.items())
    # 行业内排名中性化
    composite_score = composite_score.groupby(df['industry']).rank(pct=True)
    return composite_score
```

**A 股有效的因子**（根据实测）：
- 短期反转（1-5日）
- 换手率异动
- 分析师预期修正
- ROE（质量因子，中低频）
- 低波动（长期）

**优劣势**：

优势：学术基础扎实，有大量研究支撑；可以跟 AI/ML 结合挖掘更多因子

劣势：需要较大规模资金才能充分分散；因子有效性随时间变化，需要持续维护

---

## 五、机器学习选股

**核心逻辑**：把选股问题建模成预测问题，用 ML 模型预测未来收益率（或涨跌概率）。

本质上是多因子选股的升级版，把线性加权换成非线性模型。

```python
from sklearn.ensemble import GradientBoostingRegressor
import lightgbm as lgb

# 特征：技术指标 + 基本面因子
X_train = factor_df[feature_cols]
y_train = future_returns  # 未来 5 日收益

# LightGBM 排序模型（更适合选股场景）
model = lgb.LGBMRanker(
    n_estimators=500,
    learning_rate=0.02,
    max_depth=5,
)
model.fit(X_train, y_train, group=group_sizes)

# 预测：每只股票的相对排名分数
pred_scores = model.predict(X_test)
top_stocks = pd.Series(pred_scores, index=X_test.index).nlargest(50).index
```

**与多因子选股的区别**：
- 多因子：线性加权，可解释性强，过拟合风险低
- ML 选股：非线性，可以捕捉因子之间的交互效应，但更容易过拟合

**适合场景**：有足够历史数据（5年以上），定期重训模型（每季度或每月）

---

## 怎么选适合自己的方向

| 条件 | 建议方向 |
|------|----------|
| 刚入门，想先跑通流程 | 趋势跟踪（逻辑最简单）|
| 对 AI/ML 感兴趣 | 多因子 + LightGBM 选股 |
| 资金少，想低风险 | ETF 套利 / 可转债套利 |
| 做 A 股短线 | 均值回归（短期反转）|
| 做期货 | 趋势跟踪（期货趋势性更强）|

没有"最好的策略"，只有"适合你当前情况的策略"。

入门建议：**先把一个策略从回测做到自动化执行**，哪怕只是最简单的双均线，完整走一遍比学一百个策略思路更有价值。
