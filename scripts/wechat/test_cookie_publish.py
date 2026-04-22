#!/usr/bin/env python3
import requests
import re
import time
import json

def test_publish_flow(cookie):
    """测试cookie发布流程"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie,
        'Referer': 'https://mp.weixin.qq.com/'
    }
    
    print("=" * 60)
    print("测试Cookie发布流程")
    print("=" * 60)
    
    # 1. 测试访问发布页面
    print("\n1. 测试访问新建图文页面...")
    try:
        # 尝试访问新建图文页面
        create_url = 'https://mp.weixin.qq.com/cgi-bin/operate_appmsg?sub=create&t=media/appmsg_edit&type=10&lang=zh_CN'
        resp = requests.get(create_url, headers=headers, timeout=15)
        
        print(f"   状态码: {resp.status_code}")
        print(f"   页面大小: {len(resp.text)} 字节")
        
        # 检查页面内容
        if resp.status_code == 200:
            html = resp.text
            
            # 检查是否有发布表单
            if 'appmsg_title' in html or '标题' in html:
                print("   ✅ 找到发布表单元素")
                
                # 尝试提取token
                token_match = re.search(r'token=([a-f0-9]+)', html)
                if token_match:
                    token = token_match.group(1)
                    print(f"   获取到token: {token}")
                    return True, token, "可访问发布页面"
                else:
                    print("   ⚠️  未找到token")
                    return True, None, "可访问但无token"
            else:
                print("   ❌ 未找到发布表单")
                return False, None, "页面无发布表单"
        else:
            print("   ❌ 无法访问发布页面")
            return False, None, f"状态码{resp.status_code}"
            
    except Exception as e:
        print(f"   错误: {e}")
        return False, None, f"访问异常: {e}"
    
def test_form_submission(cookie, token):
    """测试表单提交"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie,
        'Referer': 'https://mp.weixin.qq.com/cgi-bin/operate_appmsg?sub=create&t=media/appmsg_edit&type=10&lang=zh_CN',
        'Origin': 'https://mp.weixin.qq.com',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    print("\n2. 测试表单提交...")
    
    # 测试数据
    test_data = {
        'token': token,
        'lang': 'zh_CN',
        'f': 'json',
        'ajax': '1',
        'random': str(int(time.time() * 1000)),
        'title': '测试文章 - 请勿发布',
        'author': '智能生活家',
        'digest': '这是自动化测试文章，请勿发布',
        'content': '<p>这是一篇测试文章，用于验证发布流程。</p><p>【由AI生成】</p>',
        'sourceurl': '',
        'cover': '',
        'subtype': '9',
        'copyright': '0',
        'content_type': '1',
        'appmsgid': '',
        'is_original': '0',
        'is_only_read': '0',
        'is_test': '1'  # 测试标记
    }
    
    try:
        submit_url = 'https://mp.weixin.qq.com/cgi-bin/operate_appmsg?t=ajax-response&sub=create'
        resp = requests.post(submit_url, headers=headers, data=test_data, timeout=15)
        
        print(f"   提交状态码: {resp.status_code}")
        print(f"   响应大小: {len(resp.text)} 字节")
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                print(f"   JSON响应: {json.dumps(result, ensure_ascii=False)[:200]}...")
                
                if 'ret' in result:
                    print(f"   返回码: {result['ret']}")
                    if result['ret'] == 0:
                        print("   ✅ 表单提交成功")
                        return True, "表单提交成功"
                    else:
                        print(f"   ⚠️  提交返回非0: {result.get('msg', '无错误信息')}")
                        return False, f"提交失败: {result.get('msg', '未知错误')}"
                else:
                    print("   ⚠️  响应无ret字段")
                    return True, "响应格式异常但可能成功"
            except:
                print("   ⚠️  响应不是JSON格式")
                return True, "非JSON响应"
        else:
            print("   ❌ 提交请求失败")
            return False, f"提交失败，状态码{resp.status_code}"
            
    except Exception as e:
        print(f"   提交错误: {e}")
        return False, f"提交异常: {e}"

