#!/usr/bin/env python3
"""
微信公众号每日自动发布脚本
读取预生成的文章markdown文件，提交到草稿箱

文章文件路径: /root/.openclaw/workspace/articles/daily/YYYY-MM-DD.md
由AI提前一天生成好，脚本只负责发布
"""

import requests
import json
import datetime
import time
import os
import sys
import fcntl
import re
import subprocess

# 配置
APPID = "wx4d76a79c84e3ebbc"
SECRET = "72d4248a0d0384384884116ff2470e06"
LOG_FILE = "/tmp/wechat_daily.log"
LOCK_FILE = "/tmp/wechat_daily_publish.lock"
ARTICLE_DIR = "/root/.openclaw/workspace/articles/daily"

# 轮换主题池 - 每天不同类型，保持多样性
# 周一: 实用技巧
# 周二: 健康养生
# 周三: 热点解读
# 周四: 生活故事/悬疑
# 周五: 工具测评
# 周六: 轻松趣味
# 周日: 深度思考

TOPIC_TYPES = {
    0: "实用技巧",  # 周一：手机功能、科技工具、隐藏设置等
    1: "健康养生",  # 周二：颈椎腰椎、居家锻炼、睡眠改善等
    2: "热点解读",  # 周三：当天热点、财经新闻、社会现象解读
    3: "生活故事",  # 周四：真实故事、悬疑案件、人物经历等
    4: "工具测评",  # 周五：APP测评、产品对比、使用体验等
    5: "轻松趣味",  # 周六：搞笑段子、冷知识、趣味发现等
    6: "深度思考",  # 周日：观点文章、人生感悟、社会观察等
}

def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def acquire_lock():
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except (IOError, OSError):
        log("⚠️ 另一个实例正在运行，跳过")
        sys.exit(0)

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    r = requests.get(url, timeout=10).json()
    if 'access_token' in r:
        return r['access_token']
    log(f"❌ token失败: {r}")
    return None

def upload_cover(token, image_path):
    if not os.path.exists(image_path):
        return None
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    with open(image_path, 'rb') as f:
        r = requests.post(url, files={'media': ('cover.jpg', f, 'image/jpeg')}, timeout=30).json()
    if 'media_id' in r:
        return r['media_id']
    return None

def generate_cover(prompt):
    ts = int(datetime.datetime.now().timestamp())
    encoded = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=768&nologo=true&seed={ts}"
    path = f"/tmp/wechat_cover_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 1000:
            if r.content[:3] == b'\xff\xd8\xff' or r.content[:4] == b'\x89PNG':
                with open(path, 'wb') as f:
                    f.write(r.content)
                return path
    except:
        pass
    return None

def create_draft(token, title, content, thumb_media_id, digest=""):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    article = {
        "title": title,
        "author": "生活与简单",
        "content": content,
        "digest": digest[:120] if digest else "",
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "show_cover_pic": 1,
        "need_open_comment": 0,
        "only_fans_can_comment": 0
    }
    data = {"articles": [article]}
    json_str = json.dumps(data, ensure_ascii=False).encode('utf-8')
    r = requests.post(url, data=json_str, headers={'Content-Type': 'application/json; charset=utf-8'}, timeout=30).json()
    if 'media_id' in r:
        return r['media_id']
    log(f"❌ 草稿创建失败: {r}")
    return None

