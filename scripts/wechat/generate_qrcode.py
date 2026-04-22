#!/usr/bin/env python3
import qrcode
import os
import time

# 生成微信公众号登录页面的二维码
url = "https://mp.weixin.qq.com"

# 创建二维码
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)

qr.add_data(url)
qr.make(fit=True)

# 生成二维码图片
img = qr.make_image(fill_color="black", back_color="white")

# 保存图片
timestamp = int(time.time())
filename = f"/tmp/weixin_login_qrcode_{timestamp}.png"
img.save(filename)

print(f"二维码已生成: {filename}")
print(f"二维码内容: {url}")
print(f"文件大小: {os.path.getsize(filename)} bytes")

# 显示文件信息
print("\n请用微信扫描此二维码，然后访问微信公众号平台登录。")