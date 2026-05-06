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
import subprocess

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
        "author": "生活与简单",
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
            "title": "闲聊易经｜02源流：八卦从哪来，易经怎么变成今天这样",
            "digest": "伏羲画卦、文王演卦、孔子作传，跨越千年的思想沉积层。",
            "prompt": "ancient Chinese sage drawing trigrams on turtle shell, oracle bones, bamboo scrolls, Shang dynasty bronze artifacts, historical atmosphere warm tones",
            "file": "/root/.openclaw/workspace/articles/yijing/02_源流.md"
        },
        3: {
            "title": "闲聊易经｜03阴阳：世界的基本密码",
            "digest": "阴阳不是玄学，是古人对世界最基本的观察。",
            "prompt": "yin yang symbol in nature, moon and sun, day and night, Chinese traditional painting, flowing water, mountains, harmonious balance",
            "file": "/root/.openclaw/workspace/articles/yijing/03_阴阳.md"
        },
        4: {
            "title": "闲聊易经｜04八卦：万物的八种状态",
            "digest": "天、地、雷、风、水、火、山、泽，世界就这八种东西。",
            "prompt": "eight trigrams bagua arranged in circle, traditional Chinese ink painting, natural elements water fire mountain wind, ancient scroll style",
            "file": "/root/.openclaw/workspace/articles/yijing/04_八卦.md"
        },
        5: {
            "title": "闲聊易经｜05入门：怎么读懂一卦",
            "digest": "卦象不是画符，有固定的阅读方法。",
            "prompt": "Chinese scholar studying ancient text, brush and ink, bamboo slips with hexagram diagrams, quiet study room, warm lamp",
            "file": "/root/.openclaw/workspace/articles/yijing/05_入门.md"
        },
        6: {
            "title": "闲聊易经｜06乾卦：一条龙的六个人生阶段",
            "digest": "乾卦用一条龙从出生到飞天的故事，讲了人生六个阶段。",
            "prompt": "Chinese dragon flying through clouds, six stages from deep water to heaven, traditional ink painting style, golden sunlight breaking through clouds, majestic and powerful",
            "file": "/root/.openclaw/workspace/articles/yijing/06_乾卦.md"
        },
        7: {
            "title": "闲聊易经｜07坤卦：大地从不争，但它承载了一切",
            "digest": "坤卦是乾卦的另一面，教的是承载、预判、格局和不争的智慧。",
            "prompt": "vast Chinese landscape painting, endless earth and mountains, golden soil, flowing rivers, ancient temple in distance, peaceful dawn light, grand and serene atmosphere",
            "file": "/root/.openclaw/workspace/articles/yijing/07_坤卦.md"
        },
        8: {
            "title": "闲聊易经｜08屯卦：万事开头难，但开了头就好走",
            "digest": "屯卦讲的是动弹不得——万事开头难是正常的，不是你不行。",
            "prompt": "young sprout pushing through dark soil, thunder rumbling under water, struggle and hope, Chinese ink painting style, dawn light breaking darkness",
            "file": "/root/.openclaw/workspace/articles/yijing/08_屯卦.md"
        },
    }
    return chapters.get(num)

