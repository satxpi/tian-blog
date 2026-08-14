#!/usr/bin/env python3
"""
wechat_draft_from_blog.py — 把当天博客文章发为公众号草稿

读 content/posts/*/YYYY-MM-DD-*.md (最新一篇) → markdown 转 HTML → 公众号 draft/add
用法: sudo python3 scripts/wechat_draft_from_blog.py [--date 2026-08-06]
"""
import os, sys, re, glob, argparse, time, html, json
import requests

APPID = "wx4d76a79c84e3ebbc"
SECRET = "72d4248a0d0384384884116ff2470e06"
BLOG_POSTS = '/data/tian-blog/tian-blog/content/posts'
AUTHOR = '生活与简单'

# markdown → 公众号 HTML (正规转换, 微信图文子集)
def md_to_html(md_text):
    import markdown as _md
    html = _md.markdown(md_text, extensions=['extra', 'sane_lists'])
    # 公众号适配: h1/h2 降为 h3 (微信正文标题不宜过大), 代码块转 pre
    html = html.replace('<h1>', '<h3 style="font-size:18px;font-weight:bold;">').replace('</h1>', '</h3>')
    html = html.replace('<h2>', '<h3 style="font-size:18px;font-weight:bold;">').replace('</h2>', '</h3>')
    html = html.replace('<h3>', '<h3 style="font-size:17px;font-weight:bold;">')
    html = html.replace('<blockquote>', '<blockquote style="border-left:3px solid #d9d9d9;padding-left:10px;color:#888;margin:10px 0;">')
    html = html.replace('<hr>', '<hr style="border:none;border-top:1px solid #eee;margin:15px 0;">')
    html = html.replace('<table>', '<table style="border-collapse:collapse;margin:10px 0;font-size:14px;">')
    html = html.replace('<th>', '<th style="border:1px solid #ddd;padding:6px 10px;background:#f5f5f5;">')
    html = html.replace('<td>', '<td style="border:1px solid #ddd;padding:6px 10px;">')
    html = html.replace('<img ', '<img style="max-width:100%;" ')
    return html


def parse_blog_md(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    # front matter
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    meta = {}
    body = text
    if m:
        for kv in m.group(1).split('\n'):
            if ':' in kv:
                k, v = kv.split(':', 1)
                meta[k.strip()] = v.strip().strip('"\'')
        body = text[m.end():]
    title = meta.get('title', os.path.basename(path).replace('.md', ''))
    return title, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    ap.add_argument('--file', default=None, help='指定文章文件路径(优先级高于--date)')
    a = ap.parse_args()

    if a.file:
        path = a.file
    else:
        target = a.date or time.strftime('%Y-%m-%d')
        files = sorted(glob.glob(os.path.join(BLOG_POSTS, '*', f'{target}-*.md')))
        if not files:
            print(f'❌ {target} 没有博客文章')
            return
        path = files[-1]  # 最新一篇
    title, body = parse_blog_md(path)
    print(f'📄 文章: {os.path.basename(path)}')
    print(f'   标题: {title}, 正文 {len(body)} 字符')

    # 转 HTML
    content_html = md_to_html(body)
    content_html = f'<section style="font-size:16px;line-height:1.8;color:#333;">{content_html}</section>'

    # 公众号 API
    token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}'
    token = requests.get(token_url, timeout=15).json().get('access_token')
    if not token:
        print('❌ token 获取失败')
        return

    # 生成封面图并上传 (thumb_media_id 必填)
    try:
        from PIL import Image, ImageDraw, ImageFont
        W, H = 900, 383
        img = Image.new('RGB', (W, H))
        px = img.load()
        c1, c2 = (102, 126, 234), (118, 75, 162)  # 蓝紫渐变
        for y in range(H):
            for x in range(W):
                t = x / W
                px[x, y] = (int(c1[0] + (c2[0]-c1[0])*t), int(c1[1] + (c2[1]-c1[1])*t), int(c1[2] + (c2[2]-c1[2])*t))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 48)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 28)
        except Exception:
            font = font_small = None
        if font:
            short_title = title[:14] + ('…' if len(title) > 14 else '')
            draw.text((60, 140), short_title, fill=(255, 255, 255), font=font)
            draw.text((60, 300), '生活与简单 · 每日一文', fill=(220, 220, 255), font=font_small)
        cover_path = '/tmp/wechat_cover.jpg'
        img.save(cover_path, 'JPEG', quality=90)
        up = requests.post(
            f'https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image',
            files={'media': ('cover.jpg', open(cover_path, 'rb'), 'image/jpeg')}, timeout=30).json()
        thumb_media_id = up.get('media_id', '')
        print(f'封面: {"✅ " + thumb_media_id[:15] + "…" if thumb_media_id else "❌ " + str(up)}')
    except Exception as e:
        print(f'⚠️ 封面生成/上传失败: {e}')
        thumb_media_id = ''

    url = f'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}'
    article = {
        "title": title,
        "author": AUTHOR,
        "digest": body[:35].replace('\n', ' ').replace('#', '').strip() + '…',
        "content": content_html,
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "show_cover_pic": 0,
        "need_open_comment": 0,
        "only_fans_can_comment": 0
    }
    r = requests.post(
        url,
        data=json.dumps({"articles": [article]}, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
        timeout=30).json()
    if 'media_id' in r:
        print(f'✅ 公众号草稿创建成功: media_id={r["media_id"]}')
    else:
        print(f'❌ 草稿创建失败: {r}')


if __name__ == '__main__':
    main()
