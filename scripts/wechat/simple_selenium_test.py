#!/usr/bin/env python3
"""
简化版Selenium测试
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_selenium():
    """测试Selenium是否正常工作"""
    print("测试Selenium环境...")
    
    try:
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 创建驱动
        driver = webdriver.Chrome(options=chrome_options)
        
        # 测试访问网页
        print("访问测试页面...")
        driver.get("https://www.baidu.com")
        time.sleep(2)
        
        # 检查页面标题
        title = driver.title
        print(f"页面标题: {title}")
        
        # 截图
        driver.save_screenshot("/tmp/selenium_test.png")
        print("截图已保存: /tmp/selenium_test.png")
        
        # 关闭浏览器
        driver.quit()
        
        print("✅ Selenium测试成功")
        return True
        
    except Exception as e:
        print(f"❌ Selenium测试失败: {e}")
        return False

def check_cookie():
    """检查cookie文件"""
    cookie_file = "/tmp/wechat_auto/cookie.txt"
    
    if os.path.exists(cookie_file):
        size = os.path.getsize(cookie_file)
        print(f"✅ Cookie文件存在: {cookie_file}")
        print(f"文件大小: {size} 字节")
        
        # 读取前100字符
        with open(cookie_file, 'r', encoding='utf-8') as f:
            content = f.read(100)
            print(f"内容预览: {content}...")
        
        return True
    else:
        print(f"❌ Cookie文件不存在: {cookie_file}")
        return False

def main():
    print("=" * 60)
    print("微信公众号自动化系统 - 环境测试")
    print("=" * 60)
    
    # 测试Selenium
    selenium_ok = test_selenium()
    
    # 检查cookie
    cookie_ok = check_cookie()
    
    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"Selenium环境: {'✅ 正常' if selenium_ok else '❌ 异常'}")
    print(f"Cookie文件: {'✅ 存在' if cookie_ok else '❌ 缺失'}")
    
    if selenium_ok and cookie_ok:
        print("\n🎉 环境测试通过，可以运行自动化系统")
        print("\n下一步:")
        print("1. 运行自动化发布: python3 wechat_selenium_publisher.py")
        print("2. 或使用定时任务系统")
    else:
        print("\n⚠️  环境测试未通过")
        if not selenium_ok:
            print("- 需要修复Selenium环境")
        if not cookie_ok:
            print(f"- 需要创建cookie文件: /tmp/wechat_auto/cookie.txt")
    
    print("=" * 60)

if __name__ == "__main__":
    main()