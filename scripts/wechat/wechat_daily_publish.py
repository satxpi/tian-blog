#!/usr/bin/env python3
"""
微信公众号每日自动发布脚本
用AI实时生成文章，每篇都不一样

用法: python3 wechat_daily_publish.py
定时任务: 0 8 * * * python3 /root/.openclaw/workspace/scripts/wechat/wechat_daily_publish.py >> /tmp/wechat_daily.log 2>&1
"""

import requests
import json
import datetime
import os
import sys
import fcntl

# 配置
APPID = "wx4d76a79c84e3ebbc"
SECRET = "72d4248a0d0384384884116ff2470e06"
LOG_FILE = "/tmp/wechat_daily.log"
LOCK_FILE = "/tmp/wechat_daily_publish.lock"
ARCHIVE_DIR = "/root/.openclaw/workspace/articles/daily"

# 每日主题池（按星期分组，每次随机选一个）
TOPIC_POOLS = {
    0: [  # 周一 - 新开始/重启
        "周一综合症：为什么每个周一都不想起床",
        "新的一周，你最想改变的一件事是什么",
        "周一的地铁比平时更挤，我们在赶什么",
        "重启：为什么电脑重启能解决90%的问题，人却不行",
        "周一的咖啡，和周五的咖啡有什么不同",
    ],
    1: [  # 周二 - 日常观察
        "外卖小哥的时速：我们是不是都被困在倒计时里",
        "凌晨两点的便利店，谁还在",
        "手机电量低于20%时的焦虑，和真正的焦虑有什么区别",
        "你在通勤路上想到过什么改变人生的念头",
        "为什么我们总在深夜做决定，早上又推翻",
    ],
    2: [  # 周三 - 反思/中点
        "一周过半，你还在坚持上周的决定吗",
        "效率悖论：工具越多，人越累",
        "我们用多少时间在做'准备工作'",
        "中年危机提前了：25岁就开始焦虑的人",
        "周三了，你的周末计划是不是又泡汤了",
    ],
    3: [  # 周四 - 人际/情感
        "朋友圈里过得最好的人，私下是什么样",
        "多久没跟一个老朋友聊过天了",
        "社交媒体上的'真实'，到底有多真实",
        "你上一次认真听别人说话是什么时候",
        "合群：是选择还是妥协",
    ],
    4: [  # 周五 - 释放/期待
        "周五下午三点的空气，为什么闻起来不一样",
        "周末自由：你真的自由吗",
        "从996到躺平，我们到底在选什么",
        "你的周末，是谁的周末",
        "终于周五了——这句话说了多少年",
    ],
    5: [  # 周六 - 生活/独处
        "断网24小时会发生什么",
        "一个人待着的时候，你都在干什么",
        "数字断舍离：删掉100个App之后",
        "厨房里一个人的晚餐",
        "书架上有多少书，是你永远不会读的",
    ],
    6: [  # 周日 - 放空/准备
        "周日晚上睡不着的人，在怕什么",
        "发呆算不算一种能力",
        "你有多久没有无聊过了",
        "慢：在这个所有人都赶时间的时代",
        "给下周写一封信，你会说什么",
    ],
}


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
        return lock_fd  # 保持文件描述符，锁在进程退出时自动释放
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
    """上传封面图，返回thumb_media_id"""
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
    """用pollination.ai生成封面图"""
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
    """创建草稿箱文章"""
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


def generate_article_with_ai(topic):
    """调用AI生成文章，返回 (title, content_html, image_prompt)"""
    # 使用简单的HTTP请求调用本地或远程AI API
    # 这里用一个轻量的方案：直接用prompt构建文章

    prompt = f"""你是一位生活随笔作家。请围绕主题「{topic}」写一篇微信公众号文章。

严格要求：
1. **风格**：像跟朋友聊天一样，自然、随意、有温度。不要说教，不要给建议，不要升华。
2. **结构**：不要分"开头-中间-结尾"这种模板。想到哪写到哪，像一条河自然流淌。
3. **语言**：短句为主，口语化，少用形容词。白描，不要抒情。像写日记一样。
4. **禁止**：
   - 禁止用"在这个...的时代"开头
   - 禁止用"也许/或许/大概"堆砌
   - 禁止用"让我们一起..."结尾
   - 禁止列出1/2/3点建议
   - 禁止强行升华或给人生哲理
   - 禁止用反问句结尾
5. **篇幅**：800-1200字
6. **HTML格式**：用<p>分段，<h2>做小标题（最多2个），<strong>加粗关键句
7. **结尾**：不要总结，不要展望，最末一句像聊天突然挂了电话一样收住

请直接输出HTML格式的文章内容，不要输出其他内容。"""

    # 尝试调用AI API生成
    # 方案1: 使用内置的简单模板+随机组合生成（不依赖外部API）
    # 方案2: 如果有可用的AI API，调用之

    # 先尝试通过Ollama本地生成
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.9, "top_p": 0.95}
            },
            timeout=300
        )
        if r.status_code == 200:
            result = r.json()
            content = result.get("response", "").strip()
            if content and len(content) > 200:
                log("✅ 使用Ollama本地AI生成文章")
                image_prompt = f"{topic}, warm atmosphere, daily life, natural lighting, contemplative mood"
                return topic, content, image_prompt
    except Exception as e:
        log(f"⚠️ Ollama不可用: {e}，使用内置生成")

    # 备用方案：基于主题的半随机文章生成
    return generate_fallback_article(topic)


