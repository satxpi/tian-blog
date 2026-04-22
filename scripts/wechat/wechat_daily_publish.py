#!/usr/bin/env python3
"""
微信公众号每日自动发布脚本
用通义千问AI实时生成文章，多样写作风格，每篇都不一样

用法: python3 wechat_daily_publish.py
定时任务: 0 8 * * * python3 /root/.openclaw/workspace/scripts/wechat/wechat_daily_publish.py >> /tmp/wechat_daily.log 2>&1
"""

import requests
import json
import datetime
import os
import sys
import fcntl
import re

# 配置
APPID = "wx4d76a79c84e3ebbc"
SECRET = "72d4248a0d0384384884116ff2470e06"
LOG_FILE = "/tmp/wechat_daily.log"
LOCK_FILE = "/tmp/wechat_daily_publish.lock"
ARCHIVE_DIR = "/root/.openclaw/workspace/articles/daily"

# 通义千问API
QWEN_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_KEY = "sk-ad7b90eb92ee4a21a9bd02e368b6d9e2"
QWEN_MODEL = "qwen-turbo"

# 每日主题池（按星期分组，每天随机选一个）
TOPIC_POOLS = {
    0: [  # 周一 - 新开始/重启
        "周一综合症：为什么每个周一都不想起床",
        "新的一周，你最想改变的一件事是什么",
        "周一的地铁比平时更挤，我们在赶什么",
        "重启：为什么电脑重启能解决90%的问题，人却不行",
        "周一的咖啡，和周五的咖啡有什么不同",
        "每一个周一，都是一次假装重新开始",
        "周一早上的闹钟，是你和自己的第一次谈判",
    ],
    1: [  # 周二 - 日常观察
        "外卖小哥的时速：我们是不是都被困在倒计时里",
        "凌晨两点的便利店，谁还在",
        "手机电量低于20%时的焦虑，和真正的焦虑有什么区别",
        "你在通勤路上想到过什么改变人生的念头",
        "为什么我们总在深夜做决定，早上又推翻",
        "便利店的关东煮，比米其林更治愈",
        "电梯里的沉默：一栋楼的人，谁也不认识谁",
    ],
    2: [  # 周三 - 反思/中点
        "一周过半，你还在坚持上周的决定吗",
        "效率悖论：工具越多，人越累",
        "我们用多少时间在做'准备工作'",
        "中年危机提前了：25岁就开始焦虑的人",
        "周三了，你的周末计划是不是又泡汤了",
        "收藏了100篇文章，读了0篇，这是什么病",
        "日历上写满了待办，但没有一件是自己想做的",
    ],
    3: [  # 周四 - 人际/情感
        "朋友圈里过得最好的人，私下是什么样",
        "多久没跟一个老朋友聊过天了",
        "社交媒体上的'真实'，到底有多真实",
        "你上一次认真听别人说话是什么时候",
        "合群：是选择还是妥协",
        "已读不回：现代社交最体面的冷暴力",
        "群聊里的沉默，比吵架更让人难受",
    ],
    4: [  # 周五 - 释放/期待
        "周五下午三点的空气，为什么闻起来不一样",
        "周末自由：你真的自由吗",
        "从996到躺平，我们到底在选什么",
        "你的周末，是谁的周末",
        "终于周五了——这句话说了多少年",
        "周五晚上的酒，喝的不是酒是自由",
        "周末计划：从充满期待到睡到中午",
    ],
    5: [  # 周六 - 生活/独处
        "断网24小时会发生什么",
        "一个人待着的时候，你都在干什么",
        "数字断舍离：删掉100个App之后",
        "厨房里一个人的晚餐",
        "书架上有多少书，是你永远不会读的",
        "周末醒得比工作日还早，这是什么体质",
        "一个人的下午：不回消息的权利",
    ],
    6: [  # 周日 - 放空/准备
        "周日晚上睡不着的人，在怕什么",
        "发呆算不算一种能力",
        "你有多久没有无聊过了",
        "慢：在这个所有人都赶时间的时代",
        "给下周写一封信，你会说什么",
        "周日黄昏：一周里最诚实的时刻",
        "周末的尾巴，总比周一先到",
    ],
}

