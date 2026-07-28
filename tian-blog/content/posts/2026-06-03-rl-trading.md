---
title: "强化学习做交易：FinRL框架实战，以及为什么大多数人跑不赚"
date: 2026-06-03
tags: [AI量化, 强化学习, FinRL, 深度学习, 交易策略]
collection: 代码人生
summary: 用FinRL跑了三个月的强化学习交易实验。整理了框架的用法、A股环境的搭建，以及强化学习做交易的核心难点——为什么回测看起来很好但实盘经常翻车。
---

## 强化学习做交易的思路

强化学习的核心思路很简单：把交易问题建模成一个"游戏"。

- **状态（State）**：当前的市场数据（价格、成交量、技术指标、持仓）
- **动作（Action）**：买入、卖出、持有（或者更细粒度的仓位）
- **奖励（Reward）**：这次动作带来的收益（或者夏普比率的增量）
- **环境（Environment）**：模拟市场，接受动作，返回下一个状态和奖励

智能体在环境里不断试错，通过最大化累计奖励来学习交易策略。听起来很美好——理论上它会自动找到最优策略。

---

## FinRL 框架

[FinRL](https://github.com/AI4Finance-Foundation/FinRL) 是 AI4Finance Foundation 开发的开源框架，把股票交易环境封装成 OpenAI Gym 格式，直接接 Stable-Baselines3 跑强化学习算法。

安装：

```bash
pip install finrl stable-baselines3
```

基本用法：

```python
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
import pandas as pd

# 准备数据
df = pd.read_csv("a_share_data.csv")  # 股票OHLCV数据

# 创建交易环境
env_kwargs = {
    "hmax": 100,          # 单次最大操作手数
    "initial_amount": 1000000,  # 初始资金 100万
    "buy_cost_pct": 0.001,      # 买入手续费 0.1%
    "sell_cost_pct": 0.001,     # 卖出手续费
    "reward_scaling": 1e-4,
    "state_space": 8 + len(df.tic.unique()) * 3,
    "stock_dim": len(df.tic.unique()),
    "tech_indicator_list": ["macd", "rsi_30", "cci_30", "dx_30"],
    "action_space": len(df.tic.unique()),
}

train_env = StockTradingEnv(df=train_df, **env_kwargs)

# 训练 PPO 智能体
agent = DRLAgent(env=train_env)
model_ppo = agent.get_model("ppo")
trained_ppo = agent.train_model(
    model=model_ppo,
    tb_log_name="ppo",
    total_timesteps=100000,
)

# 回测
test_env = StockTradingEnv(df=test_df, **env_kwargs)
df_account_value, df_actions = DRLAgent.DRL_prediction(
    model=trained_ppo,
    environment=test_env,
)
```

---

## A 股环境的特殊处理

FinRL 默认的环境是针对美股设计的，用在 A 股需要改几个地方：

### T+1 限制

A 股买入当天不能卖出。需要在环境里加约束：

```python
class AShareTradingEnv(StockTradingEnv):
    def _sell_stock(self, index, action):
        # 检查是否是今天买入的
        if self.buy_date[index] == self.day:
            return  # 不允许卖出
        super()._sell_stock(index, action)
```

### 涨跌停处理

涨停时买不进，跌停时卖不出。需要在动作执行前检查：

```python
def _buy_stock(self, index, action):
    # 检查是否涨停
    if self.data.close.iloc[self.day] >= self.data.close.iloc[self.day-1] * 1.099:
        return  # 涨停，无法买入
    super()._buy_stock(index, action)
```

### 奖励函数的设计

默认奖励是当日收益率变化，但这会导致智能体过于追求短期收益，频繁交易。

更好的奖励设计：

```python
def calculate_reward(self):
    portfolio_return = (self.asset_memory[-1] - self.asset_memory[-2]) / self.asset_memory[-2]
    # 添加夏普比率惩罚项
    if len(self.asset_memory) > 20:
        returns = pd.Series(self.asset_memory).pct_change().dropna()
        sharpe = returns.mean() / (returns.std() + 1e-9) * np.sqrt(252)
        return portfolio_return + 0.01 * sharpe
    return portfolio_return
```

---

## 常用算法对比

FinRL 支持多种强化学习算法，在交易场景下表现各有差异：

| 算法 | 全称 | 特点 | 适合场景 |
|------|------|------|----------|
| PPO | Proximal Policy Optimization | 稳定，易调参 | 入门首选 |
| SAC | Soft Actor-Critic | 探索性好，对连续动作友好 | 多股票多头寸管理 |
| TD3 | Twin Delayed DDPG | 比 DDPG 稳定 | 确定性策略 |
| A2C | Advantage Actor-Critic | 训练快，并行效率高 | 快速实验 |

实测结论：**SAC 和 PPO 在大多数场景下是最稳定的**。TD3 在某些特定设置下能做出很漂亮的回测，但稳定性较差。

---

## 为什么回测好但实盘烂

这是强化学习做交易最大的问题，也是很多人入坑后最沮丧的发现。

### 过拟合

强化学习模型有大量参数，在有限的历史数据上训练很容易记住"历史"而不是学到"规律"。

一个典型的过拟合信号：在训练集夏普比率 2.5，测试集掉到 0.8，实盘变成 -0.3。

缓解方法：
- 用滚动窗口训练（Walk-Forward），不要用固定训练集
- 正则化奖励函数（加入持仓集中度惩罚、换手率惩罚）
- 多个随机种子跑，取中位数表现

### 市场非平稳性

A 股 2020 年和 2024 年的市场特征完全不同。强化学习模型训练好了，市场风格一变就失效。

这个问题没有完美解决方案。一个实用做法：把训练窗口缩短（比如用最近 6 个月而不是 3 年），并定期重训模型。

### 真实交易成本

回测里的滑点和手续费往往低估了真实成本。强化学习智能体会发现"高频小仓"这个能优化回测指标的行为，但真实交易里频繁交易的成本会把收益吃掉。

强制约束：在奖励函数里加入对高换手率的惩罚。

### 部分可观测性

市场数据只是真实"市场状态"的一个不完整的投影。大量影响股价的信息（内幕消息、机构持仓变化、海外市场）在我们的状态空间里根本不存在。

强化学习在完全可观测的环境（象棋、围棋）里表现出色，但交易环境是高度部分可观测的，这是根本性的局限。

---

## 实事求是的评估

在 CSI300 成分股、2020-2024 年的测试集上，最好的强化学习策略年化收益 15% 左右，最大回撤 18%，夏普 0.9。

看起来还不错，但：

1. 这是经过大量参数调整的结果，实盘复现不一定能达到
2. 同期 CSI300 指数本身收益不高，基准低让超额收益看起来更好
3. 交易成本用的 0.1% 双边，实际可能更高

**我的结论**：强化学习是值得研究的方向，在某些特定场景（多资产配置、风控）有独特价值，但"用 RL 直接选股打败市场"这个目标，在当前技术水平下达到的难度很高。

更务实的用法是：**用强化学习做仓位管理和风控，用传统 ML 做选股信号**，两者结合。

---

## 值得参考的资源

- **FinRL 官方文档**：https://finrl.readthedocs.io
- **AI4Finance Foundation**：GitHub 上有多个相关项目
- **FinGPT + FinRL 结合**：用 LLM 提取新闻特征作为 RL 状态输入，是当前比较前沿的方向
