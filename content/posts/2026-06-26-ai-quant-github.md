---
title: "GitHub最火AI量化项目大盘点：从回测到智能决策，A股量化看这篇就够了"
date: 2026-06-26
tags: AI量化, 开源项目, GitHub, 回测, 智能决策, A股
collection: 代码人生
summary: 整理GitHub上星标过万、社区活跃的AI量化与智能决策开源项目，覆盖微软Qlib、LLM驱动分析、强化学习、回测框架等，附带实用选型建议。
---

## 前言

最近花了些时间把 GitHub 上跟 AI 量化相关的项目翻了一遍。从微软的 Qlib 到今年突然爆火的 ai-hedge-fund，从老牌回测框架 backtrader 到能用大模型直接分析 A 股的热门新秀——好东西不少，坑也有。

这篇文章把星标高、还在活跃维护的项目整理出来，按用途分了类。不管你是刚入门想搭个回测环境，还是已经在跑实盘想上 AI 模型，应该都能找到参考。

> 免责声明：以下数据来自 GitHub 公开页面及社区讨论，仅供参考。量化交易有风险，本文不构成任何投资建议。

---

## 一、AI 量化平台（全流程覆盖）

这类项目不是单一工具，而是从数据、模型、回测到执行的完整流水线。适合想系统化做 AI 量化的人。

### 1. Qlib — 微软出品，42K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [microsoft/qlib](https://github.com/microsoft/qlib) |
| **语言** | Python |
| **Star** | ≈42,000 |
| **核心亮点** | 数据处理→特征工程→模型训练→回测→执行，全流程 ML Pipeline |

Qlib 是目前量化开源圈 Star 数最高的项目，微软研究院维护，代码质量有保障。它的设计思路是把量化研究流水线化：你定义好数据、模型、策略，剩下的训练和回测它帮你跑。

2025 年推出的 **RD-Agent** 更进一步——基于 LLM 的多智能体框架，能自动做因子挖掘和策略迭代，相当于让 AI 替你跑量化研究的循环。

**适用场景**：有 ML 背景、想做因子研究和模型训练的量化分析师。对 A 股支持需要自行接入数据源。

---

### 2. Qbot — 全本地化 AI 量化机器人，16K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [UFund-Me/Qbot](https://github.com/UFund-Me/Qbot) |
| **语言** | Python |
| **Star** | ≈16,700 |
| **核心亮点** | 完全本地部署，集成 LSTM/Transformer/LightGBM，支持强化学习 |

Qbot 最大的特点是全本地跑，不依赖任何云服务。内置了深度学习模型（LSTM、Transformer、LightGBM），也接入了 FinGPT 做智能分析，还有一个"模型动物园"——把多篇学术论文里的模型实现直接拿来用。

支持股票、期货、加密货币，端到端闭环。

**适用场景**：想把 AI 模型直接用在交易上的人。本地部署，数据不外泄。

---

### 3. Abu（阿布量化）— 中国市场原生支持，16K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [bbfamily/abu](https://github.com/bbfamily/abu) |
| **语言** | Python |
| **Star** | ≈16,600 |
| **核心亮点** | 专为中国市场设计，A股/港股/期货/期权全支持 |

阿布量化是国内老牌量化系统了，自带机器学习模块和策略优化功能。优势在于对 A 股市场的原生支持——不像一些国外框架需要自己写数据适配。

**适用场景**：专注 A 股/港股的交易者，不想折腾数据源的。

---

## 二、LLM 驱动智能分析（大模型上场）

2025-2026 年最大的趋势：用大语言模型（LLM）直接分析股票、生成决策建议。这批项目增长极快。

### 4. daily_stock_analysis — 零成本 AI 股票分析，38K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) |
| **语言** | Python |
| **Star** | ≈38,800 |
| **核心亮点** | LLM 驱动，零成本定时运行，多渠道推送 |

2026 年 1 月才创建，短短 5 个月积累近 4 万 Star——这个增速在量化类项目里极其罕见。

它做的事情说起来简单：每天从多源（行情、新闻、情绪数据）拉取你的自选股信息，喂给大模型（DeepSeek、Qwen、Gemini 等），生成一份结构化分析报告，然后通过微信/钉钉/邮件推给你。

最狠的是**零成本部署**：Fork 后用 GitHub Actions 就能定时跑，不需要买服务器。

**适用场景**：想快速获得 AI 辅助决策意见的个人投资者，不想自己搭系统的。

---

### 5. ai-hedge-fund — AI 对冲基金团队，54K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) |
| **语言** | Python |
| **Star** | ≈54,000 |
| **核心亮点** | 15 个 AI Agent 模拟不同投资风格，多智能体协作决策 |

这个项目模拟了一支完整的对冲基金团队——15 个 AI 智能体，每个模仿一种投资风格（价值投资、成长股、量化、宏观对冲等），通过多轮讨论和投票给出最终买卖建议。

你可以把它理解成"用 AI 开了一场投资委员会会议"。支持回测，国内可用 DeepSeek 替代 OpenAI。

**适用场景**：想体验多 Agent 协作分析的人，教育和研究用途。实盘需谨慎。

---

### 6. FinGPT — 金融大模型开源方案

| 项目 | 详情 |
|------|------|
| **地址** | [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) |
| **语言** | Python |
| **核心亮点** | 开源金融 LLM，LoRA 微调，情感分析，数据自动聚合 |

FinGPT 是 AI4Finance 基金会推出的开源金融大模型方案。和 BloombergGPT 那种闭源方案不同，FinGPT 走的是"数据驱动 + LoRA 微调"路线——你可以用自己的数据低成本微调一个金融专属 LLM。

内置新闻情感分析、社交媒体情绪追踪、财报解读等功能。在 A 股场景下特别适合做舆情驱动的策略。