# 写作风格池（每次随机选一个，确保文章风格多样）
STYLE_POOLS = [
    {
        "name": "碎碎念日记",
        "desc": "像写私密日记一样，想到哪写到哪，短句，跳跃，不要逻辑连贯，像一个人在深夜自言自语。句子要碎，不要完整段落。",
        "examples": "闹钟。关掉。再响。再关。几点了。七点四十。完了。"
    },
    {
        "name": "冷幽默观察",
        "desc": "用冷冷的语气观察日常，像脱口秀演员在吐槽生活。不夸张，不动情，就是冷冷的、准确的、好笑的。结尾要突然收住，像说了一半不想说了。",
        "examples": "我买了一个效率App来管理我的效率App。这个句子的荒谬程度，就是我的真实生活。"
    },
    {
        "name": "市井烟火气",
        "desc": "写菜市场、早餐摊、地铁口、出租屋。用最接地气的语言写最普通的生活。要有味觉、嗅觉、触觉。像汪曾祺写吃的那样，把平凡写出香味来。",
        "examples": "巷口的煎饼摊换了人。新来的大姐手脚利索，但酱刷得少。一口下去，总觉得缺了什么。"
    },
    {
        "name": "书信体",
        "desc": "像写给某个人（可以是不存在的老朋友、未来的自己、或者某个已经走散的人）的信。用'你'来称呼。私密、温柔、有点怀旧。",
        "examples": "你还记得吗，那年我们在天台上喝啤酒，你说三十岁以后要开一家书店。"
    },
    {
        "name": "意识流",
        "desc": "像河流一样流淌，没有起承转合，一个念头接一个念头。长短句交替，有时候一个字就是一段。像看着窗外发呆时脑子里跑过的那些碎片。",
        "examples": "雨。窗。咖啡凉了。想起昨天忘回的消息。算了。"
    },
    {
        "name": "对白体",
        "desc": "整篇文章由对话推进，像剧本，像偷听到的对话。可以是两个人的，也可以是一个人的内心对话。对话要口语化，要有潜台词。",
        "examples": "「又加班？」「嗯。」「几点能走？」「不知道。」——不知道是说几点，还是说能不能走。"
    },
    {
        "name": "微型叙事",
        "desc": "讲一个小故事，不需要完整，像截取了生活的一个片段。有人物、场景、动作，但没有结局。像一篇没拍完的短片。用细节而非形容词。",
        "examples": "他站在711门口，拿着两罐啤酒，犹豫了三十秒，放回去一罐。"
    },
    {
        "name": "清单体",
        "desc": "用清单/列举的方式写，但不是123条建议，而是一个人脑子里的清单——要买的东西、想做但没做的事、记得住的瞬间。清单之间要有情绪流动。",
        "examples": "待办：回妈电话、交房租、找那本失踪的书、想起一个忘了名字的人。"
    },
]


def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def acquire_lock():
    """防重复执行锁"""
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
        log(f"❌ 封面文件不存在: {image_path}")
        return None
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    with open(image_path, 'rb') as f:
        r = requests.post(url, files={'media': ('cover.jpg', f, 'image/jpeg')}, timeout=30).json()
    if 'media_id' in r:
        return r['media_id']
    log(f"❌ 封面上传失败: {r}")
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
                log(f"✅ 封面生成: {path}")
                return path
        log(f"⚠️ 封面生成异常，status={r.status_code}, size={len(r.content)}")
    except Exception as e:
        log(f"⚠️ 封面生成失败: {e}")
    return None


