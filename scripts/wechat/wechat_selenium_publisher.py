                    self.log("表单填写不完整，但继续尝试保存")
                
                # 截图：填写后
                self.take_screenshot("after_fill")
                
                # 6. 保存为草稿
                if self.save_as_draft():
                    self.log("✅ 文章已保存为草稿")
                    
                    # 截图：保存后
                    self.take_screenshot("after_save")
                    
                    # 保存成功信息
                    success_file = self.backup_dir / f"success_{int(time.time())}.json"
                    success_data = {
                        "timestamp": datetime.now().isoformat(),
                        "topic": topic,
                        "title": title,
                        "status": "draft_saved",
                        "screenshots": [
                            str(self.take_screenshot("final")) if self.take_screenshot("final") else None
                        ]
                    }
                    
                    with open(success_file, 'w', encoding='utf-8') as f:
                        json.dump(success_data, f, ensure_ascii=False, indent=2)
                    
                    self.log(f"✅ 发布流程完成，信息已保存: {success_file}")
                    return True
                else:
                    self.log("❌ 保存失败")
                    
                    # 保存失败信息
                    error_file = self.backup_dir / f"error_{int(time.time())}.json"
                    error_data = {
                        "timestamp": datetime.now().isoformat(),
                        "topic": topic,
                        "title": title,
                        "status": "save_failed",
                        "page_url": self.driver.current_url,
                        "page_title": self.driver.title
                    }
                    
                    with open(error_file, 'w', encoding='utf-8') as f:
                        json.dump(error_data, f, ensure_ascii=False, indent=2)
                    
                    return False
                    
            finally:
                # 关闭浏览器
                if self.driver:
                    self.driver.quit()
                    self.log("浏览器已关闭")
        
        except Exception as e:
            self.log(f"❌ 发布流程异常: {e}")
            
            # 保存异常信息
            try:
                error_file = self.backup_dir / f"exception_{int(time.time())}.json"
                error_data = {
                    "timestamp": datetime.now().isoformat(),
                    "topic": topic if 'topic' in locals() else "unknown",
                    "error": str(e),
                    "status": "exception"
                }
                
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump(error_data, f, ensure_ascii=False, indent=2)
            except:
                pass
            
            return False
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def get_status(self):
        """获取系统状态"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "cookie_exists": self.cookie_file.exists(),
            "cookie_size": self.cookie_file.stat().st_size if self.cookie_file.exists() else 0,
            "content_files": len(list(self.content_dir.glob("*.txt"))) if self.content_dir.exists() else 0,
            "backup_files": len(list(self.backup_dir.glob("*.json"))) if self.backup_dir.exists() else 0,
            "log_size": self.log_file.stat().st_size if self.log_file.exists() else 0
        }
        
        # 读取最新日志
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    status["recent_logs"] = lines[-10:] if len(lines) > 10 else lines
            except:
                status["recent_logs"] = []
        
        return status

def main():
    """主函数"""
    print("微信公众号Selenium自动化发布系统")
    print("=" * 60)
    
    # 创建发布器
    publisher = WeChatSeleniumPublisher()
    
    # 检查cookie
    if not publisher.cookie_file.exists():
        print("❌ Cookie文件不存在")
        print(f"请将cookie保存到: {publisher.cookie_file}")
        print("获取cookie方法:")
        print("1. 登录 https://mp.weixin.qq.com")
        print("2. 按F12打开开发者工具")
        print("3. 复制Network中的Cookie")
        print("4. 保存到上述文件")
        return
    
    # 运行发布流程
    print("开始自动化发布流程...")
    success = publisher.run_publish_flow()
    
    # 输出状态
    status = publisher.get_status()
    print("\n" + "=" * 60)
    print("系统状态:")
    print(f"Cookie文件: {'✅ 存在' if status['cookie_exists'] else '❌ 不存在'}")
    print(f"Cookie大小: {status['cookie_size']} 字节")
    print(f"内容文件数: {status['content_files']}")
    print(f"备份文件数: {status['backup_files']}")
    print(f"日志大小: {status['log_size']} 字节")
    
    if success:
        print("\n🎉 自动化发布流程完成！")
        print("文章已保存为草稿，请登录公众号后台确认并发布。")
    else:
        print("\n⚠️  发布流程需要手动干预")
        print("请检查日志和截图，或手动发布文章。")
    
    print("\n日志文件:", publisher.log_file)
    print("备份目录:", publisher.backup_dir)
    print("=" * 60)

if __name__ == "__main__":
    main()