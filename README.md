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
│   └── privacy.html        # 隐私政策
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
sequence:   1                # 合集内排序序号（可选，数字越小越靠前）
excerpt:    自定义摘要（可选，默认取正文前120字）
featured:   true             # 是否在首页置顶（可选）
author:     老田
---

正文内容（支持标准 Markdown 语法）
```

### 文章内嵌图片

图片放入 `static/images/` 目录，在 Markdown 中引用：

```markdown
![图片描述](/static/images/your-image.jpg)
```

也支持外部图床：

```markdown
![图片描述](https://example.com/image.png)
```

构建时 `static/images/` 自动复制到 `output/static/images/`。

---

## 添加合集

编辑 `content/collections.yaml`：

```yaml
collections:
  - slug:        my-collection   # URL 标识符
    name:        合集显示名称    # 与文章 collection 字段一致
    description: 合集描述文字
```

合集内文章默认按 `sequence` 字段升序排列；未设置 `sequence` 的按文件名/slug 升序。

---

## 管理后台

本地启动管理服务器，支持在线编辑 / 上传 Markdown 发布文章：

```bash
npm run admin
# 浏览器打开 http://localhost:8080/ins/
```

发布后自动触发构建，文章即时生效。线上静态站点不支持直接发布。

---

## License

MIT — 随便用，欢迎改
