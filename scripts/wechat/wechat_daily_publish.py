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

# 通义千问API（用qwen-plus写作用）
QWEN_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_KEY = "sk-ad7b90eb92ee4a21a9bd02e368b6d9e2"
QWEN_MODEL = "qwen3.5-plus"

# 每日主题池（按星期分组）
TOPIC_POOLS = {
    0: [  # 周一
        "周一综合症：为什么每个周一都不想起床",
        "新的一周，你最想改变的一件事是什么",
        "周一的地铁比平时更挤，我们在赶什么",
        "重启：为什么电脑重启能解决90%的问题，人却不行",
        "周一的咖啡，和周五的咖啡有什么不同",
        "每一个周一，都是一次假装重新开始",
    ],
    1: [  # 周二
        "外卖小哥的时速：我们是不是都被困在倒计时里",
        "凌晨两点的便利店，谁还在",
        "手机电量低于20%时的焦虑",
        "你在通勤路上想到过什么念头",
        "便利店的关东煮比米其林治愈",
        "电梯里的沉默：一栋楼的人谁也不认识谁",
    ],
    2: [  # 周三
        "一周过半你还在坚持上周的决定吗",
        "效率悖论：工具越多人越累",
        "收藏100篇文章读了0篇这是什么病",
        "日历上写满待办但没有一件是自己想做的",
        "周三了周末计划是不是又泡汤了",
    ],
    3: [  # 周四
        "朋友圈里过得最好的人私下是什么样",
        "多久没跟一个老朋友聊过天了",
        "已读不回：现代社交最体面的冷暴力",
        "你上一次认真听别人说话是什么时候",
        "群聊里的沉默比吵架更难受",
    ],
    4: [  # 周五
        "周五下午三点的空气为什么闻起来不一样",
        "周末自由你真的自由吗",
        "终于周五了这句话说了多少年",
        "周五晚上的酒喝的不是酒是自由",
        "周末计划从充满期待到睡到中午",
    ],
    5: [  # 周六
        "断网24小时会发生什么",
        "一个人待着的时候你都在干什么",
        "数字断舍离删掉100个App之后",
        "厨房里一个人的晚餐",
        "周末醒得比工作日还早这是什么体质",
    ],
    6: [  # 周日
        "周日晚上睡不着的人在怕什么",
        "发呆算不算一种能力",
        "你有多久没有无聊过了",
        "给下周写一封信你会说什么",
        "周日黄昏一周里最诚实的时刻",
    ],
}