# ======================== 64卦完整配置 ========================
# 覆盖全部64卦：name=卦名, title=副标题, symbol=卦象符号,
# prompt=封面图描述, theme=主题关键词, digest=摘要
HEXAGRAMS = {
    1:  {"name":"开篇", "title":"不是算命，是看变化的方法论", "symbol":"☰", "prompt":"ancient Chinese I Ching book open on wooden table, warm candlelight, bamboo slips, yin yang symbol, peaceful zen atmosphere", "theme":"概论"},
    2:  {"name":"源流", "title":"八卦从哪来，易经怎么变成今天这样", "symbol":"☵", "prompt":"ancient Chinese sage drawing trigrams on turtle shell, oracle bones, bamboo scrolls, Shang dynasty bronze artifacts, historical atmosphere warm tones", "theme":"概论"},
    3:  {"name":"阴阳", "title":"世界的基本密码", "symbol":"☯", "prompt":"yin yang symbol in nature, moon and sun, day and night, Chinese traditional painting, flowing water, mountains, harmonious balance", "theme":"概论"},
    4:  {"name":"八卦", "title":"万物的八种状态", "symbol":"☰", "prompt":"eight trigrams bagua arranged in circle, traditional Chinese ink painting, natural elements water fire mountain wind, ancient scroll style", "theme":"概论"},
    5:  {"name":"入门", "title":"怎么读懂一卦", "symbol":"☰", "prompt":"Chinese scholar studying ancient text, brush and ink, bamboo slips with hexagram diagrams, quiet study room, warm lamp", "theme":"概论"},
    6:  {"name":"乾", "title":"一条龙的六个人生阶段", "symbol":"☰", "prompt":"Chinese dragon flying through clouds, six stages from deep water to heaven, traditional ink painting style, golden sunlight breaking through clouds, majestic and powerful", "theme":"自强不息"},
    7:  {"name":"坤", "title":"大地从不争，但它承载了一切", "symbol":"☷", "prompt":"vast Chinese landscape painting, endless earth and mountains, golden soil, flowing rivers, ancient temple in distance, peaceful dawn light, grand and serene atmosphere", "theme":"厚德载物"},
    8:  {"name":"屯", "title":"万事开头难，但开了头就好走", "symbol":"☵", "prompt":"young sprout pushing through dark soil, thunder rumbling under water, struggle and hope, Chinese ink painting style, dawn light breaking darkness", "theme":"初创"},
    9:  {"name":"蒙", "title":"人一辈子都在学习，问题是学什么", "symbol":"☶", "prompt":"Chinese mountain spring emerging from rocks, ancient sage teaching young student under pine tree, misty mountains, calligraphy scrolls, serene learning atmosphere", "theme":"启蒙"},
    10: {"name":"需", "title":"该等的时候别急，急了反而坏事", "symbol":"☰", "prompt":"traveler waiting by river crossing, rain clouds gathering, ancient Chinese landscape with bridge, patience and timing, ink wash painting style", "theme":"等待"},
    11: {"name":"讼", "title":"能不打官司就不打，赢了也是输", "symbol":"☵", "prompt":"two Chinese scholars arguing before a judge, ancient court scene, bamboo legal scrolls, tense but resolvable atmosphere, traditional painting style", "theme":"争端"},
    12: {"name":"师", "title":"带队伍不是靠吼，是靠规矩", "symbol":"☵", "prompt":"ancient Chinese general leading disciplined army, military tents on plains, banners flowing, dawn light, strategic mountains in background, historical epic atmosphere", "theme":"带团队"},
    13: {"name":"比", "title":"选对人站对队，比什么都重要", "symbol":"☷", "prompt":"group of Chinese scholars gathered in harmony under old tree, friendship and alliance, traditional ink painting, warm golden light, peaceful gathering", "theme":"合作"},
    14: {"name":"小畜", "title":"力量不够的时候，先蓄着", "symbol":"☰", "prompt":"gentle rain nurturing small garden, wind carrying seeds, patient growth, Chinese ink painting of countryside, spring mist, subtle power of accumulation", "theme":"蓄势"},
    15: {"name":"履", "title":"在老虎尾巴上走路——不是找死，是技巧", "symbol":"☰", "prompt":"Chinese scholar walking carefully on narrow mountain path, tiger watching calmly nearby, balance and composure, misty peaks, traditional ink wash painting", "theme":"谨慎"},
    16: {"name":"泰", "title":"为什么天地不通的时候反而最和谐", "symbol":"☷", "prompt":"sunrise over peaceful Chinese valley, heaven and earth in harmony, golden light streaming through clouds, idyllic landscape, perfect balance between forces, serene dawn", "theme":"通达"},
    17: {"name":"否", "title":"通道堵了别硬冲，先想想为什么", "symbol":"☰", "prompt":"barren Chinese landscape with blocked mountain pass, dark clouds parting to reveal small light, patience through adversity, ink wash painting, stark contrast", "theme":"闭塞"},
    18: {"name":"同人", "title":"找到志同道合的人，事半功倍", "symbol":"☰", "prompt":"diverse group of ancient Chinese scholars sharing ideas around fire, unity in diversity, open field under stars, warm communal atmosphere, traditional painting style", "theme":"团结"},
    19: {"name":"大有", "title":"拥有很多的时候，才是最危险的时候", "symbol":"☰", "prompt":"abundant harvest festival in ancient China, golden grain fields, overflowing bowls, celebration but with underlying caution, rich warm tones, traditional style", "theme":"丰盛"},
    20: {"name":"谦", "title":"易经唯一的六爻皆吉卦——低调才是最高境界", "symbol":"☷", "prompt":"modest Chinese sage standing beside mountain, small figure against grand landscape, humility and greatness, traditional ink painting, misty peaks, zen atmosphere", "theme":"谦虚"},
    21: {"name":"豫", "title":"乐极生悲不是危言耸听，是规律", "symbol":"☳", "prompt":"ancient Chinese musician playing instrument at grand banquet, celebration scene, but with subtle warning clouds on horizon, festive but reflective atmosphere, traditional painting", "theme":"欢乐"},
    22: {"name":"随", "title":"跟着趋势走，比逆流而上聪明", "symbol":"☱", "prompt":"willow tree bending with wind by Chinese lake, flowing river following natural course, adaptation and going with flow, ink wash painting, peaceful natural scene", "theme":"随顺"},
    23: {"name":"蛊", "title":"坏了的东西要修，不能拖", "symbol":"☶", "prompt":"ancient Chinese artisan repairing damaged bronze vessel, tools and materials scattered, restoration work, warm workshop light, meticulous craftsmanship, traditional painting style", "theme":"修缮"},
    24: {"name":"复", "title":"跌到谷底不是结束，是重新开始", "symbol":"☷", "prompt":"first green shoot emerging in winter snow, spring returning after harsh cold, Chinese landscape with snow melting, hope and renewal, ink wash painting, dawn light", "theme":"回归"},
    25: {"name":"无妄", "title":"不设期望，反而得到最好的结果", "symbol":"☰", "prompt":"clear open sky over empty Chinese courtyard, unexpected blessings in simplicity, no artifice no calculation, pure tranquil atmosphere, traditional ink painting, clarity", "theme":"真实"},
    26: {"name":"大畜", "title":"格局打开，装下更多东西", "symbol":"☶", "prompt":"vast Chinese mountain landscape with deep valleys, great capacity and accumulation, scholar on cliff overlooking grand scenery, traditional ink painting, epic scale, golden clouds", "theme":"大蓄势"},
    27: {"name":"颐", "title":"管住嘴，养好身，这是最大的自律", "symbol":"☶", "prompt":"ancient Chinese tea ceremony, nourishment of body and mind, careful eating and speaking, serene room with bamboo, traditional painting, mindful atmosphere", "theme":"养生"},
    28: {"name":"大过", "title":"压力太大的时候，要么扛住要么弯腰", "symbol":"☴", "prompt":"ancient Chinese bridge under tremendous weight, bending but not breaking, extreme pressure testing structure, dramatic landscape, ink wash painting, tension and resilience", "theme":"过度"},
    29: {"name":"坎", "title":"水往低处流，但低谷不是终点", "symbol":"☵", "prompt":"deep water canyon with waterfalls, Chinese landscape painting, danger and beauty coexisting, flowing water finding way through obstacles, misty deep gorge", "theme":"险难"},
    30: {"name":"离", "title":"依附不是软弱，是智慧", "symbol":"☲", "prompt":"brilliant fire and light in Chinese lantern festival, illumination and attachment, warmth spreading, vibrant red and gold, traditional Chinese festival atmosphere, clarity and brightness", "theme":"光明"},
    31: {"name":"咸", "title":"真正的影响力，不是靠权力", "symbol":"☱", "prompt":"two Chinese sages in silent understanding on mountain, mutual influence without words, telepathic connection, misty peaks, traditional ink painting, subtle emotional atmosphere", "theme":"感应"},
    32: {"name":"恒", "title":"最厉害的人，是能一直坚持的人", "symbol":"☳", "prompt":"ancient Chinese pagoda standing firm through seasons, spring summer autumn winter around it, enduring through time, traditional painting, constant yet changing, timeless atmosphere", "theme":"持久"},
    33: {"name":"遯", "title":"该退的时候就退，退一步海阔天空", "symbol":"☶", "prompt":"Chinese sage walking away into misty mountains, noble retreat, leaving worldly affairs behind, peaceful mountain path, traditional ink painting, serene departure", "theme":"退避"},
    34: {"name":"大壮", "title":"力量太大的时候，最容易犯傻", "symbol":"☳", "prompt":"powerful Chinese warhorse restrained by thin rope, great strength needing control, muscular energy contained, dramatic ink wash painting, tension between power and wisdom", "theme":"壮盛"},
    35: {"name":"晋", "title":"往上走的时候别飘，飘了就掉", "symbol":"☰", "prompt":"sunrise illuminating Chinese landscape, advancement and progress, bright morning over imperial city, golden light ascending, traditional painting, hopeful upward energy", "theme":"晋升"},
    36: {"name":"明夷", "title":"光芒被遮住了，但火还在烧", "symbol":"☷", "prompt":"sunset with glowing embers under ashes, Chinese landscape at dusk, light hidden but not extinguished, phoenix descending, traditional ink painting, subtle resilience in darkness", "theme":"光明受阻"},
    37: {"name":"家人", "title":"把家管好了，比什么都强", "symbol":"☴", "prompt":"traditional Chinese family scene in courtyard, harmony and order at home, ancient household with children studying, warm lamp light, loving disciplined atmosphere, traditional painting", "theme":"齐家"},
    38: {"name":"睽", "title":"看法不一样不是坏事，是对坏事", "symbol":"☲", "prompt":"two paths diverging in Chinese mountain landscape, opposite viewpoints looking at same thing, fire and lake elements, reconciling differences, ink wash painting, thoughtful atmosphere", "theme":"对立"},
    39: {"name":"蹇", "title":"路不通的时候，别硬走", "symbol":"☵", "prompt":"traveler facing blocked mountain path in Chinese landscape, water and mountain obstacles, stopping to reassess, misty peaks, traditional ink painting, contemplative pause", "theme":"困难"},
    40: {"name":"解", "title":"困难解开了，但别急着庆祝", "symbol":"☳", "prompt":"frozen Chinese river beginning to thaw, thunder and rain releasing tension, liberation and relief, spring melting, traditional ink painting, dynamic movement and release", "theme":"解脱"},
    41: {"name":"损", "title":"减法比加法更难，但也更重要", "symbol":"☶", "prompt":"Chinese scholar pruning bonsai tree on mountain, art of subtraction, less is more, careful trimming, traditional ink painting, mindful reduction, quiet mountain garden", "theme":"减损"},
    42: {"name":"益", "title":"帮助别人就是帮助自己", "symbol":"☳", "prompt":"rain falling on Chinese farmland, nourishing crops and village, wind bringing seeds, mutual benefit and growth, spring landscape, traditional painting, generous abundant atmosphere", "theme":"增益"},
    43: {"name":"夬", "title":"该决断的时候别犹豫，犹豫就是错", "symbol":"☰", "prompt":"Chinese warrior making decisive strike with sword, breaking through barrier, rain and heaven energy, determination and action, dramatic ink painting, powerful moment of decision", "theme":"决断"},
    44: {"name":"姤", "title":"突然出现的机会，可能是馅饼也可能是陷阱", "symbol":"☴", "prompt":"mysterious woman appearing at Chinese festival, unexpected encounter, wind beneath heaven, chance meeting with deep implications, traditional painting, enigmatic atmosphere", "theme":"邂逅"},
    45: {"name":"萃", "title":"人聚在一起，是力量也是风险", "symbol":"☷", "prompt":"grand gathering of Chinese scholars at ancient academy, assembly and convergence, joyful meeting but with underlying caution, traditional painting, communal learning atmosphere", "theme":"聚集"},
    46: {"name":"升", "title":"一步一步往上走，别想一步登天", "symbol":"☷", "prompt":"Chinese pagoda being built level by level, gradual ascent, trees growing on mountain, patient upward progress, traditional ink painting, steady constructive growth", "theme":"上升"},
    47: {"name":"困", "title":"困住了不是等死，是修炼", "symbol":"☱", "prompt":"noble Chinese scholar in confined space, patient endurance in adversity, ancient prison cell with single window of light, water pond drying, traditional painting, dignified patience", "theme":"困境"},
    48: {"name":"井", "title":"最好的资源，是最不起眼的", "symbol":"☵", "prompt":"ancient Chinese well in village center, clear water drawn by rope, enduring resource serving all generations, wind over water, traditional painting, reliable essential resource", "theme":"滋养"},
    49: {"name":"革", "title":"该变的时候不变，比变更危险", "symbol":"☲", "prompt":"Chinese revolutionary fire transforming old palace, dramatic change and reform, burning away the old, phoenix of transformation, traditional painting with dynamic fire and energy", "theme":"变革"},
    50: {"name":"鼎", "title":"真正值钱的东西，是能装东西的容器", "symbol":"☲", "prompt":"magnificent ancient Chinese bronze ding tripod vessel, symbol of state power and civilization, fire transforming contents, imperial palace setting, golden ceremonial light, traditional painting", "theme":"立业"},
    51: {"name":"震", "title":"雷声大的时候别慌，慌了才真出事", "symbol":"☳", "prompt":"thunder striking mountain peak in Chinese landscape, lightning illuminating ancient temple, shock and awakening, dramatic ink painting, powerful energy releasing, nature at full force", "theme":"震动"},
    52: {"name":"艮", "title":"知道什么时候停下来，比知道什么时候走更重要", "symbol":"☶", "prompt":"Chinese sage meditating still on mountain peak, absolute stillness and contemplation, mountain standing firm, traditional ink painting, zen mountain meditation, profound silence", "theme":"静止"},
    53: {"name":"渐", "title":"慢就是快，急就是慢", "symbol":"☴", "prompt":"wild goose landing gracefully on Chinese lake shore, gradual progression, step by step approach, trees growing on mountain, patient traditional landscape painting, gentle advancement", "theme":"渐进"},
    54: {"name":"归妹", "title":"走别人的路要小心，那不是你的路", "symbol":"☱", "prompt":"Chinese bride's journey to new home, thunder over lake, transition and proper conduct, traditional wedding scene with cautionary undertone, ancient Chinese painting, thoughtful journey", "theme":"归宿"},
    55: {"name":"丰", "title":"到巅峰的时候，就要开始往下看了", "symbol":"☲", "prompt":"abundant harvest festival under full sun in ancient China, peak prosperity with approaching sunset, thunder and lightning, maximum achievement, rich traditional painting with dramatic light", "theme":"丰盛极致"},
    56: {"name":"旅", "title":"出门在外，低调是最好的保护色", "symbol":"☲", "prompt":"Chinese traveler resting at mountain inn, fire on mountain, journey and transition, foreign land with cautious optimism, traditional ink painting, contemplative travel scene", "theme":"旅途"},
    57: {"name":"巽", "title":"真正的柔，是像风一样无孔不入", "symbol":"☴", "prompt":"gentle wind flowing through Chinese bamboo forest, penetrating without force, wood and wind elements, subtle pervasive influence, traditional ink painting, flowing graceful movement", "theme":"柔顺"},
    58: {"name":"兑", "title":"会说话的人，运气不会太差", "symbol":"☱", "prompt":"Chinese scholars joyfully conversing by lake, pleasant exchange and harmony, water meeting water, warm sunset, traditional painting, convivial intellectual atmosphere, genuine communication", "theme":"喜悦"},
    59: {"name":"涣", "title":"散了不一定是坏事，旧的不去新的不来", "symbol":"☴", "prompt":"ice melting and dispersing in Chinese river, wind over water, dissolution and liberation, blocks breaking apart, traditional ink painting, refreshing transformation, flowing movement", "theme":"涣散"},
    60: {"name":"节", "title":"没有边界的自由不是自由，是灾难", "symbol":"☵", "prompt":"regulated water flowing through Chinese canal system, proper boundaries and limits, ancient water management, controlled yet flowing, traditional painting, balanced restraint", "theme":"节制"},
    61: {"name":"中孚", "title":"信任这个东西，建立很难毁掉很快", "symbol":"☴", "prompt":"gentle wind over peaceful Chinese lake, inner truth and sincerity, two hearts connecting, traditional ink painting, tranquil reflective water surface, genuine atmosphere", "theme":"诚信"},
    62: {"name":"小过", "title":"小事情做好，比大事情做一半强", "symbol":"☳", "prompt":"small birds flying over Chinese mountain pass, modest actions and attention to detail, thunder on mountain, careful small steps, traditional ink painting, humble understated beauty", "theme":"小过"},
    63: {"name":"既济", "title":"完成了不代表结束了，守业更难", "symbol":"☵", "prompt":"successful ancient Chinese river crossing, celebration on far shore, water and fire in balance, achievement reached but caution needed, traditional painting, accomplished yet vigilant atmosphere", "theme":"完成"},
    64: {"name":"未济", "title":"没有完成，恰恰是最好的状态", "symbol":"☲", "prompt":"boat preparing to cross vast Chinese river at dawn, journey not yet complete, fire over water, anticipation and potential, traditional ink painting, hopeful beginning atmosphere, unlimited possibility", "theme":"未完成"},
}