**适用场景**：想做金融 NLP、舆情分析、用 LLM 辅助决策的量化团队。

---

## 三、强化学习交易框架（AlphaGo 式交易）

### 7. FinRL — 金融强化学习先驱，13K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) |
| **语言** | Python |
| **Star** | ≈13,000 |
| **核心亮点** | 全球首个开源金融 RL 框架，支持多种市场环境 |

FinRL 把交易建模成强化学习问题：智能体（Agent）在市场环境（Environment）中做序列决策，目标最大化收益。支持股票、期货、外汇、加密货币等多种市场。

内置多种经典强化学习算法（DQN、PPO、A2C、SAC、TD3 等），也有 FinRL-Meta 提供元学习能力。

**适用场景**：对强化学习感兴趣的研究者，想尝试非传统交易策略的人。

---

### 8. TradeMaster — NTU 出品，专注 RL 交易研究

| 项目 | 详情 |
|------|------|
| **地址** | [TradeMaster-NTU/TradeMaster](https://github.com/TradeMaster-NTU/TradeMaster) |
| **语言** | Python |
| **核心亮点** | 新加坡南洋理工出品，学术级 RL 量化研究平台 |

相比 FinRL 偏实用，TradeMaster 更偏学术研究——提供了 15+ 种强化学习算法的统一实现和基准测试，方便横向对比不同 RL 方法在交易中的表现。

**适用场景**：做量化金融学术研究的，想对比不同 RL 算法效果的。

---

## 四、回测与交易框架（老牌基石）

AI 策略最终要落地的。市面上的回测框架很多，这里选几个还在活跃维护的。

### 9. VNPY — 国内量化第一框架，23K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [vnpy/vnpy](https://github.com/vnpy/vnpy) |
| **语言** | Python |
| **Star** | ≈23,000 |
| **核心亮点** | 事件驱动架构，模块化设计，A 股/期货/期权全覆盖 |

国内最流行的量化框架，没有之一。CTA 策略、算法交易、期权套利都有专门模块。社区活跃，文档中文，对接了国内主流券商和期货公司的接口。

虽然它本身不侧重 AI，但作为交易执行层，大量的 AI 策略最终都会跑在 VNPY 上。

**适用场景**：需要实盘交易的国内量化开发者，特别是期货和期权。

---

### 10. Backtrader — Python 回测经典

| 项目 | 详情 |
|------|------|
| **地址** | [mementum/backtrader](https://github.com/mementum/backtrader) |
| **语言** | Python |
| **核心亮点** | 事件驱动，API 直观，社区庞大，教程丰富 |

如果你刚接触量化回测，Backtrader 可能是最好的入门选择。API 设计优雅，文档和社区教程非常多。虽然原仓库更新放缓，但生态已经足够成熟。

**适用场景**：量化初学者，策略快速验证。

---

### 11. VectorBT — 向量化回测，速度碾压

| 项目 | 详情 |
|------|------|
| **地址** | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) |
| **语言** | Python |
| **核心亮点** | 向量化回测，比事件驱动快几十倍，超参数优化 |

传统回测是一笔一笔模拟的，VectorBT 是整列一起算——速度快得不是一点半点。特别适合做大量参数的网格搜索和超参数优化。

**适用场景**：策略参数调优、大规模因子回测。

---

## 五、数据与学习资源

### 12. awesome-quant — 量化资源大全，25K+ Stars

| 项目 | 详情 |
|------|------|
| **地址** | [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) |
| **核心亮点** | 量化金融库、包、资源分类汇总，按语言和主题整理 |

不是工具，但可能是最实用的一个仓库——把量化领域的好用库按语言（Python、R、Julia、C++）和用途分类整理好了。不知道有啥工具可以用？来这翻翻。

### 13. machine-learning-for-trading

| 项目 | 详情 |
|------|------|
| **地址** | [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) |
| **核心亮点** | 《Machine Learning for Algorithmic Trading》配套代码，150+ Notebook |

如果想系统学习如何把 ML 用在交易上，这是目前最好的开源教程。从 NLP 情感分析到深度强化学习，从数据清洗到回测评估，覆盖完整。

---

## 六、怎么选？一张表总结

| 你的需求 | 推荐项目 | 理由 |
|----------|----------|------|
| 想做 AI 量化全流程 | **Qlib** | 微软背书，Pipeline 最完整 |
| A 股实盘交易 | **VNPY + daily_stock_analysis** | VNPY 执行，daily 辅助决策 |
| 用 LLM 分析股票 | **daily_stock_analysis / ai-hedge-fund** | 零成本，开箱即用 |
| 试试强化学习交易 | **FinRL** | 文档好，社区大 |
| 本地跑 AI 模型 | **Qbot / Abu** | 全本地，支持 A 股 |
| 刚学回测 | **Backtrader** | 最简单，教程多 |
| 大规模因子回测 | **VectorBT** | 向量化，速度快 |
| 找工具/库 | **awesome-quant** | 分类清晰，持续更新 |

---

## 结语

AI 量化的门槛在 2026 年已经大幅降低了。几年前你可能需要自己搭数据管道、写回测引擎、调模型——现在 GitHub 上这些项目把大部分轮子都造好了。

但工具永远只是工具。真正值钱的是你对市场的理解、策略的逻辑、风险的控制。开源项目能帮你从 0 到 1，从 1 到 100 还得靠自己。

如果你是刚入门，建议顺序：**Backtrader（学回测）→ VNPY（了解实盘）→ daily_stock_analysis（体验 AI）→ Qlib（深入 ML 量化）**。

---

*本文整理于 2026 年 6 月，项目数据来自 GitHub 公开页面。Star 数为近似值，请以实际页面为准。*
