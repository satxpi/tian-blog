#!/usr/bin/env python3
"""
微信公众号官方API发布脚本
使用AppID和AppSecret进行认证
"""

import requests
import json
import time
import sys
import os

class WeChatPublisher:
    def __init__(self, appid, secret):
        self.appid = appid
        self.secret = secret
        self.access_token = None
        self.token_expire_time = 0
        
    def get_access_token(self):
        """获取access_token"""
        # 如果token还有效，直接返回
        if self.access_token and time.time() < self.token_expire_time - 300:  # 提前5分钟刷新
            return self.access_token
            
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.secret}"
        
        try:
            response = requests.get(url, timeout=10)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.token_expire_time = time.time() + result['expires_in']
                print(f"✅ 获取access_token成功，有效期{result['expires_in']}秒")
                return self.access_token
            else:
                print(f"❌ 获取access_token失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
    
    def upload_image(self, image_path):
        """上传图片到微信服务器"""
        token = self.get_access_token()
        if not token:
            return None
            
        url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type=image"
        
        try:
            with open(image_path, 'rb') as f:
                files = {'media': f}
                response = requests.post(url, files=files, timeout=30)
                result = response.json()
                
            if 'media_id' in result:
                print(f"✅ 图片上传成功: {result['media_id']}")
                return result['media_id']
            else:
                print(f"❌ 图片上传失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 上传图片失败: {e}")
            return None
    
    def create_draft(self, title, content, author="智能生活家", digest=""):
        """创建草稿"""
        token = self.get_access_token()
        if not token:
            return None
            
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        
        # 构建文章内容
        articles = [{
            "title": title,
            "author": author,
            "digest": digest if digest else content[:100] + "...",
            "content": content,
            "content_source_url": "",
            "thumb_media_id": "",  # 如果需要封面图，需要先上传
            "show_cover_pic": 0,
            "need_open_comment": 0,
            "only_fans_can_comment": 0
        }]
        
        data = {
            "articles": articles
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if 'media_id' in result:
                print(f"✅ 草稿创建成功: {result['media_id']}")
                return result['media_id']
            else:
                print(f"❌ 草稿创建失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 创建草稿失败: {e}")
            return None
    
    def publish_draft(self, media_id):
        """发布草稿"""
        token = self.get_access_token()
        if not token:
            return False
            
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
        
        data = {
            "media_id": media_id
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get('errcode') == 0:
                print(f"✅ 发布成功！")
                print(f"   发布ID: {result.get('publish_id')}")
                print(f"   状态: {result.get('msg_data_id')}")
                return True
            else:
                print(f"❌ 发布失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return False
    
    def get_today_content(self):
        """获取今天的内容"""
        today = time.strftime("%Y年%m月%d日")
        
        # 检查是否有今天的文件
        content_file = f"/root/.openclaw/workspace/公众号内容/{time.strftime('%m月%d日')}_家务小贴士.md"
        
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题和内容
            lines = content.split('\n')
            title = ""
            body = ""
            
            for line in lines:
                if line.startswith('# ') and not title:
                    title = line[2:].strip()
                elif line and not line.startswith('#'):
                    body += line + '\n'
            
            if not title:
                title = f"🧹 {time.strftime('%m月%d日')}家务小贴士 | 智能生活家"
            
            return title, body
        else:
            # 使用默认内容
            title = f"🧹 {time.strftime('%m月%d日')}家务小贴士 | 5个让家务变轻松的技巧"
            content = """告别家务烦恼！今天分享5个让家务变轻松的小技巧，帮你节省时间，享受整洁的家。

## 1️⃣ 15分钟快速整理法
**核心：定时整理，不拖延**
- 设定15分钟闹钟
- 从最显眼的地方开始（茶几、餐桌）
- 只做整理，不做深度清洁
- 每天坚持，养成习惯

## 2️⃣ 分区清洁法
**核心：一次只做一个区域**
- 周一：客厅
- 周二：厨房
- 周三：卧室
- 周四：卫生间
- 周五：阳台/书房
- 周末：查漏补缺

## 3️⃣ 工具升级法
**核心：好工具事半功倍**
- 无线吸尘器：随时随地吸尘
- 蒸汽拖把：杀菌消毒一次完成
- 多功能清洁剂：一瓶搞定全屋
- 收纳盒/标签机：分类清晰

## 4️⃣ 全家参与法
**核心：家务是全家人的事**
- 制定家务分工表
- 按年龄分配任务
- 设置奖励机制
- 周末一起大扫除

## 5️⃣ 智能辅助法
**核心：科技让生活更轻松**
- 扫地机器人：自动清扫
- 洗碗机：解放双手
- 智能洗衣机：远程控制
- 智能晾衣架：自动升降

💡 **今日实践**：选择1-2个技巧，今天就开始尝试！

---
#家务技巧 #生活小贴士 #智能生活 #整理收纳

💬 **今日互动**：
分享一个你的家务小妙招！"""
            
            return title, content

def main():
    print("=" * 60)
    print("微信公众号自动化发布系统")
    print("=" * 60)
    
    # 从环境变量或配置文件获取凭证
    appid = "wx4d76a79c84e3ebbc"
    secret = "72d4248a0d0384384884116ff2470e06"
    
    if not appid or not secret:
        print("❌ 请设置AppID和AppSecret")
        sys.exit(1)
    
    # 创建发布器
    publisher = WeChatPublisher(appid, secret)
    
    # 获取今天的内容
    print("\n📝 获取今日内容...")
    title, content = publisher.get_today_content()
    print(f"   标题: {title}")
    print(f"   内容长度: {len(content)} 字符")
    
    # 创建草稿
    print("\n📄 创建草稿...")
    digest = "5个让家务变轻松的技巧，帮你节省时间，享受整洁的家。每天坚持15分钟，家务不再是负担！"
    media_id = publisher.create_draft(title, content, "智能生活家", digest)
    
    if not media_id:
        print("❌ 创建草稿失败，停止发布")
        return
    
    # 发布草稿
    print("\n🚀 发布内容...")
    success = publisher.publish_draft(media_id)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 发布流程完成！")
        print(f"   发布时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   文章标题: {title}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 发布失败，请检查错误信息")
        print("=" * 60)

if __name__ == "__main__":
    main()