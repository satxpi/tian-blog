#!/bin/bash
# 微信公众号深度文章发布脚本（带AI生图功能）
# 支持：每天8点、周三12点、周五20点、周日15点

set -e

# 环境变量
export WECHAT_APP_ID=wx4d76a79c84e3ebbc
export WECHAT_APP_SECRET=72d4248a0d0384384884116ff2470e06

# 根据时间选择主题
HOUR=$(date +%H)
WEEKDAY=$(date +%u)  # 1=周一, 7=周日

# 日志
LOG_DIR="/tmp/wechat_deep_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date '+%Y%m%d_%H%M%S').log"
exec >> "$LOG_FILE" 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 生成图片函数
generate_image() {
    local prompt="$1"
    local output_file="$2"
    local encoded_prompt=$(echo "$prompt" | sed 's/ /%20/g; s/,/%2C/g')
    
    log "开始生成图片..."
    curl -s "https://image.pollinations.ai/prompt/${encoded_prompt}?width=1024&height=768&nologo=true&seed=$(date +%s)" \
        -o "$output_file" -L --max-time 120
    
    if [ -f "$output_file" ]; then
        local filetype=$(file -b "$output_file" | head -1)
        if echo "$filetype" | grep -qE "JPEG|PNG|image"; then
            log "✅ 图片生成成功: $output_file"
            return 0
        else
            log "❌ 图片生成失败，返回的不是图片文件"
            rm -f "$output_file"
            return 1
        fi
    else
        log "❌ 图片生成失败，文件不存在"
        return 1
    fi
}

log "=== 微信公众号深度文章发布开始 ==="
log "时间: $(date)"
log "小时: $HOUR, 星期: $WEEKDAY"

# 根据时间和星期选择主题
if [ "$WEEKDAY" = "7" ]; then
    # 周日专题
    TOPIC_TYPE="sunday"
    TOPICS=("周末的意义" "慢生活的艺术" "与自己对话的时间")
    IMAGE_PROMPTS=("a person relaxing in a cozy armchair by the window, soft sunlight, peaceful atmosphere, warm colors, slow living, minimalist, calm and serene" "hands holding a cup of tea on a wooden table, plants in background, warm afternoon light, slow life, mindfulness, cozy" "person journaling alone in a quiet room, warm lamp light, peaceful evening, self-reflection, contemplative mood")
elif [ "$WEEKDAY" = "3" ]; then
    # 周三效率专题
    TOPIC_TYPE="efficiency"
    TOPICS=("效率的陷阱" "深度工作法" "时间管理哲学")
    IMAGE_PROMPTS=("a person sitting at a desk full of papers and clocks looking exhausted, hourglass, cold coffee, city night background, blue grey tone, contemplative atmosphere" "person focused working in a clean minimal workspace, single task, deep concentration, warm desk lamp, books and laptop, productive" "abstract visualization of time flowing like sand, balanced lifestyle, harmony between work and life, artistic, thought-provoking")
elif [ "$WEEKDAY" = "5" ]; then
    # 周五生活专题
    TOPIC_TYPE="life"
    TOPICS=("生活的艺术" "工作与平衡" "周末规划")
    IMAGE_PROMPTS=("artistic still life with flowers, books, and coffee, natural light, aesthetic lifestyle, warm colors, artistic composition" "scales balancing work items and personal life symbols, work-life balance concept, professional illustration" "weekend planning concept, calendar and cozy elements, relaxed atmosphere, anticipation, warm colors")
else
    # 日常深度专题
    TOPIC_TYPE="daily"
    TOPICS=("健康饮食哲学" "智能家居思考" "效率工具反思" "生活技巧深度")
    IMAGE_PROMPTS=("healthy meal on wooden table, fresh vegetables, natural lighting, mindfulness eating, warm kitchen atmosphere, organic food" "smart home concept, modern living room with subtle technology, warm lighting, cozy and intelligent, futuristic but warm" "minimalist desk setup, clean workspace, focused work environment, productivity, calm and organized" "hands doing practical life task, close-up, warm lighting, everyday wisdom, authentic moment")
fi

