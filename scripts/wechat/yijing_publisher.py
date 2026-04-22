#!/usr/bin/env python3
"""
易经全解系列自动发布脚本
每天9点由cron触发，按顺序发布下一章
"""

import requests
import json
import datetime
import time
import os
import sys
import re

APPID = "wx4d76a79c84e3ebbc"
SECRET = "72d4248a0d0384384884116ff2470e06"
STATE_FILE = "/root/.openclaw/workspace/config/yijing_state.json"
LOG_FILE = "/tmp/wechat_daily.log"

def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] [易经] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    r = requests.get(url, timeout=10).json()
    if 'access_token' in r:
        return r['access_token']
    log(f"❌ token失败: {r}")
    return None

def upload_cover(token, image_path):
    if not os.path.exists(image_path):
        log(f"❌ 封面不存在: {image_path}")
        return None
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    with open(image_path, 'rb') as f:
        r = requests.post(url, files={'media': ('cover.jpg', f, 'image/jpeg')}, timeout=30).json()
    if 'media_id' in r:
        return r['media_id']
    log(f"❌ 封面上传失败: {r}")
    return None

def generate_cover(token, prompt, seed=None):
    if seed is None:
        seed = int(time.time())
    encoded = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=768&nologo=true&seed={seed}"
    path = f"/tmp/yijing_cover_{seed}.jpg"
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 1000:
            if r.content[:3] == b'\xff\xd8\xff' or r.content[:4] == b'\x89PNG':
                with open(path, 'wb') as f:
                    f.write(r.content)
                log(f"✅ 封面生成: {path}")
                mid = upload_cover(token, path)
                return mid
    except Exception as e:
        log(f"⚠️ 封面失败: {e}")
    return None

def create_draft(token, title, content, thumb_media_id, digest=""):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    article = {
        "title": title,
        "author": "虾大",
        "content": content,
        "digest": digest,
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
    log(f"❌ 草稿失败: {r}")
    return None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"chapter": 1, "published": [], "started": datetime.datetime.now().strftime('%Y-%m-%d')}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_chapter(num):
    """根据章节号返回 (title, digest, content, cover_prompt)"""
    chapters = {
        1: {
            "title": "闲聊易经｜01开篇：不是算命，是看变化的方法论",
            "digest": "易经被误解了两千年，它不是算命，是教你做选择的智慧。",
            "prompt": "ancient Chinese I Ching book open on wooden table, warm candlelight, bamboo slips, yin yang symbol, peaceful zen atmosphere",
            "file": "/root/.openclaw/workspace/articles/yijing/01_开篇.md"
        },
        2: {
            "title": "闲聊易经｜02阴阳：世界的基本密码",
            "digest": "阴阳不是玄学，是古人对世界最基本的观察。",
            "prompt": "yin yang symbol in nature, moon and sun, day and night, Chinese traditional painting, flowing water, mountains, harmonious balance",
            "file": "/root/.openclaw/workspace/articles/yijing/02_阴阳.md"
        },
        3: {
            "title": "闲聊易经｜03八卦：万物的八种状态",
            "digest": "天、地、雷、风、水、火、山、泽，世界就这八种东西。",
            "prompt": "eight trigrams bagua arranged in circle, traditional Chinese ink painting, natural elements water fire mountain wind, ancient scroll style",
            "file": "/root/.openclaw/workspace/articles/yijing/03_八卦.md"
        },
        4: {
            "title": "闲聊易经｜04入门：怎么读懂一卦",
            "digest": "卦象不是画符，有固定的阅读方法。",
            "prompt": "Chinese scholar studying ancient text, brush and ink, bamboo slips with hexagram diagrams, quiet study room, warm lamp",
            "file": "/root/.openclaw/workspace/articles/yijing/04_入门.md"
        },
    }
    return chapters.get(num)

def main():
    log("=== 易经全解系列发布 ===")

    state = load_state()
    chapter_num = state.get("chapter", 1)

    # 检查是否有这一章的内容文件
    chapter = get_chapter(chapter_num)

    if not chapter:
        log(f"⚠️ 第{chapter_num}章内容尚未准备好，跳过")
        # 更新cron回到日常发布
        return

    # 如果有本地md文件，从文件读取内容
    if os.path.exists(chapter["file"]):
        with open(chapter["file"], 'r', encoding='utf-8') as f:
            content = f.read()
        # 转换为HTML（简单处理：段落用<p>，##用<h2>）
        html_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('**') and line.endswith('**'):
                html_lines.append(f'<p><strong>{line[2:-2]}</strong></p>')
            else:
                # 处理行内加粗
                line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                html_lines.append(f'<p>{line}</p>')
        html_content = '\n'.join(html_lines)

        # 加上页脚
        html_content += f"""
<hr>
<p>【闲聊易经·{chapter_num:02d}】</p>
<p>以上均为个人观点，如有错误的地方，还请海涵。</p>
<p>【本文由AI生成，经人工审核修改】<br/>生成时间：{datetime.datetime.now().strftime('%Y年%m月%d日')}</p>"""
    else:
        log(f"⚠️ 章节文件不存在: {chapter['file']}，跳过")
        return

    # 获取token
    token = get_token()
    if not token:
        sys.exit(1)

    # 生成封面
    thumb_media_id = generate_cover(token, chapter["prompt"], seed=1000 + chapter_num)
    if not thumb_media_id:
        log("❌ 封面失败，退出")
        sys.exit(1)

    # 提交草稿
    draft_id = create_draft(token, chapter["title"], html_content, thumb_media_id, chapter["digest"])

    if draft_id:
        log(f"✅ 第{chapter_num}章已提交: {chapter['title']}")
        state["chapter"] = chapter_num + 1
        state["published"].append({
            "num": chapter_num,
            "title": chapter["title"],
            "date": datetime.datetime.now().strftime('%Y-%m-%d'),
            "media_id": draft_id
        })
        save_state(state)
        log(f"   下一章: 第{chapter_num + 1}章")
    else:
        log("❌ 提交失败")

    log("=== 发布结束 ===")

if __name__ == "__main__":
    main()
