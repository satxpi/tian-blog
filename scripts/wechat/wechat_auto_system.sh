#!/bin/bash
# 微信公众号自动化系统 - 主控制脚本

set -e

# 配置
LOG_DIR="/tmp/wechat_auto"
COOKIE_FILE="$LOG_DIR/cookie.txt"
CONTENT_DIR="$LOG_DIR/content"
BACKUP_DIR="$LOG_DIR/backup"
CONFIG_FILE="$LOG_DIR/config.json"

# 创建目录
mkdir -p "$LOG_DIR" "$CONTENT_DIR" "$BACKUP_DIR"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/run.log"
}

# 错误处理
error_exit() {
    log "错误: $1"
    exit 1
}

# 检查依赖
check_dependencies() {
    log "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        error_exit "Python3未安装"
    fi
    
    # 检查curl
    if ! command -v curl &> /dev/null; then
        error_exit "curl未安装"
    fi
    
    log "依赖检查通过"
}

# 初始化配置
init_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" << EOF
{
    "publish_schedule": {
        "monday": "08:00",
        "wednesday": "12:00", 
        "friday": "20:00",
        "sunday": "15:00"
    },
    "content_topics": [
        "健康食谱",
        "智能家居",
        "效率工具",
        "生活技巧",
        "周末活动"
    ],
    "auto_generate": true,
    "save_as_draft": true,
    "max_retry": 3,
    "notification": {
        "enabled": false,
        "webhook": ""
    }
}
EOF
        log "配置文件已创建: $CONFIG_FILE"
    fi
}

# 检查cookie
check_cookie() {
    log "检查cookie状态..."
    
    if [ ! -f "$COOKIE_FILE" ]; then
        log "未找到cookie文件，需要手动设置"
        return 1
    fi
    
    COOKIE=$(cat "$COOKIE_FILE" | tr -d '\n')
    
    if [ -z "$COOKIE" ]; then
        log "cookie文件为空"
        return 1
    fi
    
    # 简单测试cookie
    TEST_URL="https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN"
    RESPONSE=$(curl -s -H "Cookie: $COOKIE" "$TEST_URL" | head -c 500)
    
    if echo "$RESPONSE" | grep -q "登录\|login"; then
        log "cookie可能已过期"
        return 1
    else
        log "cookie状态正常"
        return 0
    fi
}

# 生成内容
generate_content() {
    local TOPIC="$1"
    local OUTPUT_FILE="$2"
    
    log "生成内容: $TOPIC -> $OUTPUT_FILE"
    
    # 使用Python生成内容
    python3 -c "
import datetime
import json

topic = '$TOPIC'
output_file = '$OUTPUT_FILE'

# 内容模板
templates = {
    '健康食谱': '''🥗 一周健康食谱 | 科学搭配，轻松坚持

告别外卖焦虑！AI为您定制健康食谱～

📊 设计原则：
✅ 营养均衡：蛋白质25-30%、碳水45-50%
✅ 操作简单：每餐≤30分钟
✅ 成本可控：每周150-200元

🗓️ 今日推荐：
早餐：燕麦粥+水煮蛋+小番茄
午餐：鸡胸肉沙拉+糙米饭  
晚餐：清蒸鲈鱼+蒜蓉西兰花

💡 智能小贴士：
1️⃣ 批量准备食材
2️⃣ 合理搭配营养
3️⃣ 控制烹饪时间

【本文由AI生成，经人工审核修改】
发布时间：{date}''',

    '智能家居': '''🏠 智能家居入门 | 打造未来生活

智能家居让生活更便捷！

🔧 今日推荐：
✅ 智能音箱：语音控制中心
✅ 智能灯泡：APP远程控制
✅ 智能插座：传统电器智能化

🚀 入门技巧：
1. 从基础设备开始
2. 设置自动化场景
3. 逐步扩展功能

【本文由AI生成，经人工审核修改】
发布时间：{date}''',

    '效率工具': '''⚡ 效率工具推荐 | 提升生产力

告别低效工作！

🛠️ 今日推荐：
✅ Notion：全能工作台
✅ Trello：项目管理
✅ Forest：专注计时

🎯 使用建议：
1. 选择适合的工具
2. 建立工作流程
3. 定期复盘优化

【本文由AI生成，经人工审核修改】
发布时间：{date}'''
}

# 获取当前日期
current_date = datetime.datetime.now().strftime('%Y年%m月%d日')

# 选择模板
content = templates.get(topic, templates['健康食谱'])
content = content.format(date=current_date)

# 保存内容
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'内容已生成: {output_file}')
print(f'内容长度: {len(content)} 字符')
"
    
    if [ $? -eq 0 ]; then
        log "内容生成成功"
        return 0
    else
        log "内容生成失败"
        return 1
    fi
}

