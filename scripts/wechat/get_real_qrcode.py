#!/usr/bin/env python3
import requests
import re
import json
import time

def get_qrcode_url():
    # 访问登录页面
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("访问微信公众号登录页面...")
    response = session.get('https://mp.weixin.qq.com/', headers=headers)
    
    if response.status_code != 200:
        print(f"访问失败: {response.status_code}")
        return None
    
    # 查找二维码URL - 从JavaScript变量中提取
    html = response.text
    
    # 方法1: 查找qrcodeSrc变量
    pattern1 = r"qrcodeSrc\s*:\s*'([^']+)'"
    match1 = re.search(pattern1, html)
    
    if match1:
        qrcode_url = match1.group(1)
        print(f"找到二维码URL(方法1): {qrcode_url}")
        return qrcode_url
    
    # 方法2: 查找scanloginqrcode模式
    pattern2 = r'https://mp\.weixin\.qq\.com/cgi-bin/scanloginqrcode\?[^"\']+'
    match2 = re.search(pattern2, html)
    
    if match2:
        qrcode_url = match2.group(0)
        print(f"找到二维码URL(方法2): {qrcode_url}")
        return qrcode_url
    
    # 方法3: 查找包含qrcode的img标签
    pattern3 = r'<img[^>]*src="([^"]*qrcode[^"]*)"'
    match3 = re.search(pattern3, html, re.IGNORECASE)
    
    if match3:
        qrcode_url = match3.group(1)
        # 确保是完整URL
        if qrcode_url.startswith('//'):
            qrcode_url = 'https:' + qrcode_url
        elif qrcode_url.startswith('/'):
            qrcode_url = 'https://mp.weixin.qq.com' + qrcode_url
        
        print(f"找到二维码URL(方法3): {qrcode_url}")
        return qrcode_url
    
    print("未找到二维码URL")
    return None

def download_qrcode(qrcode_url):
    if not qrcode_url:
        return None
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mp.weixin.qq.com/'
    }
    
    print(f"下载二维码: {qrcode_url}")
    response = session.get(qrcode_url, headers=headers)
    
    if response.status_code != 200:
        print(f"下载失败: {response.status_code}")
        return None
    
    content_type = response.headers.get('content-type', '')
    print(f"响应类型: {content_type}")
    
    # 保存文件
    timestamp = int(time.time())
    filename = f'/tmp/real_weixin_qrcode_{timestamp}.png'
    
    with open(filename, 'wb') as f:
        f.write(response.content)
    
    print(f"二维码已保存: {filename}")
    print(f"文件大小: {len(response.content)} bytes")
    
    return filename

if __name__ == '__main__':
    print("=" * 50)
    print("获取微信公众号真实登录二维码")
    print("=" * 50)
    
    qrcode_url = get_qrcode_url()
    
    if qrcode_url:
        filename = download_qrcode(qrcode_url)
        if filename:
            print(f"\n✅ 成功获取真实登录二维码: {filename}")
            print(f"请用微信扫描此二维码登录")
        else:
            print("\n❌ 下载二维码失败")
    else:
        print("\n❌ 未找到二维码URL")
        print("请手动访问: https://mp.weixin.qq.com")