#!/usr/bin/env node
/**
 * 老田的博客 - 管理服务器
 * 用法: node server.mjs [--port 8080]
 *   提供静态文件服务 + 文章发布 API
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import express from 'express';
import multer from 'multer';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT        = __dirname;
const POSTS_DIR   = join(ROOT, 'content', 'posts');
const OUT_DIR     = join(ROOT, 'output');
const PORT        = parseInt(process.argv[process.argv.indexOf('--port') + 1]) || (process.argv.includes('--port') ? 8080 : 8080);

// 确保 posts 目录存在
if (!existsSync(POSTS_DIR)) mkdirSync(POSTS_DIR, { recursive: true });

const app = express();

// ─── 中间件 ──────────────────────────────────────────
app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true, limit: '5mb' }));

// 管理页面 — 短路径入口
app.get(['/ins', '/ins/'], (req, res) => {
  const html = readFileSync(join(OUT_DIR, 'ins', 'index.html'), 'utf8');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.send(html);
});

// 静态文件
app.use(express.static(OUT_DIR));

// ─── 构建锁 ──────────────────────────────────────────
let isBuilding = false;
let buildQueue = Promise.resolve();

function runBuild() {
  buildQueue = buildQueue.then(() => {
    return new Promise((resolve) => {
      if (isBuilding) { resolve(); return; }
      isBuilding = true;
      try {
        execSync('node build.mjs', { cwd: ROOT, stdio: 'pipe', timeout: 60000 });
        console.log('✅ 自动构建完成');
      } catch (e) {
        console.error('❌ 构建失败:', e.stderr?.toString() || e.message);
      } finally {
        isBuilding = false;
        resolve();
      }
    });
  });
  return buildQueue;
}

// ─── 文件上传配置 ────────────────────────────────────
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, POSTS_DIR),
  filename: (req, file, cb) => {
    // 保留原始文件名
    const original = Buffer.from(file.originalname, 'latin1').toString('utf8');
    cb(null, original);
  }
});
const upload = multer({
  storage,
  fileFilter: (req, file, cb) => {
    if (file.originalname.endsWith('.md') || file.mimetype === 'text/markdown') {
      cb(null, true);
    } else {
      cb(new Error('只接受 .md Markdown 文件'));
    }
  },
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB
});

// ─── API：在线编辑发布 ───────────────────────────────
app.post('/api/publish', async (req, res) => {
  try {
    const { title, date, tags, collection, excerpt, content } = req.body;

    if (!title || !content) {
      return res.status(400).json({ error: '标题和内容不能为空' });
    }

    const postDate = date || new Date().toISOString().slice(0, 10);
    // 生成 slug：保留中英文数字，其余转连字符
    let slug = title
      .replace(/[^\w\u4e00-\u9fff\u3400-\u4dbf-]+/gu, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .toLowerCase();
    // 纯标点或空标题兜底
    if (!slug || slug.length < 2) slug = 'untitled-' + Date.now().toString(36);

    const filename = `${postDate}-${slug}.md`;

    // 构建 Front Matter
    let fm = `---
title: ${title}
date: ${postDate}
slug: ${slug}
`;
    if (tags) {
      const tagArr = tags.split(/[,，]/).map(t => t.trim()).filter(Boolean);
      fm += `tags: [${tagArr.join(', ')}]\n`;
    }
    if (collection) fm += `collection: ${collection}\n`;
    if (excerpt) fm += `excerpt: ${excerpt}\n`;
    fm += `author: 老田\n---\n\n${content}`;

    writeFileSync(join(POSTS_DIR, filename), fm, 'utf8');
    console.log(`📝 文章已保存: ${filename}`);

    // 触发构建
    runBuild();

    res.json({ success: true, filename, message: `文章「${title}」已发布！` });
  } catch (e) {
    console.error('发布失败:', e);
    res.status(500).json({ error: e.message });
  }
});

// ─── API：上传 MD 文件 ────────────────────────────────
app.post('/api/upload', upload.single('file'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '请选择一个 .md 文件' });
    }

    const filename = Buffer.from(req.file.originalname, 'latin1').toString('utf8');
    console.log(`📤 文件已上传: ${filename}`);

    // 触发构建
    runBuild();

    res.json({ success: true, filename, message: `文件「${filename}」已上传并发布！` });
  } catch (e) {
    console.error('上传失败:', e);
    res.status(500).json({ error: e.message });
  }
});

// ─── API：手动触发构建 ────────────────────────────────
app.post('/api/build', async (req, res) => {
  try {
    await runBuild();
    res.json({ success: true, message: '构建完成' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ─── 404 处理 ─────────────────────────────────────────
app.use((req, res) => {
  res.status(404).send('<h1>404 Not Found</h1>');
});

// ─── 启动 ─────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🔧 管理服务器已启动`);
  console.log(`   博客预览:  http://localhost:${PORT}`);
  console.log(`   管理页面:  http://localhost:${PORT}/ins/`);
  console.log(`   发布 API:  POST /api/publish`);
  console.log(`   上传 API:  POST /api/upload\n`);
});
