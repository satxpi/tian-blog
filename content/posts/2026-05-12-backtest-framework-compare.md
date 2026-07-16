---
title: "A股回测框架横评：Backtrader、VeighNa、Qlib、vnpy哪个适合你"
date: 2026-05-12
tags: [AI量化, 回测, Backtrader, VeighNa, 框架对比, A股]
collection: 代码人生
summary: 用了半年，认真对比了四个主流量化回测框架的真实差距。从上手难度、数据接入、策略表达到实盘接入，给出具体的选型建议。
---

## 为什么要比这四个

量化圈常见的框架多得数不过来，但真正在国内 A 股场景下被广泛使用的，来来去去就这几个：

- **Backtrader**：老牌 Python 回测框架，Stack Overflow 上能搜到答案
- **VeighNa（vnpy）**：国内最大的开源量化社区，文档中文，社区活跃
- **Qlib**：微软出品，AI/因子挖掘方向最强
- **nautilus_trader**：新兴高性能框架，Rust 核心，越来越多人迁移

用了大半年，把这几个的真实体验写下来。

---

## 一句话定位

| 框架 | 一句话 | 适合谁 |
|------|--------|--------|
| Backtrader | 最好学的回测框架 | 刚入门，想快速验证策略逻辑 |
| VeighNa | 国内最完整的交易系统 | 想做实盘、接真实券商接口 |
| Qlib | AI因子挖掘的最佳工具 | 机器学习量化研究 |
| nautilus_trader | 高性能、专业级 | 对延迟敏感、需要高频/多品种 |

---

## Backtrader

### 优势

**上手快**。一个最简单的均线策略，50 行代码就能跑起来：

```python
import backtrader as bt

class SMAStrategy(bt.Strategy):
    params = (('period', 20),)
    
    def __init__(self):
        self.sma = bt.indicators.SMA(period=self.p.period)
    
    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()
        elif self.data.close[0] < self.sma[0]:
            self.sell()

cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstrategy(SMAStrategy)
result = cerebro.run()
cerebro.plot()  # 直接出图
```

**文档和社区资料丰富**。Stack Overflow、Reddit、知乎都能搜到答案，遇到问题不容易卡住。

**可视化好**。内置的 `cerebro.plot()` 直接画出资金曲线、持仓、信号标注，调试策略很方便。

### 劣势

**速度慢**。纯 Python 实现，数据量大（几千只股票、分钟级）跑起来明显感受到吃力。

**不支持实盘**。Backtrader 是纯回测框架，本身没有实盘接口，要接 CTP 或者券商 API 得自己写或者用第三方扩展。

**多品种不友好**。多资产组合、跨品种对冲写起来比较别扭。

**结论**：学习用，验证策略思路用，不适合做生产级系统。

---

## VeighNa（vnpy）

### 优势

**接口最全**。国内主流券商（华泰、东方财富、中信等）、期货 CTP、数字货币交易所，接口数量没有竞品能比。想做实盘，vnpy 是门槛最低的选择。

**GUI 界面**。带可视化操作界面，不用写代码就能看持仓、发委托、看日志，适合非程序员背景的交易者。

**中文社区**。官方文档中文，论坛活跃，很多问题发帖当天能得到回复。

### 劣势

**回测能力偏弱**。vnpy 的定位是交易系统，不是量化研究平台。做回测在参数设置、滑点处理、成本精度上比专门的回测框架差一截。

**AI/机器学习支持弱**。vnpy 的策略写法是事件驱动（`on_bar`/`on_tick`），跟 ML 模型接入有一定的框架摩擦。

**代码体积大**。整个框架依赖多、安装复杂，在服务器上部署比较折腾。

**结论**：想做国内实盘的首选，但研究阶段配合 Qlib 或 Backtrader 用效果更好。

---

## Qlib（微软）

### 优势

**AI 量化最强**。因子表达式语言 + 内置 Alpha158 因子库 + LightGBM/Transformer/LSTM 模型，整条 ML 量化管线最完整。

**实验管理好**。基于 MLflow，训练了多少个模型、哪个参数效果最好，全程有记录可以对比回溯。

**A 股数据内置**。官方有免费的 A 股日线数据工具，不用自己搭数据管线。

### 劣势

**不支持实盘**。Qlib 专注研究，没有实盘接口，研究完了要接实盘还是得靠 vnpy。

**文档不完整**。核心功能文档覆盖有限，很多高级用法需要翻源码。

**学习曲线陡**。跟 Backtrader 比，概念更多，初次使用要花不少时间理解 Handler/Dataset/Workflow 这套体系。

**结论**：做机器学习量化研究的首选，研究完接实盘配合 vnpy。

---

## nautilus_trader

### 优势

**性能碾压**。Rust 核心 + Python 接口，回测速度比 Backtrader 快 10-50 倍。处理 tick 级数据没有压力。

**架构现代**。事件驱动 + Actor 模型，回测和实盘共用同一套代码逻辑，切换无缝。

**多市场支持好**。外汇、期货、股票、加密货币，一套框架全覆盖。

### 劣势

**国内接口少**。开箱支持的是 Interactive Brokers、Binance 等国际接口，A 股券商接口需要自己开发适配器。

**社区小**。GitHub Star 不到 4000，中文资料极少，踩坑了基本靠自己看源码。

**API 设计复杂**。功能强大的代价是概念多、配置复杂，入门成本比 Backtrader 高很多。

**结论**：有性能需求、做非 A 股品种（期货/外汇）的场景很适合；A 股日线策略用不上这个性能优势。

---

## 我的实际工作流

目前用的组合是：

```
Qlib（研究）→ Backtrader（验证策略逻辑）→ VeighNa（实盘执行）
```

1. 在 Qlib 里挖因子、训练 ML 模型，得到选股信号
2. 用 Backtrader 把信号转成具体策略，做细化的回测（交易成本、仓位管理）
3. 信号满意了，接入 VeighNa 做实盘，用它的券商接口自动下单

三个框架各干各的事，没有一个框架能把三件事都做好。

---

## 选型总结

**刚入门，只想学怎么回测**：Backtrader，上手最快，资料最多。

**做 AI 量化研究，挖因子、跑 ML 模型**：Qlib，微软出品工程化最好。

**想接实盘，券商自动下单**：VeighNa，国内接口最全，中文社区靠谱。

**做期货/外汇高频，对性能要求高**：nautilus_trader，性能吊打其他几个，但 A 股支持要自己建。

别想着找一个框架解决所有问题，组合用才是正确姿势。