def generate_fallback_article(topic):
    """备用方案：半随机文章生成，确保每篇不同"""
    import random

    # 开头素材库
    openings = [
        f"今天想聊聊{topic}这件事。",
        f"{topic}——说出来你可能觉得没什么，但我就是一直在想。",
        f"刚才在楼下买了杯咖啡，突然想到{topic}。",
        f"凌晨三点醒来，脑子里转的第一个念头居然是{topic}。",
        f"有人在群里讨论{topic}，我打了一大段话又删了。",
    ]

    # 中间段落素材（根据主题动态组合）
    middle_sections = [
        "<p>很多人觉得这是小事。但小事才是生活的全部。</p>",
        "<p>我们总是在大事上较真，小事上随便。可日子，就是由小事拼起来的。</p>",
        "<p>有时候不是问题本身有多难，是我们把它想复杂了。</p>",
        "<p>想明白一件事：你不需要解决所有问题。有些问题，放着放着就不再是问题了。</p>",
        "<p>很多人说要'活在当下'，但没人告诉你当下到底怎么活。</p>",
        "<p>小时候觉得大人的世界很复杂。长大了发现，复杂是他们自己搞出来的。</p>",
        "<p>手机亮了一下。又暗了。大概又是一条不重要的通知。</p>",
        "<p>楼下便利店的小哥换人了。旧的走了，新的来了，也没什么人注意。</p>",
        "<p>有些事说出来就显得矫情，不说又憋得慌。</p>",
        "<p>我们太习惯'应该'了。应该努力，应该上进，应该开心。谁规定的？</p>",
    ]

    # 结尾素材
    endings = [
        "<p>算了，不想了。</p>",
        "<p>写到这里突然不知道该说什么了。就这样吧。</p>",
        "<p>天快亮了。</p>",
        "<p>手机还有12%的电。</p>",
        "<p>咖啡凉了。</p>",
        "<p>窗外有人在遛狗。看起来挺自在的。</p>",
    ]

    random.seed(datetime.datetime.now().strftime('%Y%m%d'))  # 同一天生成相同结果

    # 组装文章
    opening = random.choice(openings)
    # 选4-6个中间段落
    n_middle = random.randint(4, 6)
    middles = random.sample(middle_sections, min(n_middle, len(middle_sections)))
    ending = random.choice(endings)

    # 构建HTML
    content_parts = [f"<p>{opening}</p>"]
    for m in middles:
        content_parts.append(m)
    content_parts.append(ending)

    content_html = "\n".join(content_parts)
    image_prompt = f"{topic}, warm atmosphere, daily life, natural lighting, contemplative mood"

    return topic, content_html, image_prompt


def save_archive(title, content):
    """归档文章到本地"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    filepath = os.path.join(ARCHIVE_DIR, f"{date_str}_{title[:20]}.md")
    # 去掉HTML标签做纯文本存档
    import re
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

    # 选择主题
    weekday = datetime.datetime.now().weekday()
    topics = TOPIC_POOLS.get(weekday, TOPIC_POOLS[0])
    # 用日期作为随机种子，同一天选同一个主题
    day_seed = int(datetime.datetime.now().strftime('%Y%m%d'))
    random.seed(day_seed)
    topic = random.choice(topics)
    log(f"今日主题: {topic}")

    # AI生成文章
    title, content, image_prompt = generate_article_with_ai(topic)
    log(f"文章标题: {title}")

    # 8点文章不加"以上均为个人观点"，只加AI标识
    date_str = datetime.datetime.now().strftime('%Y年%m月%d日')
    content += f"""<p>【本文由AI生成，经人工审核修改】<br/>生成时间：{date_str}</p>"""

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
    digest = content[:120].replace('<', '<').replace('>', '>').replace('\n', '')[:60]
    draft_id = create_draft(token, title, content, thumb_media_id, digest)

    if draft_id:
        log(f"✅ 草稿提交成功！media_id: {draft_id}")
        log(f"   标题: {title}")
        # 归档
        save_archive(title, content)
    else:
        log("❌ 草稿提交失败")
        sys.exit(1)

    log("=== 发布完成 ===")


if __name__ == "__main__":
    main()