# 写作风格池（强化版，带范例）
STYLE_POOLS = [
    {
        "name": "冷吐槽",
        "prompt": """你是一个毒舌但不好笑的人，像脱口秀演员写段子。看到什么都想吐槽一句。

写法要求：
- 短句。一句吐槽接一句吐槽。不要连成段落。
- 具体场景。不要说"很多人"，要说"隔壁老王"。不要说"有人"，要说"我同事小张"。
- 不要说教，不要总结。只吐槽，不给答案。
- 结尾突然收住，像说完最后一句就走了。

示例（供参考风格，不要抄内容）：
「闹钟设了六个。6:00，6:05，6:10，6:15，6:20，6:25。每个都响了，每个都关了。最后一个响的时候我想，今天请假吧。然后真的请了。理由写的是：身体不适。翻译一下：床太舒服。」「买了效率App来管理效率App。这叫效率套娃。俄罗斯人看了都得叫老师。」

现在写一篇约600字的文章。直接开始，不要标题，不要开头过渡。""",
    },
    {
        "name": "白描日记",
        "prompt": """你是一个普通人，写今天发生的事。像写日记，但只记细节，不要写感受。

写法要求：
- 只写动作和画面。"闹钟响了，我按掉。窗外有鸟叫。"这样。
- 不要写"我想""我觉得""这让我意识到"。只写看到的、听到的、摸到的。
- 短句。像摄像机在记录，不要形容词堆砌。
- 场景要具体到时间、地点、细节。"凌晨2点的7-11"比"深夜的便利店"好。

示例（供参考风格）：
「7点15，闹钟。关掉。7点20，闹钟。关掉。7点30，没闹钟了，急。」「便利店阿姨问我半夜吃这么少够不够。我说够了。她多给了一根香肠。」

现在写一篇约600字的文章。不要标题，直接从第一个细节开始。""",
    },
    {
        "name": "碎碎念",
        "prompt": """你是一个人在深夜自言自语。句子很短，想到哪写到哪，不照顾逻辑。

写法要求：
- 一句一段。短的句子就几个字，长的也不超过20字。
- 跳跃。上一句说咖啡，下一句可以说天气。脑子的走向就是这样。
- 不要解释。不要说"这让我想到"，直接跳。
- 结尾可以突然停下，像睡着了或者不想写了。

示例：
「咖啡。凉了。微波炉叮了30秒。又凉了。算了。」「窗外有猫叫。不知道谁家的。听起来像饿了。我想起冰箱里还有剩饭。然后猫不叫了。它叫的时候我没动。」

现在写一篇约600字的文章。一句话开始。""",
    },
    {
        "name": "内心戏",
        "prompt": """你是一个人对着空气说话，对自己说话，对一个不存在的人说话。

写法要求：
- 用"你"来称呼。可以是过去的自己，可以是某个走了的人，可以是一切你想说给的人。
- 私密。不说大家都知道的道理，说你心里很角落的东西。
- 口语化，像真的在说话。可以跑题，可以乱。
- 结尾不需要收束，停在一个情绪的点上就行。

示例：
「你还记得那时候说好的吗。我忘了。」「你走之后我买了好多东西。都不用。」

现在写一篇约600字的文章。开头就称呼"你"。""",
    },
    {
        "name": "清单体",
        "prompt": """你脑子里现在有一张清单。不是待办事项，是可能想到的所有东西。

写法要求：
- 用序号或者符号开头。1/2/3，或者随便什么标记。
- 每一项不超过30字。可以是事、人、念头、画面。
- 不分类。想起什么写什么。
- 清单之间可以有情绪流动，但不要解释。

示例：
「1. 今天忘了吃早餐
2. 昨天的早餐也没吃
3. 好像最近都没在吃早餐
4. 应该买点面包囤着
5. 上次买的面包长霉了」

现在写一篇约600字的清单。从任意一项开始。""",
    },
    {
        "name": "微型小说",
        "prompt": """写一个小故事。不是完整的故事，是生活的一个切片。

写法要求：
- 有人物（可以无名的"他"或"她"）、有场景、有动作。
- 没有结局。不要说教。就像截取了生活的一个片段。
- 细节要具体。"他点了拿铁"比"他点了咖啡"好。"她站在711门口"比"她站在便利店门口"好。
- 不要心理描写。不要写"她想"，写她做了什么。

示例：
「他站在货架前，拿着两罐啤酒。左手拿一罐，右手拿一罐。放了回去。又拿起来。放了回去。最后两罐都没买。」

现在写一篇约600字的微型小说。从一个人、一个动作开始。""",
    },
    {
        "name": "城市漫游",
        "prompt": """你走在城市里，看到什么写什么。像拿着相机在拍。

写法要求：
- 只写城市里的画面。便利店、地铁、街角、店铺招牌、下雨的地面。
- 不写自己。不写"我看到"，直接写画面。
- 可以有人，不一定要有情节。
- 像拍了一组照片，然后一张张写出来。

示例：
「便利店门口的电风扇还转着。秋天了。」「地铁口的算命摊换了人。新的那个不问你要不要算命，问你要不要买保险。」

现在写一篇约600字的城市漫游。从一个具体地点开始。""",
    },
    {
        "name": "假装开头",
        "prompt": """每一段都像一篇文章的开头。但都不继续写下去。

写法要求：
- 一段就是一两句话，像要开始讲一个故事，但突然换下一个了。
- 可以是不同主题，但要有内在的情绪线。
- 不要解释为什么换。
- 结尾也不需要收束。

示例：
「有一次我在凌晨三点的街上走...」「说到跑步这件事，我从没坚持过超过三天...」「其实昨天本来想说一件事...」

现在写一篇约600字的文章。一个开头开始。""",
    },
]


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
    prompt = f"""主题：{topic}

{style['prompt']}

注意：
- 输出HTML格式：用<p>分段，用<strong>加粗关键短语（少用）
- 不要写标题，我另外加
- 不要输出任何其他内容，只输出文章正文"""

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
                    {"role": "system", "content": "你是一个写生活随笔的作家。你的文字短、冷、具体。你从不升华，从不给人生建议。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.92,
                "top_p": 0.88,
                "max_tokens": 2000,
                "extra_body": {"enable_thinking": False}
            },
            timeout=120
        )

        if r.status_code == 200:
            result = r.json()
            content = result['choices'][0]['message']['content'].strip()
            if content and len(content) > 300:
                log(f"✅ qwen-plus生成成功，风格={style['name']}，字数={len(content)}")
                content = re.sub(r'^```html\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                image_prompt = f"{topic}, daily life, natural lighting, warm atmosphere"
                return topic, content, image_prompt
            else:
                log(f"⚠️ 内容过短: {len(content)}字")
        else:
            log(f"❌ API失败: {r.status_code}")
    except Exception as e:
        log(f"❌ 异常: {e}")

    return None


def save_archive(title, content):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title[:20])
    filepath = os.path.join(ARCHIVE_DIR, f"{date_str}_{safe_title}.md")
    text = re.sub(r'<[^>]+>', '', content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n日期: {date_str}\n\n{text}")
    log(f"📝 归档: {filepath}")


def main():
    log("=== 开始每日发布 ===")
    lock_fd = acquire_lock()

    token = get_token()
    if not token:
        sys.exit(1)

    weekday = datetime.datetime.now().weekday()
    topics = TOPIC_POOLS.get(weekday, TOPIC_POOLS[0])
    day_seed = int(datetime.datetime.now().strftime('%Y%m%d'))

    import random
    random.seed(day_seed)
    topic = random.choice(topics)
    style = random.choice(STYLE_POOLS)

    log(f"主题: {topic}")
    log(f"风格: {style['name']}")

    # 生成文章（最多重试3次）
    article = None
    for attempt in range(3):
        article = generate_article_with_ai(topic, style)
        if article:
            break
        log(f"⚠️ 第{attempt+1}次失败")
        style = random.choice(STYLE_POOLS)
        log(f"换风格: {style['name']}")

    if not article:
        log("❌ 生成失败")
        sys.exit(1)

    title, content, image_prompt = article

    # 加AI标识
    date_str = datetime.datetime.now().strftime('%Y年%m月%d日')
    content += f"\n<p>【本文由AI生成，经人工审核修改】<br/>{date_str}</p>"

    # 封面
    cover_path = generate_cover(image_prompt)
    if not cover_path:
        log("❌ 封面失败")
        sys.exit(1)

    thumb_media_id = upload_cover(token, cover_path)
    if not thumb_media_id:
        log("❌ 上传失败")
        sys.exit(1)

    # 草稿
    plain_text = re.sub(r'<[^>]+>', '', content)
    digest = plain_text[:60]
    draft_id = create_draft(token, title, content, thumb_media_id, digest)

    if draft_id:
        log(f"✅ 草稿提交成功 media_id={draft_id}")
        log(f"   标题: {title} | 风格: {style['name']}")
        save_archive(title, content)
    else:
        sys.exit(1)

    log("=== 完成 ===")


if __name__ == "__main__":
    main()
