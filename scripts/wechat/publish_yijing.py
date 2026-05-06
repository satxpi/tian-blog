#!/usr/bin/env python3
"""发布易经文章到草稿箱，读取预生成的markdown文件"""
import requests, json, time, re, os, sys

APPID = "wx4d76a79c84e3ebbc"
SECRET = "72d4248a0d0384384884116ff2470e06"

def md_to_html(text):
    """markdown转HTML，保留code block"""
    html = text
    # 处理code block
    code_blocks = []
    def save_code(m):
        code_blocks.append('<pre><code>' + m.group(1) + '</code></pre>')
        return f'__CODE_BLOCK_{len(code_blocks)-1}__'
    html = re.sub(r'```(.+?)```', save_code, html, flags=re.S)
    
    # 标题
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.M)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.M)
    # 加粗
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # 斜体
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # 列表
    html = re.sub(r'^(\d+)\. (.+)$', r'<p>\1. \2</p>', html, flags=re.M)
    # 分隔线
    html = re.sub(r'^---$', '<hr>', html, flags=re.M)
    # 段落（双换行）
    parts = html.split('\n\n')
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith('<h') or part.startswith('<pre') or part.startswith('<hr') or part.startswith('__CODE'):
            result.append(part)
        else:
            result.append(f'<p>{part}</p>')
    html = '\n'.join(result)
    # 还原code block
    for i, block in enumerate(code_blocks):
        html = html.replace(f'<p>__CODE_BLOCK_{i}__</p>', block)
        html = html.replace(f'__CODE_BLOCK_{i}__', block)
    return html

def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else "/root/.openclaw/workspace/articles/yijing/10_需.md"
    
    token = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}").json()['access_token']
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.strip().split('\n')
    title = lines[0].replace('# ', '').strip()
    content = '\n'.join(lines[1:])
    html = md_to_html(content)
    
    # AI标识只加一次
    html += '\n<p style="color:#999;font-size:12px;margin-top:30px;">本文由AI生成，经人工审核修改</p>'
    
    # 封面
    prompt = "ancient Chinese I Ching, traditional ink painting, zen atmosphere, warm tones"
    encoded = requests.utils.quote(prompt)
    seed = int(time.time())
    img_path = f"/tmp/yijing_cover_{seed}.jpg"
    r = requests.get(f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=768&nologo=true&seed={seed}", timeout=120)
    if r.status_code == 200 and len(r.content) > 1000:
        with open(img_path, 'wb') as f:
            f.write(r.content)
        with open(img_path, 'rb') as f:
            r = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image", files={'media': ('cover.jpg', f, 'image/jpeg')}).json()
        if 'media_id' not in r:
            print(f"封面上传失败: {r}")
            return
    else:
        print("封面生成失败")
        return
    
    article = {
        "title": title,
        "author": "生活与简单",
        "content": html,
        "digest": content[:120].replace('<', '').replace('>', ''),
        "thumb_media_id": r['media_id'],
        "show_cover_pic": 1
    }
    r = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
        data=json.dumps({"articles": [article]}, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'}
    ).json()
    
    if 'media_id' in r:
        print(f"OK: {title} | media_id: {r['media_id']}")
    else:
        print(f"FAIL: {r}")

if __name__ == "__main__":
    main()
