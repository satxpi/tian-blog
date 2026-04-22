#!/usr/bin/env python3
import requests
import re
import json
import time

def get_mp_info(cookie):
    """获取公众号基本信息"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie,
        'Referer': 'https://mp.weixin.qq.com/'
    }
    
    print("=" * 60)
    print("获取公众号基本信息")
    print("=" * 60)
    
    info = {}
    
    # 1. 获取首页信息
    print("\n1. 分析首页信息...")
    try:
        resp = requests.get('https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN', 
                           headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            
            # 提取公众号名称
            name_pattern = r'公众号名称[^>]*>([^<]+)'
            name_match = re.search(name_pattern, html)
            if name_match:
                info['name'] = name_match.group(1).strip()
                print(f"   公众号名称: {info['name']}")
            
            # 提取原始ID (从cookie中已有)
            info['original_id'] = 'gh_5335932c96d1'
            print(f"   原始ID: {info['original_id']}")
            
            # 提取bizuin (从cookie中已有)
            info['bizuin'] = '3685278932'
            print(f"   Bizuin: {info['bizuin']}")
            
            # 检查公众号类型
            if '服务号' in html:
                info['type'] = '服务号'
            elif '订阅号' in html:
                info['type'] = '订阅号'
            else:
                info['type'] = '未知'
            print(f"   公众号类型: {info['type']}")
            
            # 检查认证状态
            if '已认证' in html or '认证' in html and '未认证' not in html:
                info['verified'] = True
                print(f"   认证状态: 已认证")
            else:
                info['verified'] = False
                print(f"   认证状态: 未认证")
                
    except Exception as e:
        print(f"   错误: {e}")
    
    # 2. 检查设置页面
    print("\n2. 检查设置页面...")
    try:
        resp = requests.get('https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&lang=zh_CN',
                           headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            
            # 检查开发者配置
            if '开发者ID' in html or 'AppID' in html:
                info['has_dev_config'] = True
                print(f"   开发者配置: 已设置")
                
                # 尝试提取AppID
                appid_pattern = r'AppID[^>]*>([^<]+)'
                appid_match = re.search(appid_pattern, html, re.IGNORECASE)
                if appid_match:
                    info['appid'] = appid_match.group(1).strip()
                    print(f"   AppID: {info['appid']}")
            else:
                info['has_dev_config'] = False
                print(f"   开发者配置: 未设置")
                
    except Exception as e:
        print(f"   错误: {e}")
    
    # 3. 检查内容情况
    print("\n3. 检查内容情况...")
    try:
        resp = requests.get('https://mp.weixin.qq.com/cgi-bin/material?action=list&t=material/list&type=news&lang=zh_CN',
                           headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            
            # 检查是否有内容
            if '暂无素材' in html or 'empty' in html.lower():
                info['has_content'] = False
                print(f"   现有内容: 无")
            else:
                info['has_content'] = True
                print(f"   现有内容: 有")
                
                # 粗略估计文章数量
                article_count = html.count('article_item') + html.count('news_item')
                if article_count > 0:
                    info['article_count'] = article_count
                    print(f"   文章数量估计: {article_count}")
                    
    except Exception as e:
        print(f"   错误: {e}")
    
    # 4. 检查消息管理
    print("\n4. 检查消息和粉丝...")
    try:
        resp = requests.get('https://mp.weixin.qq.com/cgi-bin/message?t=message/list&lang=zh_CN',
                           headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            
            # 检查是否有新消息
            if '新消息' in html or '未读' in html:
                info['has_new_messages'] = True
                print(f"   新消息: 有")
            else:
                info['has_new_messages'] = False
                print(f"   新消息: 无")
                
    except Exception as e:
        print(f"   错误: {e}")
    
    # 5. 检查统计页面（粉丝数）
    print("\n5. 检查统计信息...")
    try:
        resp = requests.get('https://mp.weixin.qq.com/cgi-bin/analysis?t=analysis/index&lang=zh_CN',
                           headers=headers, timeout=15)
        
        if resp.status_code == 200:
            html = resp.text
            
            # 尝试提取粉丝数
            fan_patterns = [
                r'粉丝数[^>]*>([\d,]+)',
                r'关注人数[^>]*>([\d,]+)',
                r'(\d+)[^<]*个粉丝',
                r'(\d+)[^<]*位关注者'
            ]
            
            for pattern in fan_patterns:
                match = re.search(pattern, html)
                if match:
                    fans = match.group(1).replace(',', '')
                    info['fans_count'] = int(fans)
                    print(f"   粉丝数量: {info['fans_count']}")
                    break
                    
            if 'fans_count' not in info:
                print(f"   粉丝数量: 未找到")
                
    except Exception as e:
        print(f"   错误: {e}")
    
    return info

def save_mp_report(info, cookie):
    """保存公众号分析报告"""
    
    timestamp = int(time.time())
    filename = f'/tmp/mp_analysis_report_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("微信公众号分析报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n基本信息:\n")
        f.write("-" * 40 + "\n")
        
        if 'name' in info:
            f.write(f"公众号名称: {info['name']}\n")
        if 'original_id' in info:
            f.write(f"原始ID: {info['original_id']}\n")
        if 'bizuin' in info:
            f.write(f"Bizuin: {info['bizuin']}\n")
        if 'type' in info:
            f.write(f"公众号类型: {info['type']}\n")
        if 'verified' in info:
            f.write(f"认证状态: {'已认证' if info['verified'] else '未认证'}\n")
        
        f.write("\n配置情况:\n")
        f.write("-" * 40 + "\n")
        if 'has_dev_config' in info:
            f.write(f"开发者配置: {'已设置' if info['has_dev_config'] else '未设置'}\n")
        if 'appid' in info:
            f.write(f"AppID: {info['appid']}\n")
        
        f.write("\n运营情况:\n")
        f.write("-" * 40 + "\n")
        if 'has_content' in info:
            f.write(f"现有内容: {'有' if info['has_content'] else '无'}\n")
        if 'article_count' in info:
            f.write(f"文章数量: {info['article_count']}\n")
        if 'has_new_messages' in info:
            f.write(f"新消息: {'有' if info['has_new_messages'] else '无'}\n")
        if 'fans_count' in info:
            f.write(f"粉丝数量: {info['fans_count']}\n")
        
        f.write("\nCookie信息:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Cookie长度: {len(cookie)} 字符\n")
        f.write(f"关键字段:\n")
        f.write(f"  wxuin: 76407456099719\n")
        f.write(f"  bizuin: 3685278932\n")
        f.write(f"  master_user: gh_5335932c96d1\n")
    
    print(f"\n报告已保存: {filename}")
    return filename

if __name__ == '__main__':
    cookie = '''yyb_muid=2B8756D0CC606D17230640FFCD066CA9; qq_domain_video_guid_verify=f711a8b820ed8b46; _qimei_uuid42=1980f0103031005d70705ca172275dbe4f7ea59574; pgv_pvid=6690267565; _qimei_fingerprint=3bbf8076805400b4b8f93aeaa85beffb; _qimei_h38=2db8c4cf70705ca172275dbe0200000b01980f; _qimei_i_3=73fa6586c00b5189c19ff830588727e6a2eff0f21a080b8bbd8b200e2fc6716f693536943c89e2d8958a; _qimei_q32=0dee58a781ea1f94016c8fea38b19969; _qimei_q36=47147a99ba0b9e151e457b97300013019816; pac_uid=0_A6mWteTfYEtwp; omgid=0_A6mWteTfYEtwp; RK=kUR3WPjxUc; ptcz=36d12bb6af847e08ffa3c8e86b1a4e7f5602f84219105b35f6c92f188cf3aeff; _qimei_i_2=23c46886925b54dc909ef7620a8421e9a2efa1f0475f0685e6862f5b2693206d6263369c3088e4bdaa9d; _qimei_i_1=64c36b80c1085888c5c4a8375b8373e5a4bfa5f610590487e0dd7d582493206c616365953980eadc80b3f0e1; eas_sid=F1l7M723m2C8C1N7h0b0d9u8i1; ETCI=610ba8c5debc4b42867cf290db3cf2bb; msecToken=6451efbcf0d0854594dec795748fba06; logTrackKey=2286fa380b6e4073bad0d4bc4cf4c3cf; secToken=28aeeacef7625f3cb4ad6fae856e8061; fuid=1a0811c2d7c340638665e02ec5c7930d; ua_id=PUlMfN5ZV4aHNJS8AAAAAHKIwaoIUs-53h141Vwvl58=; _clck=mb4fu5|1|g5a|0; uuid=26ab3b0f6fbbc912cf15de64a92369a5; wxuin=76407456099719; cert=waSJns3H4NjWa869InFXpcIc2ZwgJUfZ; _qpsvr_localtk=0.7866975870144556; data_bizuin=3685278932; bizuin=3685278932; master_user=gh_5335932c96d1; master_sid=WnR5TVprYnRheU93WnBudHpZY3R6RGwwZF9HS2cyMDNzMFpYRXdDc2prT0NIbmxWYUxzWjlNQlZFVjUyYW80YUJiNVVvOGc0cUVjbVRDSE43cHpZY0dkRlMzbHRNdkZqNk4zVWVDbTVuQnBUVkZIT0ljcE5oNUVCSkZzR3hqNGgzcW4zZGppekUxZFBPclA5; master_ticket=473f53bbb6b1683fc8fae69999b4361a; data_ticket=4yD6OsSGcqPmjzFyV4r0wiluEo1nVzhyDw1Xd56Mk8wAG/0dGl/K5KlKCpM7Sl9U; rand_info=CAESIADq+ifcj5ZmkFHcq+DrVNNMuJc6lNTH3xBA5c/chx8I; slave_bizuin=3685278932; slave_user=gh_5335932c96d1; slave_sid=dUZRVmw3UjJERFF3TmNJTTRaX1Baamx3OFF2UHJWbVhCNlN3NGtvZ25YMzhZNTlxNktIYjdNRXl1dVZaUzJxVTlocVFCQnpkbGM5QzhzUFBQdlplcXo3WmVZdlR2NGpkUWxLNUFxVVpWMlB5WUhjOVNDSHlwQ0p1NDhGdDU2Yjl1S1RNa3dZZU9UdGVrcUw2; __wx_phantom_mark__=yRTd85BN9y; _clsk=1v7cw2v|1776414988805|2|1|mp.weixin.qq.com/weheat-agent/payload/record'''
    
    print(f"Cookie长度: {len(cookie)} 字符")
    
    # 获取公众号信息
    mp_info = get_mp_info(cookie)
    
    # 保存报告
    report_file = save_mp_report(mp_info, cookie)
    
    print("\n" + "=" * 60)
    print("✅ 公众号分析完成！")
    print("=" * 60)
    
    # 总结
    print("\n📊 分析总结:")
    
    if 'name' in mp_info:
        print(f"   公众号: {mp_info['name']}")
    if 'type' in mp_info:
        print(f"   类型: {mp_info['type']}")
    if 'verified' in mp_info:
        print(f"   认证: {'✅ 已认证' if mp_info['verified'] else '❌ 未认证'}")
    if 'has_dev_config' in mp_info:
        print(f"   API配置: {'✅ 已设置' if mp_info['has_dev_config'] else '❌ 未设置'}")
    if 'has_content' in mp_info:
        print(f"   现有内容: {'✅ 有' if mp_info['has_content'] else '❌ 无'}")
    if 'fans_count' in mp_info:
        print(f"   粉丝数量: {mp_info['fans_count']}")
    
    print(f"\n📁 详细报告: {report_file}")