# 随机选择主题
RANDOM_INDEX=$(( RANDOM % ${#TOPICS[@]} ))
SELECTED_TOPIC="${TOPICS[$RANDOM_INDEX]}"
SELECTED_PROMPT="${IMAGE_PROMPTS[$RANDOM_INDEX]}"

log "主题类型: $TOPIC_TYPE"
log "选定主题: $SELECTED_TOPIC"
log "图片Prompt: $SELECTED_PROMPT"

# 生成图片
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
IMAGE_FILE="/tmp/wechat_cover_${TIMESTAMP}.jpg"

if generate_image "$SELECTED_PROMPT" "$IMAGE_FILE"; then
    # 使用本地图片URL（需要通过wenyan或手动上传到公众号）
    COVER_URL="file://${IMAGE_FILE}"
    log "✅ 图片生成完成"
else
    # 备用：使用占位图
    COVER_URL="https://picsum.photos/800/450"
    log "⚠️ 使用备用图片"
fi

# 生成深度文章
python3 << PYTHON_EOF
import datetime
import sys

# 深度文章模板
deep_templates = {
    '健康饮食哲学': {
        'title': '健康饮食的哲学：我们吃的不仅是食物，更是生活态度',
        'content': '''## 🍽️ 餐桌上的哲学

清晨六点，厨房里飘来燕麦粥的香气。这不仅仅是一顿早餐，**而是一天开始的仪式**。

### 🌱 食物的三重意义

**第一重：生理需求**
- 提供能量，维持生命
- 满足味蕾，带来愉悦

**第二重：心理慰藉**  
- 妈妈做的菜，是童年的记忆
- 深夜的一碗面，是孤独时的陪伴

**第三重：生活哲学**
- 选择吃什么，就是选择成为什么样的人
- 烹饪的过程，是与食材对话的过程

### 🧘 慢食运动的启示

在意大利兴起的"慢食运动"提出：**吃得慢一点，生活才能快活一点**。

### 🌟 实践建议

**从明天开始，尝试：**
1. **每周一次"无手机晚餐"**：专注食物，专注对话
2. **学习一道传统菜肴**：连接文化，连接记忆

### 💫 结语

健康饮食，不是严格的卡路里计算，**而是一种生活态度的选择**。

当我们用心对待每一餐，我们不仅在滋养身体，**更在滋养灵魂**。

---
【本文由AI生成，经人工审核修改】
生成时间：{date}'''
    },
    
    '智能家居思考': {
        'title': '智能家居：当科技遇见生活，我们失去了什么？',
        'content': '''## 🌌 深夜的思考

凌晨两点，我对着手机轻声说："小爱同学，关灯。" 房间瞬间陷入黑暗。这一刻，我突然意识到：**我们正在把生活的控制权，一点一点交给机器。**

### 🤖 便利的代价

**1. 隐私的边界正在模糊**
每一次与智能设备的交互，都在为算法提供数据。

**2. 技能的退化**
当智能灯泡不响应时，我们的第一反应是："重启一下APP试试。"

**3. 情感的疏离**
智能家居让生活更"高效"，却也让我们与家人的直接互动变少。

### 🌟 寻找平衡

**科技应该服务于人，而不是控制人**

真正的智能家居，应该是**隐形的服务者**。

**几个思考方向：**
1. **选择性智能化**：不是所有东西都需要智能
2. **数据自主权**：保持对个人信息的控制
3. **技能保留**：保持基本的动手能力

### 💫 结语

智能家居就像一盏小夜灯：它提供光明，但不取代月光。

在这个科技飞速发展的时代，**保持清醒的思考，比拥有最先进的设备更重要。**

---
【本文由AI生成，经人工审核修改】
生成时间：{date}'''
    },
    
    '效率工具反思': {
        'title': '效率的陷阱：当我们追求高效时，失去了什么？',
        'content': '''## ⏰ 时间的悖论

我安装了第10个效率工具，设置了第20个自动化流程，节省了无数时间。
但为什么，**我反而感觉更忙了？**

### 🔄 效率的恶性循环

**1. 工具越多，负担越重**
每个工具都需要学习、配置、维护。

**2. 自动化越多，控制越少**
当一切都自动化后，**我们是否变成了自己系统的奴隶？**

**3. 数据越多，焦虑越深**
每天看到自己的时间统计、任务完成率、效率评分。

### 🌈 真正的效率

**效率不是做更多的事，而是做对的事**

**重新定义效率：**
1. **深度工作**：专注2小时，胜过碎片化8小时
2. **有意义的休息**：真正的放松，不是刷手机
3. **选择性放弃**：不做某些事，比做更多事更重要

### 🧭 实践指南

**从工具依赖到自我掌控：**
1. **每周工具清理**：删除不再使用的效率工具
2. **设置"无工具日"**：体验原始的工作方式
3. **关注成果，而非过程**：完成比完美更重要

### 🌟 结语

最高效的工具，不是最复杂的软件，**而是清醒的头脑和明确的目标。**

让我们在追求效率的同时，**不忘生活的本质：创造价值，享受过程，保持人性。**

---
【本文由AI生成，经人工审核修改】
生成时间：{date}'''
    },
    
    '周末的意义': {
        'title': '周末的意义：在忙碌的世界中，如何找回属于自己的时间？',
        'content': '''## 🌅 周日下午的困惑

周日下午三点，阳光透过窗户洒在书桌上。
我打开电脑，准备"高效利用"这个周末。
但内心有个声音在问：**这真的是我想要的周末吗？**

### 🌿 重新定义周末

**周末不是"要做"什么，而是"不做"什么**

**尝试这些"不做"清单：**
1. **不查看工作消息**（紧急情况除外）
2. **不刷社交媒体**（至少半天）
3. **不做"有用"的事**（允许自己"浪费"时间）

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

---
【本文由AI生成，经人工审核修改】
生成时间：{date} 周日'''
    }
}

topic_key = '$SELECTED_TOPIC'
image_file = '$IMAGE_FILE'

template = deep_templates.get(topic_key, deep_templates['效率工具反思'])

current_date = datetime.datetime.now().strftime('%Y年%m月%d日')
title = template['title']
content = template['content'].format(date=current_date)

# 保存文章
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
file_path = f"/tmp/wechat_deep_{timestamp}.md"

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(f"""---
title: "{title}"
author: "生活思考者"
cover: "{image_file}"
---

{content}
""")

print(f"FILE:{file_path}")
print(f"TITLE:{title}")
print(f"IMAGE:{image_file}")
PYTHON_EOF

# 获取生成的文件路径
ARTICLE_FILE=$(python3 -c "
import os
for f in os.listdir('/tmp'):
    if f.startswith('wechat_deep_') and f.endswith('.md'):
        print(f'/tmp/{f}')
        break
" | tail -1)

if [ -f "$ARTICLE_FILE" ] && [ -s "$ARTICLE_FILE" ]; then
    log "✅ 深度文章生成成功"
    log "文件: $ARTICLE_FILE"
    log "标题: $(grep -m1 'title:' "$ARTICLE_FILE" | cut -d'"' -f2)"
    log "图片: $(grep 'cover:' "$ARTICLE_FILE" | cut -d'"' -f2)"
    
    # 发布到公众号草稿箱
    log "开始发布到公众号草稿箱..."
    
    # 检查wenyan是否可用
    if command -v wenyan &> /dev/null; then
        wenyan publish --file "$ARTICLE_FILE" 2>&1 | tee -a "$LOG_FILE"
        PUBLISH_RESULT=${PIPESTATUS[0]}
        
        if [ $PUBLISH_RESULT -eq 0 ]; then
            log "✅ 文章成功提交到草稿箱！"
        else
            log "❌ wenyan发布失败，错误码: $PUBLISH_RESULT"
            log "请手动检查文章文件: $ARTICLE_FILE"
        fi
    else
        log "⚠️ wenyan-cli未安装，文章已保存到: $ARTICLE_FILE"
        log "请手动使用wenyan publish --file $ARTICLE_FILE 发布"
    fi
else
    log "❌ 文章生成失败"
    exit 1
fi

log "=== 微信公众号深度文章发布结束 ==="