def check_cookie_validity(cookie):
    """检查cookie有效性"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie
    }
    
    print("\n3. 检查cookie有效性...")
    
    test_urls = [
        ('首页', 'https://mp.weixin.qq.com/'),
        ('内容管理', 'https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN'),
        ('素材管理', 'https://mp.weixin.qq.com/cgi-bin/material?action=list&t=material/list&lang=zh_CN')
    ]
    
    valid_count = 0
    for name, url in test_urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 1000:
                if '登录' not in resp.text or '微信扫一扫' not in resp.text:
                    print(f"   ✅ {name}: 有效")
                    valid_count += 1
                else:
                    print(f"   ❌ {name}: 需要登录")
            else:
                print(f"   ⚠️  {name}: 状态{resp.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: 错误 {e}")
    
    return valid_count >= 2  # 至少2个页面有效

if __name__ == '__main__':
    cookie = '''yyb_muid=2B8756D0CC606D17230640FFCD066CA9; qq_domain_video_guid_verify=f711a8b820ed8b46; _qimei_uuid42=1980f0103031005d70705ca172275dbe4f7ea59574; pgv_pvid=6690267565; _qimei_fingerprint=3bbf8076805400b4b8f93aeaa85beffb; _qimei_h38=2db8c4cf70705ca172275dbe0200000b01980f; _qimei_i_3=73fa6586c00b5189c19ff830588727e6a2eff0f21a080b8bbd8b200e2fc6716f693536943c89e2d8958a; _qimei_q32=0dee58a781ea1f94016c8fea38b19969; _qimei_q36=47147a99ba0b9e151e457b97300013019816; pac_uid=0_A6mWteTfYEtwp; omgid=0_A6mWteTfYEtwp; RK=kUR3WPjxUc; ptcz=36d12bb6af847e08ffa3c8e86b1a4e7f5602f84219105b35f6c92f188cf3aeff; _qimei_i_2=23c46886925b54dc909ef7620a8421e9a2efa1f0475f0685e6862f5b2693206d6263369c3088e4bdaa9d; _qimei_i_1=64c36b80c1085888c5c4a8375b8373e5a4bfa5f610590487e0dd7d582493206c616365953980eadc80b3f0e1; eas_sid=F1l7M723m2C8C1N7h0b0d9u8i1; ETCI=610ba8c5debc4b42867cf290db3cf2bb; msecToken=6451efbcf0d0854594dec795748fba06; logTrackKey=2286fa380b6e4073bad0d4bc4cf4c3cf; secToken=28aeeacef7625f3cb4ad6fae856e8061; fuid=1a0811c2d7c340638665e02ec5c7930d; ua_id=PUlMfN5ZV4aHNJS8AAAAAHKIwaoIUs-53h141Vwvl58=; _clck=mb4fu5|1|g5a|0; uuid=26ab3b0f6fbbc912cf15de64a92369a5; wxuin=76407456099719; cert=waSJns3H4NjWa869InFXpcIc2ZwgJUfZ; _qpsvr_localtk=0.7866975870144556; data_bizuin=3685278932; bizuin=3685278932; master_user=gh_5335932c96d1; master_sid=WnR5TVprYnRheU93WnBudHpZY3R6RGwwZF9HS2cyMDNzMFpYRXdDc2prT0NIbmxWYUxzWjlNQlZFVjUyYW80YUJiNVVvOGc0cUVjbVRDSE43cHpZY0dkRlMzbHRNdkZqNk4zVWVDbTVuQnBUVkZIT0ljcE5oNUVCSkZzR3hqNGgzcW4zZGppekUxZFBPclA5; master_ticket=473f53bbb6b1683fc8fae69999b4361a; data_ticket=4yD6OsSGcqPmjzFyV4r0wiluEo1nVzhyDw1Xd56Mk8wAG/0dGl/K5KlKCpM7Sl9U; rand_info=CAESIADq+ifcj5ZmkFHcq+DrVNNMuJc6lNTH3xBA5c/chx8I; slave_bizuin=3685278932; slave_user=gh_5335932c96d1; slave_sid=dUZRVmw3UjJERFF3TmNJTTRaX1Baamx3OFF2UHJWbVhCNlN3NGtvZ25YMzhZNTlxNktIYjdNRXl1dVZaUzJxVTlocVFCQnpkbGM5QzhzUFBQdlplcXo3WmVZdlR2NGpkUWxLNUFxVVpWMlB5WUhjOVNDSHlwQ0p1NDhGdDU2Yjl1S1RNa3dZZU9UdGVrcUw2; __wx_phantom_mark__=yRTd85BN9y; _clsk=1v7cw2v|1776414988805|2|1|mp.weixin.qq.com/weheat-agent/payload/record'''
    
    print(f"Cookie长度: {len(cookie)} 字符")
    
    # 检查cookie有效性
    is_valid = check_cookie_validity(cookie)
    
    if is_valid:
        print("\n✅ Cookie有效，继续测试发布流程...")
        
        # 测试发布流程
        can_publish, token, publish_msg = test_publish_flow(cookie)
        
        if can_publish and token:
            print(f"\n✅ 可以访问发布页面: {publish_msg}")
            
            # 测试表单提交
            can_submit, submit_msg = test_form_submission(cookie, token)
            
            if can_submit:
                print(f"\n🎉 发布流程测试成功！")
                print(f"结果: {submit_msg}")
                print("\n可以实施自动化发布系统")
            else:
                print(f"\n⚠️  表单提交测试失败")
                print(f"错误: {submit_msg}")
                print("\n可能需要调整提交参数")
        else:
            print(f"\n❌ 无法访问发布页面")
            print(f"错误: {publish_msg}")
            print("\n可能需要更新cookie或检查权限")
    else:
        print("\n❌ Cookie无效或已过期")
        print("需要更新cookie")
    
    print("\n" + "=" * 60)
    print("测试完成")