def parse_markdown(filepath):
    """解析markdown文件，提取标题和内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.strip().split('\n')
    title = ""
    content_lines = []
    
    for line in lines:
        if line.startswith('# ') and not title:
            title = line[2:].strip()
            continue
        content_lines.append(line)
    
    content = '\n'.join(content_lines).strip()
    html = markdown_to_html(content)
    
    return title, html

def markdown_to_html(text):
    """简单markdown转HTML"""
    lines = text.split('\n')
    html_lines = []
    in_code = False
    in_list = False
    
    for line in lines:
        if line.startswith('```'):
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False
            else:
                html_lines.append('<pre><code>')
                in_code = True
            continue
        
        if in_code:
            html_lines.append(line)
            continue
        
        if not line.strip():
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('')
            continue
        
        if line.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{line[4:].strip()}</h3>')
            continue
        if line.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{line[3:].strip()}</h2>')
            continue
        
        if line.startswith('- ') or line.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{line[2:].strip()}</li>')
            continue
        
        if in_list:
            html_lines.append('</ul>')
            in_list = False
        
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'__(.+?)__', r'<strong>\1</strong>', line)
        line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
        line = re.sub(r'_(.+?)_', r'<em>\1</em>', line)
        
        html_lines.append(f'<p>{line}</p>')
    
    if in_list:
        html_lines.append('</ul>')
    if in_code:
        html_lines.append('</code></pre>')
    
    return '\n'.join(html_lines)

def generate_article_auto(today, topic_type, article_file):
    """使用openclaw agent自动生成日常文章"""
    day_prompts = {
        0: "实用技巧类（手机功能、科技工具、隐藏设置等冷门实用内容）",
        1: "健康养生类（颈椎腰椎、居家锻炼、睡眠改善等实用建议）",
        2: "热点解读类（近期社会热点、财经新闻、现象解读）",
        3: "生活故事/悬疑类（真实故事、悬疑案件、人物经历等）",
        4: "工具测评类（APP测评、产品对比、使用体验等）",
        5: "轻松趣味类（冷知识、趣味发现、搞笑段子等）",
        6: "深度思考类（人生感悟、社会观察、观点文章等）",
    }
    prompt = day_prompts.get(datetime.datetime.now().weekday(), "生活类")
    
    message = (
        f"请撰写一篇{today}的公众号日常文章，类型：{prompt}，保存到 {article_file}。\n\n"
        f"【核心原则：写得像真人写的博客文章，不像AI模板】\n\n"
        f"【必须避免的AI味】：\n"
        f"- 禁止'现象→分析→总结→升华'的固定套路\n"
        f"- 禁止每段末尾都来一句金句/总结句\n"
        f"- 禁止高频使用'但''然而''不是X，是Y'\n"
        f"- 禁止'我不是X，但…'的自谦式结尾\n"
        f"- 禁止每个观点都配一个完美案例\n"
        f"- 禁止情绪一路平稳，要有快慢松紧\n\n"
        f"【写作风格要求】：\n"
        f"- 从一个具体的场景、故事或对话切入，不要从大道理开始\n"
        f"- 段落长短参差：有的一句话成段，有的连续几段紧凑推进\n"
        f"- 用口语写，不用书面语（'然而'→'不过'，'因此'→'所以'）\n"
        f"- 细节要具体可感：不说'他很焦虑'，说'他盯着手机不停刷新屏幕'\n"
        f"- 可以突然跳转话题，可以停顿，可以话说到一半不说了——真人就这样\n"
        f"- 结尾不要总结升华，留白就好。让读者自己想\n"
        f"- 偶尔可以不完整、不工整，这反而真实\n\n"
        f"【格式】：\n"
        f"- 标题要有吸引力\n"
        f"- 结尾加「本文由AI生成，经人工审核修改」\n"
        f"- 不预告下一篇\n"
        f"- 直接写入文件，不需要确认"
    )
    
    cmd = [
        "openclaw", "agent",
        "--agent", "main",
        "--message", message,
        "--timeout", "300",
    ]
    
    log(f"🤖 文章不存在，开始自动生成... (类型: {topic_type})")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=320)
        if result.returncode == 0 and os.path.exists(article_file):
            log(f"✅ 文章自动生成完成: {article_file} ({os.path.getsize(article_file)} bytes)")
            return True
        else:
            log(f"❌ 生成失败 (exit={result.returncode}): {result.stderr[:300]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"❌ 生成超时（320秒）")
        return False
    except Exception as e:
        log(f"❌ 生成异常: {e}")
        return False


def main():
    lock_fd = acquire_lock()
    log("=== 开始每日发布 ===")
    
    # 检查今天的文章文件
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    weekday = datetime.datetime.now().weekday()  # 0=周一
    topic_type = TOPIC_TYPES.get(weekday, "生活")
    
    log(f"今日类型: {topic_type}")
    
    article_file = os.path.join(ARTICLE_DIR, f"{today}.md")
    
    # 文件不存在时自动生成
    if not os.path.exists(article_file):
        generated = generate_article_auto(today, topic_type, article_file)
        if not generated:
            log(f"❌ 文章自动生成失败")
            sys.exit(1)
    
    # 获取token
    token = get_token()
    if not token:
        sys.exit(1)
    
    # 解析文章
    title, content = parse_markdown(article_file)
    if not title or not content:
        log(f"❌ 文章解析失败")
        sys.exit(1)
    
    log(f"文章: {title}")
    
    # 生成封面
    cover_prompt = f"{title[:30]}, modern lifestyle, warm atmosphere"
    cover_path = generate_cover(cover_prompt)
    
    thumb_media_id = None
    if cover_path:
        thumb_media_id = upload_cover(token, cover_path)
        if thumb_media_id:
            log(f"✅ 封面上传成功")
    
    if not thumb_media_id:
        log("⚠️ 封面生成/上传失败，使用备用封面")
        # 尝试用一个简单的纯色封面
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (1024, 768), '#2C3E50')
            draw = ImageDraw.Draw(img)
            # 画一些简单的装饰
            for i in range(0, 1024, 80):
                draw.line([(i, 0), (i, 768)], fill='#34495E', width=1)
            for i in range(0, 768, 80):
                draw.line([(0, i), (1024, i)], fill='#34495E', width=1)
            path = f"/tmp/wechat_fallback_cover_{int(time.time())}.jpg"
            img.save(path, 'JPEG', quality=90)
            thumb_media_id = upload_cover(token, path)
            if thumb_media_id:
                log(f"✅ 备用封面上传成功")
        except Exception as e:
            log(f"⚠️ 备用封面也失败: {e}")

    if not thumb_media_id:
        log("❌ 所有封面方式都失败，退出")
        sys.exit(1)
    
    # 添加AI标识
    if "本文由AI生成" not in content:
        content += '<p style="color:#999;font-size:12px;margin-top:30px;">本文由AI生成，经人工审核修改</p>'
    
    # 创建草稿
    media_id = create_draft(token, title, content, thumb_media_id)
    
    if media_id:
        log(f"✅ 草稿创建成功: {title}")
        log(f"   media_id: {media_id}")
    else:
        log(f"❌ 草稿创建失败")
        sys.exit(1)
    
    log("=== 发布结束 ===")

if __name__ == "__main__":
    main()