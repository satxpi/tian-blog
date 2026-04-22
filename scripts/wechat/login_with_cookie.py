#!/usr/bin/env python3
import requests
import json
import time
import os

def login_with_cookie(cookie_str):
    """使用cookie登录微信公众号后台"""
    
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cookie': cookie_str
    }
    
    print("=" * 60)
    print("尝试使用cookie登录微信公众号后台")
    print("=" * 60)
    
    # 尝试访问首页
    print("\n1. 访问首页检查登录状态...")
    try:
        response = requests.get('https://mp.weixin.qq.com/', headers=headers, timeout=30)
        print(f"   状态码: {response.status_code}")
        print(f"   响应大小: {len(response.text)} 字节")
        
        # 检查是否登录成功
        if '登录' in response.text and '微信扫一扫' in response.text:
            print("   ❌ 检测到登录页面，cookie可能无效或已过期")
            return False, "未登录状态"
        elif 'mp.weixin.qq.com' in response.url and 'cgi-bin' not in response.url:
            print("   ✅ 可能已登录，访问首页成功")
            return True, "首页访问成功"
        else:
            # 检查重定向
            print(f"   最终URL: {response.url}")
            if response.history:
                print(f"   重定向次数: {len(response.history)}")
                for i, resp in enumerate(response.history):
                    print(f"   重定向 {i+1}: {resp.status_code} -> {resp.url}")
            
            return True, f"访问成功，URL: {response.url}"
            
    except Exception as e:
        print(f"   ❌ 访问失败: {e}")
        return False, f"访问异常: {e}"
    
def check_admin_page(cookie_str):
    """检查管理页面访问权限"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie_str
    }
    
    print("\n2. 尝试访问管理页面...")
    
    # 尝试几个可能的管理页面
    admin_pages = [
        ('首页', 'https://mp.weixin.qq.com/'),
        ('内容管理', 'https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN'),
        ('用户管理', 'https://mp.weixin.qq.com/cgi-bin/user_tag?action=index&lang=zh_CN'),
        ('消息管理', 'https://mp.weixin.qq.com/cgi-bin/message?t=message/list&lang=zh_CN'),
        ('素材管理', 'https://mp.weixin.qq.com/cgi-bin/material?action=list&t=material/list&lang=zh_CN'),
        ('设置页面', 'https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&lang=zh_CN')
    ]
    
    results = []
    for name, url in admin_pages:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            status = resp.status_code
            size = len(resp.text)
            
            # 简单判断是否成功
            if status == 200 and size > 1000:
                result = f"✅ {name}: 可访问 ({size}字节)"
                # 检查是否有登录提示
                if '登录' in resp.text and '微信扫一扫' in resp.text:
                    result = f"❌ {name}: 需要登录"
            else:
                result = f"⚠️  {name}: 状态{status} ({size}字节)"
            
            results.append(result)
            print(f"   {result}")
            
        except Exception as e:
            result = f"❌ {name}: 错误 {e}"
            results.append(result)
            print(f"   {result}")
    
    return results

def check_api_config(cookie_str):
    """检查API配置页面"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie_str
    }
    
    print("\n3. 检查API配置权限...")
    
    api_pages = [
        ('基本配置', 'https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=index&lang=zh_CN'),
        ('开发者配置', 'https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=dev&lang=zh_CN'),
        ('接口权限', 'https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=api&lang=zh_CN')
    ]
    
    api_results = []
    for name, url in api_pages:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            
            # 检查页面内容关键词
            content = resp.text.lower()
            checks = []
            
            if 'appid' in content or '开发者id' in content:
                checks.append("找到AppID相关配置")
            if 'appsecret' in content or '开发者密码' in content:
                checks.append("找到AppSecret相关配置")
            if 'token' in content and '服务器' in content:
                checks.append("找到服务器配置")
            if '接口' in content and '权限' in content:
                checks.append("找到接口权限配置")
            
            if checks:
                result = f"✅ {name}: 可访问 - {', '.join(checks)}"
            else:
                result = f"⚠️  {name}: 可访问但未找到关键配置"
            
            api_results.append(result)
            print(f"   {result}")
            
        except Exception as e:
            result = f"❌ {name}: 错误 {e}"
            api_results.append(result)
            print(f"   {result}")
    
    return api_results

