# 老田的博客

> 从小田变老田 — 个人静态博客，基于 Python + Jinja2 + Markdown 构建

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 构建站点

```bash
python build.py
```

### 3. 本地预览

```bash
python build.py --serve
# 浏览器打开 http://localhost:8080/index.html
```

---

## 项目结构

```
tian-blog/
├── build.py                 # 构建脚本（核心）
├── config.yaml              # 站点配置（域名、AdSense ID 等）
├── requirements.txt
│
├── content/
│   ├── posts/               # 博客文章（Markdown）
│   │   └── YYYY-MM-DD-slug.md
│   └── collections.yaml     # 合集定义
│
├── templates/               # Jinja2 HTML 模板
│   ├── base.html            # 公共布局（头尾、导航、Cookie 横幅）
│   ├── index.html           # 首页
│   ├── post.html            # 文章详情页
│   ├── archive.html         # 归档页
│   ├── collection.html      # 合集详情页
│   ├── collections_index.html # 合集列表页
│   ├── about.html           # 关于页
│   └── privacy.html         # 隐私政策（Google AdSense 必需）
│
├── static/
│   ├── css/style.css        # 主样式
│   ├── js/main.js           # 交互脚本
│   └── images/              # 图片资源
│
└── output/                  # 构建产物（部署此目录）
```

---

## 写文章

在 `content/posts/` 目录创建 `.md` 文件，文件名格式建议为 `YYYY-MM-DD-slug.md`。

### Front Matter 字段

```yaml
---
title:      文章标题（必填）
date:       2025-01-01       # 日期（必填）
slug:       url-friendly-name # URL 标识符，默认用文件名
tags:       [标签1, 标签2]
collection: 合集名称         # 必须与 collections.yaml 中的 name 一致
excerpt:    自定义摘要（可选，默认取正文前120字）
featured:   true             # 是否在首页置顶（可选）
author:     老田
---

正文内容（支持标准 Markdown 语法）
```

---

## 添加合集

编辑 `content/collections.yaml`：

```yaml
collections:
  - slug:        my-collection   # URL 标识符
    name:        合集显示名称    # 与文章 collection 字段一致
    icon:        🎯             # Emoji 图标
    description: 合集描述文字
```

## License

MIT — 随便用，欢迎改