def create_draft(token, title, content, thumb_media_id, digest=""):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    article = {
        "title": title,
        "author": "虾大",
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


def generate_article_with_ai(topic, style):
    """调用通义千问生成文章"""
    prompt = f"""你是一位生活随笔作家。请围绕主题「{topic}」写一篇微信公众号文章。

写作风格：{style['name']}
风格要求：{style['desc']}
风格示例：{style['examples']}

硬性要求：
1. 篇幅800-1200字
2. 用HTML格式输出：<p>分段，<h2>小标题（最多1个），<strong>加粗关键句
3. 不要说教，不要给建议，不要列123点
4. 不要"在这个...的时代"开头
5. 不要"让我们一起..."结尾
6. 不要反问句结尾
7. 不要强行升华给人生哲理
8. 结尾要像聊天突然挂了电话一样收住，不要总结
9. 8点日常文章不加"以上均为个人观点"

直接输出HTML文章内容，不要输出任何其他内容。"""

    try:
        r = requests.post(
            f"{QWEN_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {QWEN_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一位有才华的生活随笔作家，擅长用独特的风格写日常生活。你从不废话，从不模板化。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.95,
                "top_p": 0.9,
                "max_tokens": 3000,
            },
            timeout=120
        )

        if r.status_code == 200:
            result = r.json()
            content = result['choices'][0]['message']['content'].strip()
            if content and len(content) > 200:
                log(f"✅ 通义千问生成成功，风格: {style['name']}，字数: {len(content)}")
                # 清理可能的多余标记
                content = re.sub(r'^```html\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                image_prompt = f"{topic}, {style['name']} style, warm atmosphere, daily life, natural lighting"
                return topic, content, image_prompt
            else:
                log(f"⚠️ AI返回内容过短: {len(content)}字")
        else:
            log(f"❌ 通义千问API失败: status={r.status_code}, body={r.text[:200]}")
    except Exception as e:
        log(f"❌ AI生成异常: {e}")

    return None


def save_archive(title, content):
    """归档文章到本地"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    # 清理标题中的特殊字符
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title[:20])
    filepath = os.path.join(ARCHIVE_DIR, f"{date_str}_{safe_title}.md")
    text = re.sub(r'<[^>]+>', '', content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"日期: {date_str}\n\n")
        f.write(text)
    log(f"📝 文章已归档: {filepath}")


def main():
    log("=== 开始每日发布 ===")

    # 防重复锁
    lock_fd = acquire_lock()

    # 获取token
    token = get_token()
    if not token:
        log("❌ 获取token失败，退出")
        sys.exit(1)

    # 选择主题（用日期做种子，同一天选同一个）
    weekday = datetime.datetime.now().weekday()
    topics = TOPIC_POOLS.get(weekday, TOPIC_POOLS[0])
    day_seed = int(datetime.datetime.now().strftime('%Y%m%d'))

    import random
    random.seed(day_seed)
    topic = random.choice(topics)

    # 选择写作风格（用日期做种子，确保每天风格不同）
    style = random.choice(STYLE_POOLS)

    log(f"今日主题: {topic}")
    log(f"写作风格: {style['name']}")

    # AI生成文章（最多重试3次）
    article = None
    for attempt in range(3):
        article = generate_article_with_ai(topic, style)
        if article:
            break
        log(f"⚠️ 第{attempt+1}次生成失败，重试...")
        if attempt < 2:
            # 换个风格再试
            style = random.choice(STYLE_POOLS)
            log(f"切换风格: {style['name']}")

    if not article:
        log("❌ AI生成3次均失败，退出")
        sys.exit(1)

    title, content, image_prompt = article

    # 8点文章只加AI标识，不加"以上均为个人观点"
    date_str = datetime.datetime.now().strftime('%Y年%m月%d日')
    content += f"\n<p>【本文由AI生成，经人工审核修改】<br/>生成时间：{date_str}</p>"

    # 生成封面
    cover_path = generate_cover(image_prompt)
    if not cover_path:
        log("❌ 封面生成失败，退出")
        sys.exit(1)

    # 上传封面
    thumb_media_id = upload_cover(token, cover_path)
    if not thumb_media_id:
        log("❌ 封面上传失败，退出")
        sys.exit(1)

    # 创建草稿
    plain_text = re.sub(r'<[^>]+>', '', content)
    digest = plain_text[:60]
    draft_id = create_draft(token, title, content, thumb_media_id, digest)

    if draft_id:
        log(f"✅ 草稿提交成功！media_id: {draft_id}")
        log(f"   标题: {title}")
        log(f"   风格: {style['name']}")
        save_archive(title, content)
    else:
        log("❌ 草稿提交失败")
        sys.exit(1)

    log("=== 发布完成 ===")


if __name__ == "__main__":
    main()
