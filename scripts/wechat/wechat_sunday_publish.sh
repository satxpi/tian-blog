#!/bin/bash
# 周日下午3点深度文章发布脚本

set -e

# 环境变量
export WECHAT_APP_ID=wx4d76a79c84e3ebbc
export WECHAT_APP_SECRET=72d4248a0d0384384884116ff2470e06

# 日志
LOG_FILE="/tmp/wechat_sunday.log"
exec >> "$LOG_FILE" 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== 周日下午文章发布开始 ==="

# 生成深度文章
python3 -c "
import datetime
import random

# 周日专题文章
sunday_topics = [
    {
        'title': '周末的意义：在忙碌的世界中，如何找回属于自己的时间？',
        'content': '''## 🌅 周日下午的困惑

周日下午三点，阳光透过窗户洒在书桌上。
我打开电脑，准备\"高效利用\"这个周末。
但内心有个声音在问：**这真的是我想要的周末吗？**

### 🌿 重新定义周末

**周末不是\"要做\"什么，而是\"不做\"什么**

**尝试这些\"不做\"清单：**
1. **不查看工作消息**（紧急情况除外）
2. **不刷社交媒体**（至少半天）
3. **不做\"有用\"的事**（允许自己\"浪费\"时间）
4. **不安排密集行程**（留白比填满更重要）

### 🧘 实践建议

**从下个周末开始：**
- **周六上午：深度休息**
- **周六下午：创造性活动**  
- **周日上午：身体连接**
- **周日下午：心灵整理**

### 🌟 结语

周末的真正意义，**不是从工作中逃离，而是回归生活本身。**

在这个永远在线、永远忙碌的时代，
**学会休息，是最重要的生存技能。**

愿每个周末，都是你与自己对话的时间。

---
【本文由AI生成，经人工审核修改】
生成时间：{date} 周日'''
    },
    {
        'title': '慢生活的艺术：为什么我们越忙，越需要学会「浪费」时间？',
        'content': '''## 🕰️ 时间的悖论

我们拥有比祖先更多的时间节省工具，
却感觉时间比任何时候都紧张。

**效率工具没有解放我们，反而让我们更忙碌。**

### 🌊 慢生活的智慧

**真正的效率，不是做得更快，而是做得更对。**

**慢生活的三个层次：**
1. **身体慢**：放慢脚步，感受呼吸
2. **心灵慢**：减少信息输入，增加思考空间
3. **关系慢**：深度连接，而不是浅层社交

### 🌱 实践方法

**从今天开始尝试：**
1. **每天15分钟「无目的时间」**
2. **每周一次「数字排毒」**
3. **每月一天「计划外日」**

### 💫 结语

在这个追求效率的时代，
**最大的奢侈，是拥有属于自己的时间。**

让我们重新学习「浪费」时间的艺术。

---
【本文由AI生成，经人工审核修改】
生成时间：{date} 周日'''
    }
]

# 选择主题
topic = random.choice(sunday_topics)

# 获取当前日期
current_date = datetime.datetime.now().strftime('%Y年%m月%d日')

# 生成内容
title = topic['title']
content = topic['content'].format(date=current_date)

# 保存为Markdown文件
import os
file_path = f\"/tmp/sunday_article_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md\"

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(f\"\"\"---
title: \"{title}\"
author: \"生活思考者\"
cover: \"https://picsum.photos/800/450\"
---

{content}
\"\"\")

print(f\"文件已保存: {file_path}\")
print(f\"标题: {title}\")

# 返回文件路径
print(f\"FILE:{file_path}\")
"

# 获取生成的文件路径
OUTPUT=$(python3 -c "$PYTHON_SCRIPT" | grep "FILE:" | cut -d: -f2)
ARTICLE_FILE=$(echo "$OUTPUT" | tr -d ' ')

if [ -f "$ARTICLE_FILE" ]; then
    log "文章生成成功: $ARTICLE_FILE"
    
    # 使用wenyan-cli发布
    log "开始发布到公众号草稿箱..."
    wenyan publish --file "$ARTICLE_FILE"
    
    if [ $? -eq 0 ]; then
        log "✅ 周日下午文章发布成功！"
    else
        log "❌ 发布失败，请检查wenyan-cli配置"
    fi
else
    log "❌ 文章生成失败"
fi

log "=== 周日下午文章发布结束 ==="
