#!/usr/bin/env python3
"""
稳健的微信公众号发布脚本
基于测试经验，正确处理参数限制和错误
"""

import requests
import json
import time
import base64
import os
from typing import Optional, Dict, Any

class WeChatRobustPublisher:
    def __init__(self, appid: str, secret: str):
        self.appid = appid
        self.secret = secret
        self.access_token = None
        self.token_expire_time = 0
        
    def get_access_token(self) -> Optional[str]:
        """获取access_token，带缓存"""
        if self.access_token and time.time() < self.token_expire_time - 300:
            return self.access_token
            
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.secret}"
        
        try:
            response = requests.get(url, timeout=10)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.token_expire_time = time.time() + result['expires_in']
                print(f"✅ access_token获取成功，有效期{result['expires_in']}秒")
                return self.access_token
            else:
                print(f"❌ 获取access_token失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
    
    def validate_parameters(self, title: str, author: str, digest: str) -> Dict[str, Any]:
        """验证并修正参数，确保符合微信API限制"""
        # 标题不超过32个字
        if len(title) > 32:
            title = title[:32]
            print(f"⚠️  标题截断为32字: {title}")
        
        # 作者不超过16个字
        if len(author) > 16:
            author = author[:16]
            print(f"⚠️  作者截断为16字: {author}")
        
        # 摘要不超过128个字
        if digest and len(digest) > 128:
            digest = digest[:128]
            print(f"⚠️  摘要截断为128字: {digest[:50]}...")
        
        return {
            'title': title,
            'author': author,
            'digest': digest
        }
    
    def upload_cover_image(self) -> Optional[str]:
        """上传封面图获取永久media_id"""
        token = self.get_access_token()
        if not token:
            return None
            
        # 创建一个简单的默认封面图（1x1透明PNG）
        image_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        
        # 使用material/add_material接口上传永久素材
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
        
        try:
            files = {'media': ('cover.png', image_data, 'image/png')}
            response = requests.post(url, files=files, timeout=30)
            result = response.json()
            
            if 'media_id' in result:
                print(f"✅ 封面图上传成功，media_id: {result['media_id'][:20]}...")
                return result['media_id']
            else:
                print(f"❌ 封面图上传失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 上传封面图失败: {e}")
            return None
    
    def create_draft(self, title: str, content: str, author: str = "智能生活家", 
                    digest: str = "", cover_media_id: Optional[str] = None) -> Optional[str]:
        """创建草稿（稳健版）"""
        token = self.get_access_token()
        if not token:
            return None
        
        # 验证并修正参数
        validated = self.validate_parameters(title, author, digest)
        title = validated['title']
        author = validated['author']
        digest = validated['digest']
        
        # 构建文章数据
        article = {
            'title': title,
            'author': author,
            'content': content,
            'content_source_url': '',
            'need_open_comment': 0,
            'only_fans_can_comment': 0
        }
        
        # 如果有摘要，添加摘要字段
        if digest:
            article['digest'] = digest
        
        # 如果有封面图，添加封面图字段
        if cover_media_id:
            article['thumb_media_id'] = cover_media_id
            article['show_cover_pic'] = 1
        else:
            article['show_cover_pic'] = 0
        
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        data = {'articles': [article]}
        
        print(f"📝 创建草稿参数:")
        print(f"   标题: {title} ({len(title)}字)")
        print(f"   作者: {author} ({len(author)}字)")
        print(f"   摘要: {digest[:50] if digest else '无'} ({len(digest) if digest else 0}字)")
        print(f"   内容长度: {len(content)}字符")
        print(f"   封面图: {'有' if cover_media_id else '无'}")
        
        try:
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            print(f"📋 创建草稿响应: {json.dumps(result, ensure_ascii=False)}")
            
            if 'media_id' in result:
                draft_id = result['media_id']
                print(f"✅ 草稿创建成功！草稿ID: {draft_id}")
                return draft_id
            else:
                errcode = result.get('errcode')
                errmsg = result.get('errmsg', '未知错误')
                print(f"❌ 草稿创建失败: {errcode} - {errmsg}")
                
                # 根据错误码提供建议
                if errcode == 40007:
                    print("   建议: thumb_media_id无效，可能需要重新上传封面图")
                elif errcode == 45003:
                    print("   建议: 标题长度超出32字限制")
                elif errcode == 45004:
                    print("   建议: 摘要长度超出128字限制")
                elif errcode == 45110:
                    print("   建议: 作者长度超出16字限制")
                elif errcode == 48001:
                    print("   建议: API未授权，需要在公众号后台开通权限")
                    
                return None
                
        except Exception as e:
            print(f"❌ 创建草稿异常: {e}")
            return None
    
    def publish_draft(self, draft_id: str) -> bool:
        """发布草稿"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
        data = {'media_id': draft_id}
        
        print(f"🚀 发布草稿ID: {draft_id}")
        
        try:
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            print(f"📋 发布响应: {json.dumps(result, ensure_ascii=False)}")
            
            if result.get('errcode') == 0:
                print(f"✅ 发布成功！")
                print(f"   发布ID: {result.get('publish_id', 'N/A')}")
                print(f"   消息ID: {result.get('msg_data_id', 'N/A')}")
                return True
            else:
                print(f"⚠️  发布失败: {result.get('errcode')} - {result.get('errmsg')}")
                return False
                
        except Exception as e:
            print(f"❌ 发布异常: {e}")
            return False
    
    def get_today_content(self) -> tuple:
        """获取今天的内容"""
        # 今天的内容：家务小贴士
        title = "5个让家务变轻松的技巧"
        content = '''<p>告别家务烦恼！今天分享5个让家务变轻松的小技巧，帮你节省时间，享受整洁的家。</p>

<h2>1️⃣ 15分钟快速整理法</h2>
<p><strong>核心：定时整理，不拖延</strong></p>
<ul>
<li>设定15分钟闹钟</li>
<li>从最显眼的地方开始（茶几、餐桌）</li>
<li>只做整理，不做深度清洁</li>
<li>每天坚持，养成习惯</li>
</ul>

<h2>2️⃣ 分区清洁法</h2>
<p><strong>核心：一次只做一个区域</strong></p>
<ul>
<li>周一：客厅</li>
<li>周二：厨房</li>
<li>周三：卧室</li>
<li>周四：卫生间</li>
<li>周五：阳台/书房</li>
<li>周末：查漏补缺</li>
</ul>

<h2>3️⃣ 工具升级法</h2>
<p><strong>核心：好工具事半功倍</strong></p>
<ul>
<li>无线吸尘器：随时随地吸尘</li>
<li>蒸汽拖把：杀菌消毒一次完成</li>
<li>多功能清洁剂：一瓶搞定全屋</li>
<li>收纳盒/标签机：分类清晰</li>
</ul>

<h2>4️⃣ 全家参与法</h2>
<p><strong>核心：家务是全家人的事</strong></p>
<ul>
<li>制定家务分工表</li>
<li>按年龄分配任务</li>
<li>设置奖励机制</li>
<li>周末一起大扫除</li>
</ul>

<h2>5️⃣ 智能辅助法</h2>
<p><strong>核心：科技让生活更轻松</strong></p>
<ul>
<li>扫地机器人：自动清扫</li>
<li>洗碗机：解放双手</li>
<li>智能洗衣机：远程控制</li>
<li>智能晾衣架：自动升降</li>
</ul>

<p>💡 <strong>今日实践</strong>：选择1-2个技巧，今天就开始尝试！</p>

<hr>
<p><strong>#家务技巧 #生活小贴士 #智能生活 #整理收纳</strong></p>

<p>💬 <strong>今日互动</strong>：<br>
分享一个你的家务小妙招！</p>'''
        
        digest = "分享5个家务技巧，帮你节省时间，享受整洁的家。"
        
        return title, content, digest

def main():
    print("=" * 60)
    print("微信公众号稳健发布系统")
    print("=" * 60)
    
    # 使用您的公众号凭证
    appid = "wx4d76a79c84e3ebbc"
    secret = "72d4248a0d0384384884116ff2470e06"
    
    if not appid or not secret:
        print("❌ 请设置AppID和AppSecret")
        return
    
    # 创建发布器
    publisher = WeChatRobustPublisher(appid, secret)
    
    # 测试access_token
    print("\n🔑 测试API连接...")
    token = publisher.get_access_token()
    if not token:
        print("❌ API连接失败，请检查凭证")
        return
    
    print("✅ API连接正常")
    
    # 获取今天的内容
    print("\n📝 准备今日内容...")
    title, content, digest = publisher.get_today_content()
    print(f"   标题: {title}")
    print(f"   摘要: {digest}")
    print(f"   内容长度: {len(content)}字符")
    
    # 上传封面图
    print("\n🖼️  上传封面图...")
    cover_media_id = publisher.upload_cover_image()
    
    # 创建草稿
    print("\n📄 创建草稿...")
    draft_id = publisher.create_draft(
        title=title,
        content=content,
        author="生活家",  # 简化作者名
        digest=digest,
        cover_media_id=cover_media_id
    )
    
    if not draft_id:
        print("\n⚠️  草稿创建失败，尝试无封面图版本...")
        # 尝试无封面图
        draft_id = publisher.create_draft(
            title=title,
            content=content,
            author="生活家",
            digest=digest,
            cover_media_id=None
        )
    
    if draft_id:
        # 发布草稿
        print("\n🚀 发布内容...")
        success = publisher.publish_draft(draft_id)
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 发布流程完成！")
            print(f"   发布时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   文章标题: {title}")
            print("=" * 60)
            
            # 保存发布记录
            record = {
                'status': 'success',
                'title': title,
                'draft_id': draft_id,
                'publish_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'content_length': len(content)
            }
            
            record_file = f"/root/.openclaw/workspace/公众号发布成功_{time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
            print(f"\n📁 发布记录已保存: {record_file}")
        else:
            print("\n" + "=" * 60)
            print("⚠️  草稿已创建但发布失败")
            print(f"   草稿ID: {draft_id}")
            print(f"   请在公众号后台「草稿箱」中手动发布")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 发布失败")
        print("   可能原因:")
        print("   1. API权限不足（需要开通草稿箱功能）")
        print("   2. 参数格式问题")
        print("   3. 频率限制")
        print("=" * 60)
        
        # 建议方案
        print("\n💡 建议解决方案:")
        print("   1. 登录公众号后台检查API权限")
        print("   2. 使用网页发布方案（cookie方式）")
        print("   3. 手动复制内容到公众号后台发布")

if __name__ == "__main__":
    main()