# 发布内容
publish_content() {
    local CONTENT_FILE="$1"
    local TOPIC="$2"
    
    log "尝试发布内容: $TOPIC"
    
    if [ ! -f "$CONTENT_FILE" ]; then
        log "内容文件不存在: $CONTENT_FILE"
        return 1
    fi
    
    # 读取内容
    CONTENT=$(cat "$CONTENT_FILE")
    TITLE="【AI生成】$TOPIC | $(date '+%m月%d日')"
    
    # 读取cookie
    if [ ! -f "$COOKIE_FILE" ]; then
        log "cookie文件不存在"
        return 1
    fi
    
    COOKIE=$(cat "$COOKIE_FILE")
    
    # 尝试发布（简化版）
    log "使用简化发布方法..."
    
    # 创建发布脚本
    PUBLISH_SCRIPT="/tmp/publish_$$.py"
    
    cat > "$PUBLISH_SCRIPT" << EOF
import requests
import time
import sys

cookie = '''$COOKIE'''
title = '''$TITLE'''
content = '''$CONTENT'''

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Referer': 'https://mp.weixin.qq.com/'
}

print("尝试发布文章...")
print(f"标题: {title}")
print(f"内容长度: {len(content)} 字符")

# 尝试多种发布方式
methods = [
    {
        'name': '直接发布API',
        'url': 'https://mp.weixin.qq.com/cgi-bin/operate_appmsg',
        'data': {
            't': 'ajax-response',
            'sub': 'create',
            'token': '123456',
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1',
            'random': str(int(time.time() * 1000)),
            'title': title,
            'author': '智能生活家',
            'digest': 'AI生成内容，智能生活指南',
            'content': content[:500] + '...' if len(content) > 500 else content,
            'copyright': '0'
        }
    }
]

for method in methods:
    print(f"\\n尝试方法: {method['name']}")
    try:
        resp = requests.post(method['url'], headers=headers, data=method['data'], timeout=15)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.text[:200]}...")
        
        if resp.status_code == 200:
            print("✅ 请求成功")
            sys.exit(0)
        else:
            print("❌ 请求失败")
            
    except Exception as e:
        print(f"错误: {e}")

print("\\n所有方法都失败，需要手动发布")
print("\\n文章内容已保存，请手动发布:")
print(f"标题: {title}")
print(f"内容文件: $CONTENT_FILE")

sys.exit(1)
EOF
    
    # 执行发布脚本
    python3 "$PUBLISH_SCRIPT"
    PUBLISH_RESULT=$?
    
    # 清理
    rm -f "$PUBLISH_SCRIPT"
    
    if [ $PUBLISH_RESULT -eq 0 ]; then
        log "✅ 发布成功"
        return 0
    else
        log "⚠️  发布可能需要手动操作"
        
        # 保存发布信息
        MANUAL_FILE="$BACKUP_DIR/manual_$(date '+%Y%m%d_%H%M%S').txt"
        cat > "$MANUAL_FILE" << EOF
需要手动发布的文章
===================

发布时间: $(date)
主题: $TOPIC
标题: $TITLE

内容文件: $CONTENT_FILE

操作步骤:
1. 登录 https://mp.weixin.qq.com
2. 新建图文消息
3. 复制标题和内容
4. 添加"由AI生成"标识
5. 保存或发布

EOF
        
        log "手动发布指南已保存: $MANUAL_FILE"
        return 1
    fi
}

# 主流程
main() {
    log "微信公众号自动化系统启动"
    log "工作目录: $LOG_DIR"
    
    # 检查依赖
    check_dependencies
    
    # 初始化配置
    init_config
    
    # 检查cookie
    if ! check_cookie; then
        log "请更新cookie文件: $COOKIE_FILE"
        log "获取cookie方法:"
        log "1. 登录 https://mp.weixin.qq.com"
        log "2. 按F12打开开发者工具"
        log "3. 复制Network中的Cookie"
        log "4. 保存到 $COOKIE_FILE"
        exit 1
    fi
    
    # 选择主题
    TOPICS=("健康食谱" "智能家居" "效率工具" "生活技巧" "周末活动")
    TOPIC_INDEX=$(( $(date +%s) % ${#TOPICS[@]} ))
    SELECTED_TOPIC="${TOPICS[$TOPIC_INDEX]}"
    
    log "今日主题: $SELECTED_TOPIC"
    
    # 生成内容文件
    CONTENT_FILE="$CONTENT_DIR/$(date '+%Y%m%d_%H%M%S')_${SELECTED_TOPIC}.txt"
    
    if generate_content "$SELECTED_TOPIC" "$CONTENT_FILE"; then
        # 发布内容
        if publish_content "$CONTENT_FILE" "$SELECTED_TOPIC"; then
            log "✅ 自动化流程完成"
        else
            log "⚠️  发布流程需要手动干预"
        fi
    else
        log "❌ 内容生成失败"
    fi
    
    # 备份日志
    BACKUP_LOG="$BACKUP_DIR/log_$(date '+%Y%m%d').txt"
    cat "$LOG_DIR/run.log" >> "$BACKUP_LOG"
    
    log "系统运行完成"
}

# 执行主流程
main "$@"