---
title: Agent框架三足鼎立：LangGraph、CrewAI、AutoGen怎么选
date: 2025-06-15
tags: [AI, Agent, 框架, 开发]
collection: 代码人生
sequence: 54
---

六月份我决定认真研究 Agent 框架。

起因是我们团队想搞一个"自动代码审查 + 文档生成"的流水线——以前都是人做，现在想试试让 AI Agent 接管。

市面上三个主流框架，我都跑了 Demo，说说体会。

## 先搞清楚一个概念

**Agent ≠ 大模型。**

大模型只会回答你问的问题。Agent 会自己决定"先干什么、后干什么、用什么工具、遇到问题了换什么方案"。

框架的作用就是帮你把大模型变成 Agent——给它安上手脚（工具调用）和大脑（规划+反思）。

## LangGraph（LangChain出品）

**哲学：** Agent 是一个**状态图**。每个节点是一步操作（调用模型、使用工具、检查结果），边是条件跳转。

**写代码的感觉：** 像在画流程图。

```python
graph = StateGraph(AgentState)
graph.add_node("think", think_node)
graph.add_node("act", act_node)
graph.add_node("observe", observe_node)
graph.add_conditional_edges("think", decide_next, {
    "act": "act",
    "done": END
})
```

**优点：** 灵活、精确、状态可追踪。适合复杂的多步骤 Agent。

**缺点：** 代码量大，上手陡。一个简单的 Agent 也要写上百行。

**类比：** 像 React——你想怎么控制就怎么控制，但每件事都得自己来。

## CrewAI

**哲学：** Agent 是一个**团队**。你定义不同角色（研究员、写手、审稿人），他们会自动协作。

```python
researcher = Agent(role="研究员", goal="收集资料")
writer = Agent(role="写手", goal="写出初稿")
reviewer = Agent(role="审稿人", goal="质量把关")

crew = Crew(agents=[researcher, writer, reviewer], tasks=[...])
result = crew.kickoff()
```

**优点：** 上手极快，十分钟就能跑起来。概念直观——谁都能理解"一个团队在干活"。

**缺点：** 黑盒。Agent之间的交互你控制不了，有时候跑偏了只能重来。

**类比：** 像招了个项目经理——他管团队怎么干活，你只管验收结果。

## AutoGen（微软出品）

**哲学：** Agent 之间**对话**。两个 Agent 互相聊，像同事讨论问题那样找到答案。

**优点：** 多 Agent 协作场景最强，auto-feedback 天然内置。微软背后维护，更新勤快。

**缺点：** 文档差、报错信息跟天书一样。概念多（ConversableAgent、GroupChat、ToolAgent……），学起来头痛。

**类比：** 像 Slack 群聊——大家七嘴八舌，总能聊出个结果。

## 我选了哪个

做了个"自动代码审查"的 Demo——输入一个 PR，输出代码审查意见。

| 框架 | 完成度 | 代码量 | 上手时间 | 稳定性 |
|------|--------|--------|---------|--------|
| LangGraph | 85% | ~400行 | 3天 | 稳 |
| CrewAI | 60% | ~120行 | 半天 | 一般 |
| AutoGen | 70% | ~250行 | 2天 | 一般 |

最后选了 **LangGraph**。虽然写得多，但可控性对我这种强迫症来说太重要了。

团队试水阶段其实用 CrewAI 更合适——快点跑出结果，验证想法。

---

*写于通宵跑 Demo 后的早晨。Agent 框架的选择跟选编程语言一样，它决定了你未来三个月怎么工作。*