def save_login_info(cookie_str, results):
    """保存登录信息"""
    
    timestamp = int(time.time())
    filename = f'/tmp/weixin_login_report_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("微信公众号登录检查报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Cookie长度: {len(cookie_str)} 字符\n")
        f.write("\n检查结果:\n")
        
        for result in results:
            f.write(f"{result}\n")
    
    print(f"\n4. 报告已保存: {filename}")
    return filename

if __name__ == '__main__':
    # 从用户提供的cookie
    cookie = "yyb_muid=2B8756D0CC606D17230640FFCD066CA9; qq_domain_video_guid_verify=f711a8b820ed8b46; _qimei_uuid42=1980f0103031005d70705ca172275dbe4f7ea59574; pgv_pvid=6690267565; _qimei_fingerprint=3bbf8076805400b4b8f93aeaa85beffb; _qimei_h38=2db8c4cf70705ca172275dbe0200000b01980f; _qimei_i_3=73fa6586c00b5189c19ff830588727e6a2eff0f21a080b8bbd8b200e2fc6716f693536943c89e2d8958a; _qimei_q32=0dee58a781ea1f94016c8fea38b19969; _qimei_q36=47147a99ba0b9e151e457b97300013019816; pac_uid=0_A6mWteTfYEtwp; omgid=0_A6mWteTfYEtwp; RK=kUR3WPjxUc; ptcz=36d12bb6af847e08ffa3c8e86b1a4e7f5602f84219105b35f6c92f188cf3aeff; _qimei_i_2=23c46886925b54dc909ef7620a8421e9a2efa1f0475f0685e6862f5b2693206d6263369c3088e4bdaa9d; _qimei_i_1=64c36b80c1085888c5c4a8375b8373e5a4bfa5f610590487e0dd7d582493206c616365953980eadc80b3f0e1; eas_sid=F1l7M723m2C8C1N7h0b0d9u8i1; ETCI=610ba8c5debc4b42867cf290db3cf2bb; msecToken=6451efbcf0d0854594dec795748fba06; logTrackKey=2286fa380b6e4073bad0d4bc4cf4c3cf; secToken=28aeeacef7625f3cb4ad6fae856e8061; fuid=1a0811c2d7c340638665e02ec5c7930d; _clck=mb4fu5|1|g5a|0; _qpsvr_localtk=0.7866975870144556; _clsk=k7pon2|1776412468102|11|1|mp.weixin.qq.com/weheat-agent/payload/record"
    
    print(f"Cookie长度: {len(cookie)} 字符")
    print(f"Cookie前100字符: {cookie[:100]}...")
    
    # 执行检查
    login_success, login_msg = login_with_cookie(cookie)
    
    if login_success:
        print(f"\n✅ 登录检查: {login_msg}")
        
        # 检查管理页面
        admin_results = check_admin_page(cookie)
        
        # 检查API配置
        api_results = check_api_config(cookie)
        
        # 保存报告
        all_results = [login_msg] + admin_results + api_results
        report_file = save_login_info(cookie, all_results)
        
        print("\n" + "=" * 60)
        print("✅ 检查完成！")
        print("=" * 60)
        
        # 总结
        success_count = sum(1 for r in all_results if '✅' in r)
        warning_count = sum(1 for r in all_results if '⚠️' in r)
        error_count = sum(1 for r in all_results if '❌' in r)
        
        print(f"\n总结:")
        print(f"  成功: {success_count}")
        print(f"  警告: {warning_count}")
        print(f"  错误: {error_count}")
        
        if success_count > 0:
            print("\n🎉 可以访问微信公众号后台！")
            print("下一步: 开始检查具体配置和制定运营计划")
        else:
            print("\n❌ 无法访问，可能需要更新cookie或重新登录")
            
    else:
        print(f"\n❌ 登录失败: {login_msg}")
        print("建议: 请提供新的cookie或尝试其他登录方式")