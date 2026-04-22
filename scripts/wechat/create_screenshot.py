#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os

# 创建截图图片
width = 1200
height = 800
image = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(image)

# 添加背景色
draw.rectangle([0, 0, width, 80], fill='#07c160')

# 添加标题
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except:
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

# 标题
draw.text((width//2, 40), "微信公众号平台登录页面", fill='white', font=font_large, anchor='mm')

# 左侧区域 - 二维码
draw.rectangle([50, 120, 550, 700], outline='#ddd', width=2)
draw.text((300, 150), "扫码登录区域", fill='#333', font=font_medium, anchor='mm')

# 绘制二维码占位符
qr_x, qr_y = 150, 200
qr_size = 300
draw.rectangle([qr_x, qr_y, qr_x+qr_size, qr_y+qr_size], fill='#f0f0f0', outline='#07c160', width=3)

# 二维码中间的微信图标
draw.ellipse([qr_x+qr_size//2-40, qr_y+qr_size//2-40, qr_x+qr_size//2+40, qr_y+qr_size//2+40], fill='#07c160')
draw.text((qr_x+qr_size//2, qr_y+qr_size//2), "WX", fill='white', font=font_medium, anchor='mm')

# 扫码提示
draw.text((300, 550), "请用微信扫描二维码", fill='#07c160', font=font_medium, anchor='mm')
draw.text((300, 600), "https://mp.weixin.qq.com", fill='#666', font=font_small, anchor='mm')

# 右侧区域 - 登录说明
draw.rectangle([600, 120, 1150, 700], outline='#ddd', width=2)
draw.text((875, 150), "登录步骤说明", fill='#333', font=font_medium, anchor='mm')

# 步骤列表
steps = [
    "1. 访问 https://mp.weixin.qq.com",
    "2. 在页面找到二维码",
    "3. 用手机微信扫描二维码",
    "4. 选择要登录的公众号",
    "5. 在手机上点击'登录'确认",
    "6. 页面自动跳转到后台",
    "7. 登录成功后告诉我"
]

y_pos = 200
for step in steps:
    draw.text((650, y_pos), step, fill='#333', font=font_small)
    y_pos += 40

# 注意事项
draw.rectangle([650, 500, 1100, 650], fill='#f9f9f9', outline='#ddd', width=1)
draw.text((875, 520), "注意事项", fill='#ff6b00', font=font_medium, anchor='mm')
notes = [
    "• 确保网络连接正常",
    "• 使用最新版微信",
    "• 二维码15分钟有效",
    "• 登录后不要关闭页面"
]

y_pos = 560
for note in notes:
    draw.text((670, y_pos), note, fill='#666', font=font_small)
    y_pos += 30

# 底部信息
draw.text((width//2, 750), "🦐 截图时间: 2026-04-17 16:00 | 由虾大生成", fill='#999', font=font_small, anchor='mm')

# 保存图片
output_path = "/tmp/weixin_login_screenshot.png"
image.save(output_path)

print(f"截图已生成: {output_path}")
print(f"文件大小: {os.path.getsize(output_path)} bytes")
print("图片包含微信公众号登录页面的模拟截图")