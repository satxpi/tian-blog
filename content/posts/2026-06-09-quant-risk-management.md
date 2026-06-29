---
title: "量化策略的风控：最大回撤、夏普比率之外，你还需要知道这些"
date: 2026-06-09
tags: [AI量化, 风险管理, 回撤, 夏普比率, 仓位管理]
collection: 代码人生
summary: 量化策略回测出来漂亮，实盘一打开账户就开始亏。这篇文章聊聊风险管理的实质：不只是最大回撤和夏普比率，而是你的策略在不同市场环境下会怎么死。
---

## 为什么风控比选股更重要

很多人刚入门量化，把 90% 的时间花在找 Alpha——挖因子、调模型参数。但我越做越觉得，**风控才是量化策略的生死线**。

一个平庸的选股模型 + 好的风控 = 可以长期活着

一个优秀的选股模型 + 差的风控 = 某天一个极端行情直接爆仓

2022 年 A 股剧烈波动，很多看起来很稳的量化策略单月最大回撤超过 30%。不是因为选股模型坏掉了，是因为风控没有做好极端情形的保护。

---

## 常见的风险指标

### 最大回撤（Max Drawdown）

```python
def max_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = cumulative / rolling_max - 1
    return drawdown.min()  # 负数，越接近 0 越好
```

最大回撤看的是账户从"历史最高点"到"最低点"的跌幅。一般认为：
- < 10%：保守策略，可接受
- 10%-20%：中等风险
- > 30%：高风险，心理压力大，容易在底部割肉

### 夏普比率（Sharpe Ratio）

```python
def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.025) -> float:
    excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
    return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
```

夏普比率衡量的是"每承担一单位风险获得的超额收益"。
- < 0.5：风险调整后回报差
- 0.5-1.0：可接受
- > 1.5：优秀，但要小心过拟合

**夏普比率的局限**：假设收益正态分布，但实际上市场收益是"厚尾"的——极端事件发生频率比正态分布预测的高得多。

### Calmar 比率

```python
def calmar_ratio(returns: pd.Series) -> float:
    annual_return = (1 + returns).prod() ** (252 / len(returns)) - 1
    mdd = abs(max_drawdown(returns))
    return annual_return / mdd if mdd != 0 else np.inf
```

年化收益 / 最大回撤。比夏普比率更直观——"每回撤 1 元，能赚多少"。

### VaR 和 CVaR

```python
import numpy as np

def var_cvar(returns: pd.Series, confidence: float = 0.95):
    # VaR：95%置信度下，单日最大损失不超过
    var = np.percentile(returns, (1 - confidence) * 100)
    # CVaR：超过VaR那部分的平均损失（尾部期望损失）
    cvar = returns[returns <= var].mean()
    return var, cvar
```

CVaR（条件风险价值）比 VaR 更准确，因为它考虑了极端情况下的平均损失，而不是只给出一个截断点。

---

## 仓位管理

### Kelly 公式

凯利公式给出了在已知胜率和赔率时，最优的仓位比例：

```
Kelly % = (胜率 × 赔率 - 败率) / 赔率

其中：赔率 = 平均盈利 / 平均亏损
```

```python
def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    win_rate: 胜率（0到1）
    avg_win: 平均盈利（正数）
    avg_loss: 平均亏损（正数）
    """
    b = avg_win / avg_loss  # 赔率
    kelly = (win_rate * b - (1 - win_rate)) / b
    return max(0, kelly)

# 示例：胜率55%，平均盈利1.5%，平均亏损1%
kelly = kelly_fraction(0.55, 1.5, 1.0)
print(f"Kelly fraction: {kelly:.2%}")  # → Kelly fraction: 27.50%

# 实际使用半Kelly或1/4Kelly，避免过度激进
safe_fraction = kelly * 0.5
```

全凯利仓位理论上最优，但波动极大，心理难以承受。实践中用 1/4 到 1/2 凯利。

### 波动率目标（Vol Targeting）

