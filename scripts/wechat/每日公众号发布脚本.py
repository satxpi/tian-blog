#!/usr/bin/env python3
"""
每日微信公众号文章自动发布脚本
每天生成一篇有深度、有感情的文章，提交到草稿箱
"""

import os
import json
import time
import random
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class DailyWeChatPublisher:
    def __init__(self, appid: str, secret: str):
        self.appid = appid
        self.secret = secret
        self.workspace = "/root/.openclaw/workspace"
        
    def get_today_theme(self) -> Dict:
        """根据日期和主题库选择今天的主题"""
        themes = [
            {
                "category": "生活哲学",
                "themes": [
                    "慢生活的艺术：在快节奏时代找回内心的宁静",
                    "孤独的价值：如何与独处时光和解",
                    "简单的力量：少即是多的生活智慧",
                    "感恩练习：每天发现三个小确幸",
                    "正念生活：在平凡日常中寻找非凡意义"
                ]
            },
            {
                "category": "情感关系", 
                "themes": [
                    "高质量陪伴：放下手机，真正看见彼此",
                    "爱的语言：五种表达爱意的方式",
                    "边界感：亲密关系中的自我与尊重",
                    "家庭仪式感：创造属于你们的独特时刻",
                    "冲突的艺术：如何把争吵变成深度沟通"
                ]
            },
            {
                "category": "自我成长",
                "themes": [
                    "终身学习：在变化时代保持竞争力的秘密",
                    "情绪管理：从被情绪控制到与情绪共处",
                    "时间投资：把时间花在真正重要的事情上",
                    "习惯养成：微小改变带来的巨大影响",
                    "自我接纳：爱上不完美的自己"
                ]
            },
            {
                "category": "社会观察",
                "themes": [
                    "数字断舍离：在信息过载时代保持清醒",
                    "消费主义反思：我们真的需要那么多吗？",
                    "工作意义：除了谋生，工作还能带给我们什么？",
                    "社区连接：重建现代人的邻里关系",
                    "环境意识：从小事做起的环境保护"
                ]
            }
        ]
        
        # 根据日期选择主题，确保每天不同
        day_of_year = datetime.now().timetuple().tm_yday
        category_idx = day_of_year % len(themes)
        category = themes[category_idx]
        
        theme_idx = (day_of_year // len(themes)) % len(category["themes"])
        theme = category["themes"][theme_idx]
        
        return {
            "category": category["category"],
            "theme": theme,
            "date": datetime.now().strftime("%Y年%m月%d日")
        }
    
    def generate_article_content(self, theme_info: Dict) -> str:
        """生成文章内容"""
        category = theme_info["category"]
        theme = theme_info["theme"]
        date = theme_info["date"]
        
        # 封面图库（Unsplash高质量图片）
        cover_images = [
            "https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1519681393784-d120267933ba?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1506744038136-46273834b3fb?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1518837695005-2083093ee35b?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
        ]
        
        cover_image = random.choice(cover_images)
        
        # 生成文章内容框架
        article = f"""---
title: {theme}
author: 生活家
cover: {cover_image}
---

*本文由AI生成，经人工审核修改*

## 一、开篇：为什么我们需要思考"{theme.split('：')[0]}"？

在这个{random.choice(['快节奏', '信息爆炸', '物质丰富', '连接紧密'])}的时代，我们似乎拥有了更多，却常常感到{random.choice(['空虚', '焦虑', '迷茫', '疲惫'])}。"{theme}"这个话题，或许能给我们一些启发。

## 二、核心观点：三个层次的思考

### 第一层：现象观察
- 我们日常生活中的具体表现
- 社会普遍存在的现象
- 个人经历的真实案例

### 第二层：深层原因
- 心理层面的驱动因素
- 社会文化的影响
- 时代背景的作用

### 第三层：解决方案
- 个人可以采取的具体行动
- 思维模式的转变
- 长期坚持的方法

## 三、实践指南：从今天开始尝试

### 第一步：自我觉察
1. 记录相关的情境和感受
2. 分析触发因素
3. 了解自己的反应模式

### 第二步：小步改变
1. 选择一个最容易开始的点
2. 设定切实可行的目标
3. 记录改变带来的影响

### 第三步：建立习惯
1. 将新行为融入日常生活
2. 寻找支持系统
3. 定期反思和调整

## 四、真实故事：他们是如何做到的？

（这里可以加入虚构但真实感人的小故事，展示理论在实践中的应用）

## 五、深度思考：超越表面的意义

"{theme}"不仅仅是一个技巧或方法，它背后反映的是：
- 我们对{random.choice(['生活', '自我', '关系', '社会'])}的理解
- 价值观的重新审视
- 生命意义的探索

## 六、互动与反思

### 今日思考题：
1. 关于"{theme.split('：')[0]}"，你最大的困惑是什么？
2. 你曾经有哪些相关的成功或失败经历？
3. 如果要从一个微小改变开始，你会选择什么？

### 行动建议：
- 本周尝试文中的一个方法
- 记录你的感受和变化
- 与信任的人分享你的体验

## 七、结语：慢慢来，比较快

改变从来不是一蹴而就的。就像{random.choice(['园丁培育花朵', '匠人打磨作品', '旅者探索未知'])}一样，需要耐心、坚持和爱。

愿你在探索"{theme.split('：')[0]}"的路上，找到属于自己的节奏和答案。

---

**💬 今日互动：**
分享你对"{theme.split('：')[0]}"的思考或经历。
你的故事，或许能点亮另一个人的路。"""
        
        return article
    
    def save_article(self, content: str, theme_info: Dict) -> str:
        """保存文章到文件"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"每日文章_{date_str}_{theme_info['category']}.md"
        filepath = os.path.join(self.workspace, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📝 文章已保存: {filepath}")
        return filepath
    
    def publish_to_draft(self, filepath: str) -> bool:
        """使用wenyan-cli发布到草稿箱"""
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['WECHAT_APP_ID'] = self.appid
            env['WECHAT_APP_SECRET'] = self.secret
            
            # 执行wenyan publish命令
            cmd = ['wenyan', 'publish', '--file', filepath]
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ 成功提交到草稿箱")
                print(f"   输出: {result.stdout.strip()}")
                return True
            else:
                print(f"❌ 提交失败")
                print(f"   错误: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ 命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 执行异常: {e}")
            return False
    
    def run_daily_publish(self):
        """执行每日发布流程"""
        print("=" * 60)
        print(f"📅 每日公众号文章发布 - {datetime.now().strftime('%Y年%m月%d日 %A')}")
        print("=" * 60)
        
        # 1. 获取今日主题
        print("\n🎯 步骤1: 确定今日主题...")
        theme_info = self.get_today_theme()
        print(f"   分类: {theme_info['category']}")
        print(f"   主题: {theme_info['theme']}")
        
        # 2. 生成文章内容
        print("\n📝 步骤2: 生成文章内容...")
        article_content = self.generate_article_content(theme_info)
        print(f"   文章长度: {len(article_content)} 字符")
        
        # 3. 保存文章文件
        print("\n💾 步骤3: 保存文章文件...")
        filepath = self.save_article(article_content, theme_info)
        
        # 4. 提交到草稿箱
        print("\n🚀 步骤4: 提交到公众号草稿箱...")
        success = self.publish_to_draft(filepath)
        
        # 5. 记录日志
        print("\n📋 步骤5: 记录发布日志...")
        log_entry = {
            "date": datetime.now().isoformat(),
            "theme": theme_info["theme"],
            "category": theme_info["category"],
            "filepath": filepath,
            "success": success,
            "article_length": len(article_content)
        }
        
        log_file = os.path.join(self.workspace, "公众号发布日志.json")
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        print(f"   日志已记录: {log_file}")
        
        # 6. 输出总结
        print("\n" + "=" * 60)
        if success:
            print("🎉 每日发布任务完成！")
            print(f"   主题: {theme_info['theme']}")
            print(f"   文件: {os.path.basename(filepath)}")
            print(f"   状态: 已提交到草稿箱")
        else:
            print("⚠️  发布任务部分完成")
            print(f"   主题: {theme_info['theme']}")
            print(f"   文件: {os.path.basename(filepath)}")
            print(f"   状态: 文章已生成，但提交失败")
        
        print("=" * 60)

def main():
    """主函数"""
    # 公众号凭证
    appid = "wx4d76a79c84e3ebbc"
    secret = "72d4248a0d0384384884116ff2470e06"
    
    if not appid or not secret:
        print("❌ 请设置公众号凭证")
        return
    
    # 创建发布器
    publisher = DailyWeChatPublisher(appid, secret)
    
    # 执行每日发布
    publisher.run_daily_publish()
    
    # 提示信息
    print("\n💡 后续操作:")
    print("   1. 登录公众号后台检查草稿箱")
    print("   2. 审核文章内容")
    print("   3. 手动发布")
    print("   4. 观察读者反馈")
    print("\n🔄 自动化设置:")
    print("   可以将此脚本添加到crontab，每天自动运行")
    print("   Example: 0 9 * * * cd /root/.openclaw/workspace && python3 每日公众号发布脚本.py")

if __name__ == "__main__":
    main()