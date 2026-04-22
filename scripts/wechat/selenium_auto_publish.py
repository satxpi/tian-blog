#!/usr/bin/env python3
"""
微信公众号自动化发布脚本
使用Selenium模拟人工操作
"""

import time
import json
import os
from datetime import datetime

# Selenium相关导入（安装后可用）
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium未安装，将生成模拟脚本")

class WeChatAutoPublisher:
    """微信公众号自动化发布器"""
    
    def __init__(self, cookie=None, headless=True):
        """
        初始化发布器
        
        Args:
            cookie: 可选的cookie字符串
            headless: 是否无头模式（后台运行）
        """
        self.cookie = cookie
        self.headless = headless
        self.driver = None
        self.log_file = f'/tmp/wechat_publish_log_{int(time.time())}.txt'
        
    def setup_driver(self):
        """设置浏览器驱动"""
        if not SELENIUM_AVAILABLE:
            print("错误: Selenium未安装")
            return False
        
        try:
            from selenium.webdriver.chrome.options import Options
            
            # 配置Chrome选项
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')  # 无头模式
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 其他配置
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 创建驱动
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 设置隐式等待
            self.driver.implicitly_wait(10)
            
            self.log("浏览器驱动设置成功")
            return True
            
        except Exception as e:
            self.log(f"设置浏览器驱动失败: {e}")
            return False
    
    def login_with_cookie(self):
        """使用cookie登录"""
        if not self.driver:
            self.log("错误: 浏览器未初始化")
            return False
        
        try:
            # 先访问首页
            self.driver.get('https://mp.weixin.qq.com/')
            time.sleep(3)
            
            # 如果有cookie，设置cookie
            if self.cookie:
                # 解析cookie字符串
                cookies = self.parse_cookie_string(self.cookie)
                for cookie_dict in cookies:
                    try:
                        self.driver.add_cookie(cookie_dict)
                    except:
                        pass
                
                # 刷新页面应用cookie
                self.driver.refresh()
                time.sleep(3)
            
            # 检查是否登录成功
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            if 'login' not in current_url and '登录' not in page_source:
                self.log("✅ Cookie登录成功")
                return True
            else:
                self.log("❌ Cookie登录失败，可能需要扫码")
                return False
                
        except Exception as e:
            self.log(f"登录过程出错: {e}")
            return False
    
    def parse_cookie_string(self, cookie_str):
        """解析cookie字符串为字典列表"""
        cookies = []
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookie_dict = {
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.weixin.qq.com',
                    'path': '/',
                    'secure': False,
                    'httpOnly': False
                }
                cookies.append(cookie_dict)
        return cookies
    
    def navigate_to_publish(self):
        """导航到发布页面"""
        if not self.driver:
            return False
        
        try:
            # 尝试直接访问发布页面
            publish_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=10&lang=zh_CN'
            self.driver.get(publish_url)
            time.sleep(3)
            
            # 检查是否在发布页面
            if 'appmsg' in self.driver.current_url:
                self.log("✅ 成功进入发布页面")
                return True
            else:
                # 尝试通过菜单导航
                self.log("尝试通过菜单导航...")
                return self.navigate_by_menu()
                
        except Exception as e:
            self.log(f"导航到发布页面失败: {e}")
            return False
    
    def navigate_by_menu(self):
        """通过菜单导航到发布页面"""
        try:
            # 点击"内容与互动"菜单
            menu_xpath = "//span[contains(text(), '内容与互动') or contains(text(), 'Content')]"
            menu = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, menu_xpath))
            )
            menu.click()
            time.sleep(1)
            
            # 点击"图文消息"
            article_xpath = "//a[contains(text(), '图文消息') or contains(text(), 'Articles')]"
            article_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, article_xpath))
            )
            article_link.click()
            time.sleep(3)
            
            # 点击"新建图文消息"
            create_xpath = "//a[contains(text(), '新建图文消息') or contains(text(), 'New Article')]"
            create_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, create_xpath))
            )
            create_btn.click()
            time.sleep(3)
            
            self.log("✅ 通过菜单导航到发布页面成功")
            return True
            
        except Exception as e:
            self.log(f"菜单导航失败: {e}")
            return False
    
    def fill_article_form(self, title, content, author="智能生活家"):
        """填写文章表单"""
        try:
            # 等待表单加载
            time.sleep(3)
            
            # 填写标题
            title_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="title"], #title, [placeholder*="标题"]')
            title_input.clear()
            title_input.send_keys(title)
            self.log(f"填写标题: {title}")
            
            # 填写作者（如果有）
            try:
                author_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="author"], #author, [placeholder*="作者"]')
                author_input.clear()
                author_input.send_keys(author)
                self.log(f"填写作者: {author}")
            except:
                self.log("未找到作者输入框，跳过")
            
            # 切换到内容编辑器
            # 微信公众号使用富文本编辑器，需要特殊处理
            try:
                # 尝试通过iframe访问编辑器
                iframe = self.driver.find_element(By.CSS_SELECTOR, 'iframe.ueditor_iframe, iframe[id*="editor"]')
                self.driver.switch_to.frame(iframe)
                
                # 获取编辑器body
                editor_body = self.driver.find_element(By.CSS_SELECTOR, 'body')
                editor_body.clear()
                
                # 输入内容
                editor_body.send_keys(content)
                self.log("通过iframe填写内容")
                
                # 切换回主文档
                self.driver.switch_to.default_content()
                
            except:
                # 如果iframe方式失败，尝试其他方式
                self.log("iframe方式失败，尝试其他方式")
                
                # 尝试直接找到内容输入区域
                try:
                    content_area = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"], textarea[name="content"]')
                    content_area.clear()
                    
                    # 使用JavaScript设置内容
                    self.driver.execute_script("arguments[0].innerHTML = arguments[1];", content_area, content)
                    self.log("通过JavaScript设置内容")
                except:
                    self.log("内容填写失败，可能需要手动操作")
                    return False
            
            # 添加"由AI生成"标识
            try:
                # 在内容末尾添加标识
                self.driver.execute_script(f"""
                    var editor = document.querySelector('div[contenteditable="true"], [id*="editor"]');
                    if (editor) {{
                        editor.innerHTML += '<p style="color:#999;font-size:12px;margin-top:20px;">【本文由AI生成，仅供参考】</p>';
                    }}
                """)
                self.log("添加AI生成标识")
            except:
                pass
            
            self.log("✅ 表单填写完成")
            return True
            
        except Exception as e:
            self.log(f"填写表单失败: {e}")
            return False
    
    def publish_article(self, save_as_draft=True):
        """发布文章"""
        try:
            if save_as_draft:
                # 保存为草稿
                draft_btn = self.driver.find_element(By.CSS_SELECTOR, 'a[class*="draft"], button[class*="draft"], [onclick*="draft"]')
                draft_btn.click()
                self.log("点击保存草稿")
            else:
                # 直接发布
                publish_btn = self.driver.find_element(By.CSS_SELECTOR, 'a[class*="publish"], button[class*="publish"], [onclick*="publish"]')
                publish_btn.click()
                self.log("点击发布")
            
            # 等待操作完成
            time.sleep(5)
            
            # 检查是否成功
            success_indicator = self.driver.find_elements(By.XPATH, '//*[contains(text(), "成功") or contains(text(), "Success") or contains(text(), "保存")]')
            
            if success_indicator:
                self.log("✅ 文章保存/发布成功")
                return True
            else:
                self.log("⚠️  操作完成但未检测到成功提示")
                return True
                
        except Exception as e:
            self.log(f"发布操作失败: {e}")
            return False
    
    def generate_article_content(self, topic="健康食谱"):
        """生成文章内容"""
        # 基础模板
        templates = {
            "健康食谱": """🥗 一周健康食谱 | 科学搭配，轻松坚持

告别外卖焦虑！AI为您定制的7天健康食谱来了～

📊 设计原则：
✅ 营养均衡：蛋白质25-30%、碳水45-50%
✅ 操作简单：每餐≤30分钟
✅ 成本可控：每周150-200元

🗓️ 每日食谱亮点：

【周一】清爽启动
早餐：燕麦粥+水煮蛋+小番茄
午餐：鸡胸肉沙拉+糙米饭
晚餐：清蒸鲈鱼+蒜蓉西兰花

【周二】蛋白质日  
早餐：全麦吐司+豆浆+香蕉
午餐：牛肉炒西兰花+杂粮饭
晚餐：虾仁炒蛋+凉拌黄瓜

💡 智能小贴士：
1️⃣ 批量准备：周日洗切蔬菜，分装保鲜
2️⃣ 时间管理：早餐提前准备，晚餐30分钟搞定

📱 个性化服务：
回复关键词获取专属食谱

🎯 本周挑战：
完成7天健康饮食打卡！

健康饮食是长期的生活方式
从这一周开始，让AI成为您的私人营养师！

【本文由AI生成，仅供参考】""",
            
            "智能家居": """🏠 智能家居入门指南 | 打造未来生活

智能家居让生活更便捷、更安全、更节能！

🔧 基础设备推荐：
✅ 智能音箱：控制中心
✅ 智能灯泡：语音/APP控制
✅ 智能插座：传统电器智能化
✅ 智能门锁：安全便捷

🚀 入门方案（1000元内）：
1. 小米/天猫精灵智能音箱
2.  Yeelight智能灯泡
3. 小米智能插座
4. 基础传感器套装

💡 使用技巧：
• 设置自动化场景
• 语音控制优化
• 能源管理监控

【本文由AI生成，仅供参考】""",
            
            "效率工具": """⚡ 效率工具推荐 | 提升工作生产力

告别低效工作，这些工具让你事半功倍！

🛠️ 推荐工具：
✅ Notion：全能工作台
✅ Trello：项目管理
✅ Forest：专注计时
✅ Grammarly：写作助手

🎯 使用建议：
1. 选择适合的工具组合
2. 建立标准化流程
3. 定期复盘优化

【本文由AI生成，仅供参考】"""
        }
        
        # 获取模板或使用默认
        content = templates.get(topic, templates["健康食谱"])
        
        # 添加当前日期
        current_date = datetime.now().strftime("%Y年%m月%d日")
        content = f"{content}\n\n发布时间：{current_date}"
        
        return content
    
    def run_publish_flow(self, topic="健康食谱"):
        """运行完整的发布流程"""
        self.log("=" * 60)
        self.log(f"开始自动化发布流程 - 主题: {topic}")
        self.log("=" * 60)
        
        # 1. 设置浏览器
        if not self.setup_driver():
            return False
        
        try:
            # 2. 登录
            if not self.login_with_cookie():
                self.log("登录失败，结束流程")
                return False
            
            # 3. 导航到发布页面
            if not self.navigate_to_publish():
                self.log("无法进入发布页面，结束流程")
                return False
            
            # 4. 生成内容
            title = f"【AI生成】{topic} | {datetime.now().strftime('%m月%d日')}"
            content = self.generate_article_content(topic)
            
            # 5. 填写表单
            if not self.fill_article_form(title, content):
                self.log("表单填写失败")
                return False
            
            # 6. 发布（先保存为草稿）
            if not self.publish_article(save_as_draft=True):
                self.log("发布失败")
                return False
            
            self.log("=" * 60)
            self.log("✅ 自动化发布流程完成！")
            self.log("=" * 60)
            
            return True
            
        except Exception as e:
            self.log(f"发布流程异常: {e}")
            return False
        
        finally:
            # 关闭浏览器
            if self.driver:
                self.driver.quit()
                self.log("浏览器已关闭")
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def get_log_content(self):
        """获取日志内容"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return "日志文件不存在"

def main():
    """主函数"""
    print("微信公众号自动化发布系统")
    print("=" * 60)
    
    # 使用提供的cookie
    cookie = '''yyb_muid=2B8756D0CC606D17230640FFCD066CA9; qq_domain_video_guid_verify=f711a8b820ed8b46; _qimei_uuid42=1980f0103031005d70705ca172275dbe4f7ea59574; pgv_pvid=6690267565; _qimei_fingerprint=3bbf8076805400b4b8f93aeaa85beffb; _qimei_h38=2db8c4cf70705ca172275dbe0200000b01980f; _qimei_i_3=73fa6586c00b5189c19ff830588727e6a2eff0f21a080b8bbd8b200e2fc6716f693536943c89e2d8958a; _qimei_q32=0dee58a781ea1f94016c8fea38b19969; _qimei_q36=47147a99ba0b9e151e457b97300013019816; pac_uid=0_A6mWteTfYEtwp; omgid=0_A6mWteTfYEtwp; RK=kUR3WPjxUc; ptcz=36d12bb6af847e08ffa3c8e86b1a4e7f5602f84219105b35f6c92f188cf3aeff; _qimei_i_2=23c46886925b54dc909ef7620a8421e9a2efa1f0475f0685e6862f5b2693206d6263369c3088e4bdaa9d; _qimei_i_1=64c36b80c1085888c5c4a8375b8373e5a4bfa5f610590487e0dd7d582493206c616365953980eadc80b3f0e1; eas_sid=F1l7M723m2C8C1N7h0b0d9u8i1; ETCI=610ba8c5debc4b42867cf290db3cf2bb; msecToken=6451efbcf0d0854594dec795748fba06; logTrackKey=2286fa380b6e4073bad0