def get_chapter_file(num):
    """返回章节对应的Markdown文件路径"""
    hx = HEXAGRAMS.get(num)
    if hx:
        return f"/root/.openclaw/workspace/articles/yijing/{num:02d}_{hx['name']}.md"
    return None


def get_chapter_info(num):
    """获取章节信息，兼容旧字典和新HEXAGRAMS"""
    # 旧字典里有更完整的title/digest/prompt/file配置，优先用
    old = get_chapter(num)
    if old:
        return old
    # 否则从HEXAGRAMS构造
    hx = HEXAGRAMS.get(num)
    if not hx:
        return None
    name = hx["name"]
    title = hx["title"]
    return {
        "title": f"闲聊易经｜{num:02d}{name}卦：{title}",
        "digest": f"易经第{num}章{name}卦——{title}",
        "prompt": hx["prompt"],
        "file": f"/root/.openclaw/workspace/articles/yijing/{num:02d}_{name}.md",
        "name": name,
    }


def md_to_html(content):
    """将Markdown内容转换为HTML"""
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
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html_lines.append(f'<p>{line}</p>')
    return '\n'.join(html_lines)


def generate_chapter_content(num, file_path):
    """调用openclaw agent自动生成章节内容"""
    hx = HEXAGRAMS.get(num)
    if not hx:
        log(f"❌ HEXAGRAMS中没有第{num}卦的配置")
        return False

    name = hx["name"]
    title = hx["title"]
    theme = hx["theme"]

    message = (
        f"请撰写易经系列第{num}章「{name}卦」的文章，保存到 {file_path}。\n\n"
        f"要求：\n"
        f"1. 标题格式：闲聊易经｜{num:02d}{name}卦：{title}\n"
        f"2. 参考 /root/.openclaw/workspace/articles/yijing/07_坤卦.md 的风格和结构，用同样口语化、有见解的写作方式\n"
        f"3. 文章结构：开篇引入→卦象解析→卦辞解读→象传→六爻解读（初爻到上爻逐一讲解，每爻有核心观点和生活应用）→总结升华\n"
        f"4. 核心主题：{theme}\n"
        f"5. 每个部分要有独到见解，结合现代生活场景，不要只是翻译古文\n"
        f"6. 结尾加「以上均为个人观点，如有错误的地方，还请海涵。」\n"
        f"7. 结尾加「【本文由AI生成，经人工审核修改】」\n"
        f"8. 不要预告下一篇\n"
        f"9. 直接写入文件，不需要确认"
    )

    cmd = [
        "openclaw", "agent",
        "--agent", "main",
        "--message", message,
        "--timeout", "300",
    ]

    log(f"🤖 开始生成第{num}章「{name}卦」内容...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=320)
        if result.returncode == 0:
            log(f"✅ 第{num}章内容生成完成")
            if os.path.exists(file_path):
                log(f"   文件已保存: {file_path} ({os.path.getsize(file_path)} bytes)")
                return True
            else:
                log(f"⚠️ 生成命令成功但文件未创建: {file_path}")
                return False
        else:
            log(f"❌ 生成失败 (exit={result.returncode}): {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"❌ 生成超时（320秒）")
        return False
    except Exception as e:
        log(f"❌ 生成异常: {e}")
        return False


def main():
    log("=== 易经全解系列发布 ===")

    state = load_state()
    chapter_num = state.get("chapter", 1)

    if chapter_num > 64:
        log("🎉 全部64章已发布完毕！")
        return

    # 检查是否今天已经发布过
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    for pub in state.get("published", []):
        if pub.get("date") == today:
            log(f"⚠️ 今天已发布第{pub['num']}章，跳过重复发布")
            return

    # 获取章节信息（兼容旧字典和新HEXAGRAMS）
    chapter = get_chapter_info(chapter_num)

    if not chapter:
        log(f"❌ 第{chapter_num}章无配置，跳过")
        return

    file_path = chapter["file"]

    # 如果文件不存在，自动生成
    if not os.path.exists(file_path):
        log(f"📄 章节文件不存在: {file_path}")
        generated = generate_chapter_content(chapter_num, file_path)
        if not generated:
            log(f"❌ 内容生成失败，明天再试")
            return

    # 读取文件内容
    if not os.path.exists(file_path):
        log(f"❌ 章节文件仍不存在: {file_path}，退出")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    html_content = md_to_html(content)

    # 获取token
    token = get_token()
    if not token:
        log("❌ token获取失败")
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
        # 移除今天可能存在的重复记录（以防万一）
        state["published"] = [p for p in state.get("published", []) if p.get("date") != today]
        state["published"].append({
            "num": chapter_num,
            "title": chapter["title"],
            "date": today,
            "media_id": draft_id
        })
        save_state(state)
        log(f"   下一章: 第{chapter_num + 1}章")
    else:
        log("❌ 提交失败")

    log("=== 发布结束 ===")

if __name__ == "__main__":
    main()
