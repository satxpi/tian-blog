# 老田的博客

> 从小田变老田 — 个人静态博客，基于 Node.js + Nunjucks + Markdown 构建

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 构建站点

```bash
node build.mjs
```

### 3. 本地预览

```bash
node build.mjs --serve
# 浏览器打开 http://localhost:8080/index.html
```

---

## 项目结构

```
tian-blog/
├── build.mjs               # 构建脚本（核心）
├── config.yaml             # 站点配置（域名、AdSense ID 等）
├── package.json
│
├── content/
│   ├── posts/              # 博客文章（Markdown）
│   │   └── YYYY-MM-DD-slug.md
│   └── collections.yaml    # 合集定义
│
├── templates/              # Nunjucks HTML 模板
│   ├── base.html           # 公共布局（头尾、导航、Cookie 横幅）
│   ├── index.html          # 首页
│   ├── post.html           # 文章详情页
│   ├── archive.html        # 归档页
│   ├── collection.html     # 合集详情页
│   ├── collections_index.html # 合集列表页
│   ├── about.html          # 关于页
│   └── privacy.html        # 隐私政策（Google AdSense 必需）
│
├── static/
│   ├── css/style.css       # 主样式
│   ├── js/main.js          # 交互脚本
│   └── images/             # 图片资源
│
└── output/                 # 构建产物（部署此目录）
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

---

## 配置 Google AdSense

1. 申请 Google AdSense 账号并获得审核通过
2. 修改 `config.yaml` 中的 `adsense_publisher_id`
3. 全局替换所有模板文件中的 `ca-pub-XXXXXXXXXXXXXXXX` 为你的真实 ID
4. 全局替换广告位中的 `data-ad-slot="XXXXXXXXXX"` 为你的广告单元 ID

### AdSense 合规要求

本项目已内置：
- ✅ 隐私政策页面 (`privacy.html`)
- ✅ Cookie 同意横幅（首次访问弹出）
- ✅ `robots.txt` 和 `sitemap.xml` 自动生成
- ✅ 广告旁边无违禁内容
- ✅ `<meta name="robots" content="index, follow">` 确保内容可索引

---

## 部署

推送 `main` 分支到 GitHub，GitHub Actions 会自动构建并部署到 GitHub Pages。

如需手动部署，构建后将 `output/` 目录部署到任意静态托管：
- **GitHub Pages** — 自动（push 即部署）
- **Vercel / Netlify** — 连接仓库，构建命令 `node build.mjs --prod`，输出目录 `output`
- **Cloudflare Pages** — 同上
- **任意静态托管** — 上传 `output/` 目录

---

## License

MIT — 随便用，欢迎改