不用固定仓位，而是根据市场波动率动态调整：

```python
def volatility_target_position(signal: float, vol: float, target_vol: float = 0.15) -> float:
    """
    signal: 选股信号（-1 到 1）
    vol: 当前市场波动率（年化）
    target_vol: 目标波动率，默认 15%
    """
    scaling = target_vol / (vol + 1e-8)
    return signal * min(scaling, 2.0)  # 最大 2 倍杠杆
```

这样在市场平静时加仓，在市场剧烈波动时减仓，实现"逆波动率配置"。

---

## 集中度风险

### 行业集中度

```python
def sector_concentration(portfolio: dict, sector_map: dict) -> dict:
    """计算各行业的持仓权重"""
    sector_weights = {}
    total = sum(portfolio.values())
    for stock, weight in portfolio.items():
        sector = sector_map.get(stock, "unknown")
        sector_weights[sector] = sector_weights.get(sector, 0) + weight / total
    return sector_weights

# 检查单一行业是否超过阈值
def check_sector_limit(sector_weights: dict, limit: float = 0.3) -> list:
    return [s for s, w in sector_weights.items() if w > limit]
```

单一行业持仓超过 30% 是常见的集中度警告线。2022 年新能源行情结束，很多量化组合因为新能源持仓过重损失惨重。

### 因子暴露

一个看起来多样化的股票组合，可能在底层因子上高度集中。比如持了 50 只股票，但全部是小市值科技股，实际上暴露的是同一个风险因子。

```python
from sklearn.decomposition import PCA

# 通过 PCA 分析组合的主要风险来源
factor_matrix = pd.DataFrame(factor_data)  # 每只股票的因子暴露
pca = PCA(n_components=5)
pca.fit(factor_matrix)
print("主要风险因子解释方差：", pca.explained_variance_ratio_)
```

---

## 压力测试

回测只能告诉你策略在历史上的表现，不能告诉你在极端情形下会怎样。压力测试补充这个空白：

```python
def stress_test(strategy_returns: pd.Series, market_returns: pd.Series):
    """模拟不同市场条件下策略的表现"""
    # 定义极端情景
    scenarios = {
        "2015股灾": ("2015-06-01", "2015-08-31"),
        "2018贸易战": ("2018-01-01", "2018-12-31"),
        "2020疫情": ("2020-01-15", "2020-04-01"),
        "2022大跌": ("2022-01-01", "2022-10-31"),
    }
    
    results = {}
    for name, (start, end) in scenarios.items():
        period_returns = strategy_returns[start:end]
        results[name] = {
            "策略收益": period_returns.sum(),
            "最大回撤": max_drawdown(period_returns),
            "夏普": sharpe_ratio(period_returns),
        }
    return pd.DataFrame(results).T
```

如果你的策略在每个历史极端行情里都能活下来，那实盘遇到类似情形的概率也更高。

---

## 一个实用的风控规则集

整理了一些实践中用的比较多的规则：

**仓位控制**
- 单只股票最大仓位 ≤ 5%（50 只股票最大分散化）
- 单一行业最大仓位 ≤ 30%
- 最大净仓位 ≤ 95%（保留 5% 现金缓冲）

**止损规则**
- 单日组合亏损 > 3%：暂停交易，检查是否有信号异常
- 当月累计亏损 > 8%：减仓至 50%
- 季度亏损 > 15%：全面暂停，重新审视模型

**换手率控制**
- 单日换手率 ≤ 20%（高换手带来高交易成本）
- 月度换手率 ≤ 200%（超过意味着策略在过度优化）

**模型监控**
- 信号 IC 连续 5 个交易日低于 0：检查模型是否失效
- 预期收益与实际收益差异 > 2 个标准差：触发预警

---

## 结语

量化风控没有终点。市场会变，有效的策略会失效，新的极端情形会出现。

风控不是为了让收益最大，是为了让你**在市场给你最坏情况时，还能活着等到下一次机会**。这比任何 Alpha 因子都重要。
