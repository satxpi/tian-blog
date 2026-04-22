# TOOLS.md - 工具速查

*精简版，详细配置见 memory/infra.md*

---

## 🔑 微信公众号凭证

export WECHAT_APP_ID=wx4d76a79c84e3ebbc
export WECHAT_APP_SECRET=72d4248a0d0384384884116ff2470e06

---

## 📁 目录结构

```
workspace/
├── scripts/wechat/     公众号脚本
│   ├── wechat_daily_publish.py    每天8点日常文章
│   ├── yijing_publisher.py        每天9点易经章节
│   ├── wechat_robust_publish.py   API发布工具类
│   └── ...其他旧脚本
├── articles/
│   ├── yijing/         易经系列md文件
│   └── daily/          日常文章存档
├── config/             配置文件（公众号凭证、易经状态等）
├── archive/            归档旧文件
├── stock/             股票日记网站（systemd服务依赖此路径）
├── scripts/stock/     股票监控脚本
├── memory/             记忆存储
└── skills/             技能目录
```

---

## 🔧 定时任务

| 时间 | 任务 | 脚本 |
|------|------|------|
| 每天8:00 | 日常文章→草稿箱 | scripts/wechat/wechat_daily_publish.py |
| 每天9:00 | 易经章节→草稿箱 | scripts/wechat/yijing_publisher.py |
| 开机 | 股票日记监控 | /root/stock_diary_monitor_simple.sh |

---

## ⚠️ 重要规则

- **绝不删草稿箱内容** — 用户自己判断删不删
- **提交不用问** — 直接提交
- **标题格式** — 闲聊易经｜01开篇：...
- **结尾** — 8点日常文章：只加AI标识，不加"以上均为个人观点"；9点易经文章：加"以上均为个人观点，如有错误的地方，还请海涵。"+AI标识
- **不预告下一篇**

---

## 📝 技能速查

**必用技能**：
| 名称 | 用途 |
|------|------|
| self-improving-agent | 记录错误和学习 |
| tavily-search | AI搜索 |

**备用技能**：
| 名称 | 用途 |
|------|------|
| summarize | URL摘要 |
| weather | 天气查询 |

---

*更新：2026-04-21*
