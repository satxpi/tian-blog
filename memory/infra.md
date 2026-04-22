# 基础设施配置

## 服务器
- **主机**: VM-0-6-ubuntu
- **公网IP**: 见 keys.md

---

## 股市日记网站
- **路径**: `/root/.openclaw/workspace/stock/`
- **访问地址**: `http://IP/stock/` ⚠️ 注意不是根目录
- **端口**: 80
- **启动命令**: `cd /root/.openclaw/workspace/stock && nohup python3 server.py > /tmp/stock.log 2>&1 &`
- **日志**: `/tmp/stock.log`
- **PID检查**: `ps aux | grep server.py`

---

*更新: 2026-03-30*
