#!/usr/bin/env python3
import requests
import json
import time
import os

def get_qrcode():
    # 先访问首页获取最新的二维码信息
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    # 访问首页
    print("访问微信公众号平台首页...")
    response = session.get('https://mp.weixin.qq.com/')
    
    if response.status_code != 200:
        print(f"访问首页失败: {response.status_code}")
        return None
    
    # 从页面中提取二维码URL
    import re
    qrcode_pattern = r'https://mp\.weixin\.qq\.com/cgi-bin/scanloginqrcode\?action=getqrcode&random=\d+&login_appid='
    matches = re.findall(qrcode_pattern, response.text)
    
    if not matches:
        print("未找到二维码URL")
        # 尝试从script标签中查找
        script_pattern = r'var qrcode_url = "([^"]+)"'
        script_matches = re.findall(script_pattern, response.text)
        if script_matches:
            qrcode_url = script_matches[0]
        else:
            return None
    else:
        qrcode_url = matches[0]
    
    print(f"找到二维码URL: {qrcode_url}")
    
    # 下载二维码
    print("下载二维码...")
    qr_response = session.get(qrcode_url)
    
    if qr_response.status_code != 200:
        print(f"下载二维码失败: {qr_response.status_code}")
        return None
    
    # 检查返回类型
    content_type = qr_response.headers.get('content-type', '')
    print(f"返回类型: {content_type}")
    
    # 保存文件
    timestamp = int(time.time())
    if 'image' in content_type:
        filename = f'/tmp/weixin_qrcode_{timestamp}.png'
        with open(filename, 'wb') as f:
            f.write(qr_response.content)
        print(f"二维码已保存为: {filename}")
        return filename
    elif 'json' in content_type:
        # 可能是JSON格式，尝试解析
        try:
            data = qr_response.json()
            print(f"JSON响应: {json.dumps(data, ensure_ascii=False)[:200]}...")
            # 有些接口返回base64图片
            if 'qrcode' in data or 'img' in data:
                import base64
                # 这里需要根据实际响应结构处理
                print("需要根据实际JSON结构处理base64图片")
        except:
            print("无法解析JSON响应")
    
    return None

if __name__ == '__main__':
    result = get_qrcode()
    if result:
        print(f"成功: {result}")
    else:
        print("失败")