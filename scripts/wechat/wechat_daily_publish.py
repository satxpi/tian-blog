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
QWEN_MODEL = "qwen3.5-plus"

# 每日主题池
TOPIC_POOLS = {
    0: ["周一综合症：为什么每个周一都不想起床", "重启：电脑重启能解决90%问题人却不行", "周一的咖啡和周五的咖啡有什么不同", "每一个周一都是一次假装重新开始"],
    1: ["外卖小哥的时速我们是不是都被困在倒计时里", "凌晨两点的便利店谁还在", "便利店的关东煮比米其林治愈", "电梯里的沉默一栋楼的人谁也不认识谁"],
    2: ["一周过半你还在坚持上周的决定吗", "收藏100篇文章读了0篇这是什么病", "日历写满待办但没一件是自己想做的", "周三了周末计划是不是又泡汤了"],
    3: ["朋友圈里过得最好的人私下是什么样", "多久没跟一个老朋友聊过天了", "已读不回现代社交最体面的冷暴力", "群聊里的沉默比吵架更难受"],
    4: ["周五下午三点的空气为什么闻起来不一样", "终于周五了这句话说了多少年", "周五晚上的酒喝的不是酒是自由", "周末计划从充满期待到睡到中午"],
    5: ["断网24小时会发生什么", "一个人待着的时候你都在干什么", "厨房里一个人的晚餐", "周末醒得比工作日还早这是什么体质"],
    6: ["周日晚上睡不着的人在怕什么", "发呆算不算一种能力", "给下周写一封信你会说什么", "周日黄昏一周里最诚实的时刻"],
}

# 核心系统prompt（所有风格共用）
SYSTEM_PROMPT = """你是一个写生活随笔的作家。你的文章必须有内核——读完能让读者沉默三秒，或者会心一笑。

铁律（违反任何一条就是失败）：
1. 标题承诺必须兑现——标题说"断网24小时"，正文就必须围绕断网展开，不能跑题写一堆不相关的场景
2. 必须有叙事线——文章要有推进感，不能是零散画面的随机堆砌。可以是：一个事件的发展、一种情绪的变化、一个发现的过程、一个悬念的揭晓
3. 细节必须为主题服务——每个场景、每句描写都要跟主题有关系。不相关的精彩画面也删掉
4. 绝对禁止说教——不要给建议、不要总结、不要"让我们一起"
5. 绝对禁止升华——不要在结尾给人生哲理、不要反问句结尾
6. 绝对禁止空洞——不要"在这个时代"、不要"也许"、"或许"堆砌
7. 结尾要有余韵——不是突然断掉，也不是总结陈词。像电影最后一个镜头，画面停了但意思还在
8. 情绪通过细节传递，不直说——不要写"我觉得""我想""这让我意识到"
9. 具体比抽象好——"7-11的关东煮"比"便利店的食物"好
10. 文章要有一个核心感受——读完之后读者心里留下一种情绪，而不是"看了很多画面但不知道想说什么"""

# 写作风格池
STYLE_POOLS = [
    {
        "name": "冷吐槽",
        "prompt": """风格：毒舌脱口秀，短句吐槽，一句接一句。具体到人名地名。只吐槽不给答案。但吐槽必须围绕主题，不能东一句西一句。

结构：从主题出发，吐槽层层递进（表面现象→荒谬之处→冷不丁一句扎心的），不是随机罗列。

参考：
「闹钟设了六个，6:00到6:25每五分钟一个。全响了，全关了。最后一个响的时候想请假。真的请了。理由：身体不适。翻译：床太舒服。」

写600字。""",
    },
    {
        "name": "白描",
        "prompt": """风格：抓住有意味的瞬间，跳过没有的。短句，白描，不要形容词堆砌。

⚠️ 白描≠画面堆砌！
烂白描：便利店烤肠、地铁口招牌、客厅挂钟——三个画面零关联，读完不知道想说什么
好白描：一个人在便利店等微波炉便当加热，1分30秒，看着转盘转了三圈——这是孤独

必须有叙事推进：场景之间要有关系，要么是时间的推进，要么是情绪的递进，要么是因果。不能是随机抓拍拼一起。
写600字。""",
    },
    {
        "name": "碎碎念",
        "prompt": """风格：深夜自言自语。一句一段，短的几个字，长的不超20字。跳跃，不照顾逻辑，不解释。

但碎碎念不是胡言乱语——表面散，底下有一条情绪线牵着。所有碎片都指向同一个感受，只是角度不同。

参考：
「咖啡。凉了。微波炉30秒。又凉了。算了。」「窗外有猫叫。不知道谁家的。」

写600字。""",
    },
    {
        "name": "内心戏",
        "prompt": """风格：对"你"说话。过去的自己、走了的人、一切想说的对象。私密、口语、可以跑题。

但必须围绕主题展开——"你"和主题有什么关系？为什么是现在想起"你"？这个要清楚。

参考：
「你还记得那时候说好的吗。我忘了。」「你走之后我买了好多东西。都不用。」

写600字。""",
    },
    {
        "name": "清单体",
        "prompt": """风格：脑子里的清单，不是待办。序号开头，每项不超30字。不分类，想起什么写什么。

清单要有推进感——从1到N不是随机的，读下来能感觉到某种情绪或想法在变化。可能是越写越认真，也可能是越写越跑偏但跑偏本身就很有意思。

参考：
「1. 今天忘了吃早餐 2. 昨天也没吃 3. 好像最近都没吃 4. 该买面包 5. 上次买的发霉了」

写600字。""",
    },
    {
        "name": "微型小说",
        "prompt": """风格：生活切片。有人物场景动作。不写"她想"，写她做了什么。细节具体。

必须有故事弧线——起因、经过、结果（或没有结果的悬停）。不是只写一个静态场景。

参考：
「他拿了两罐啤酒。左一罐右一罐。放回去。又拿。又放。最后都没买。」

写600字。""",
    },
    {
        "name": "城市漫游",
        "prompt": """风格：城市里抓拍。便利店、地铁口、街角、招牌、雨后的地面。不写"我看到"，直接写画面。

⚠️ 城市漫游≠随机街拍合集！
烂城市漫游：写6个不相关的城市画面拼一起，没有主题
好城市漫游：所有画面都围绕主题，画面之间有呼应或对比，读完有整体感受

必须是主题驱动的城市观察——标题说什么，你的镜头就找什么。
写600字。""",
    },
    {
        "name": "假装开头",
        "prompt": """风格：每段像文章开头，但都不继续。一段一两句话就换。不同角度但有内在情绪线。

所有开头都围绕同一个主题，像从不同门走进同一个房间。不是从10个不同房间各看一眼。

参考：
「有一次我在凌晨三点的街上走...」「说到跑步，我从没坚持过超过三天...」「其实昨天本来想说一件事...」

写600字。""",
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


def generate_article_with_ai(topic, style):
    """调用通义千问生成文章"""
    prompt = f"""主题：{topic}

{style['prompt']}

输出HTML格式：用<p>分段，<strong>加粗关键短语（少用）。不要写标题，只输出正文。"""

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
                    {"role": "system", "content": SYSTEM_PROMPT},
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
                log(f"✅ 生成成功 风格={style['name']} 字数={len(content)}")
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

    # 8点文章只加AI标识
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
