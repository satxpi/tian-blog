#!/usr/bin/env node
/**
 * 老田的博客 - 静态站点生成器 (Node.js)
 * 用法: node build.mjs [--serve] [--prod]
 */

import { readFileSync, writeFileSync, readdirSync, mkdirSync, rmSync, cpSync, existsSync } from 'fs';
import { join, dirname, relative } from 'path';
import { fileURLToPath } from 'url';
import { createServer } from 'http';
import { extname } from 'path';
import { marked } from 'marked';
import nunjucks from 'nunjucks';
import { load as yamlLoad } from 'js-yaml';
import hljs from 'highlight.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT         = __dirname;
const CONTENT_DIR  = join(ROOT, 'content');
const POSTS_DIR    = join(CONTENT_DIR, 'posts');
const TMPL_DIR     = join(ROOT, 'templates');
const STATIC_DIR   = join(ROOT, 'static');
const OUT_DIR      = join(ROOT, 'output');
const SITE_CONFIG  = join(ROOT, 'config.yaml');
const COLLECTIONS_FILE = join(CONTENT_DIR, 'collections.yaml');

// ─── marked 配置 ───────────────────────────────────────
marked.setOptions({
  headerIds: true,
  headerPrefix: '',
  breaks: true,
  gfm: true,
});

// 自定义渲染器：代码高亮
const renderer = new marked.Renderer();
renderer.code = function({ text, lang }) {
  if (lang && hljs.getLanguage(lang)) {
    const highlighted = hljs.highlight(text, { language: lang }).value;
    return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`;
  }
  return `<pre><code>${text}</code></pre>`;
};
marked.use({ renderer });

// ─── 辅助函数 ─────────────────────────────────────────

function loadYaml(path) {
  if (!existsSync(path)) return {};
  return yamlLoad(readFileSync(path, 'utf8')) || {};
}

function slugify(text) {
  return text.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9\u4e00-\u9fff\-]/gu, '');
}

// ─── Front Matter 解析 ────────────────────────────────
const FRONTMATTER_RE = /^---\s*\n(.*?)\n---\s*\n/s;

function parsePost(filePath) {
  const text = readFileSync(filePath, 'utf8');
  let meta = {};
  let body = text;
  const m = text.match(FRONTMATTER_RE);
  if (m) {
    try { meta = yamlLoad(m[1]) || {}; } catch (e) { meta = {}; }
    body = text.slice(m[0].length);
  }

  const fname  = filePath.split(/[\\/]/).pop().replace(/\.md$/, '');
  const slug   = meta.slug || fname;
  const dateStr = meta.date ? String(meta.date).slice(0, 10) : '1970-01-01';
  let tags = meta.tags || [];
  if (typeof tags === 'string') tags = tags.split(',').map(t => t.trim()).filter(Boolean);

  // Markdown → HTML
  const contentHtml = marked.parse(body);
  // 提取标题生成 TOC
  const tocItems = extractToc(contentHtml);
  const tocHtml   = buildTocHtml(tocItems);

  // 摘要
  const plain = contentHtml.replace(/<[^>]+>/g, '');
  const excerpt = meta.excerpt || plain.slice(0, 120).trim();

  // 阅读时间
  const wordCount = plain.replace(/\s+/g, '').length;
  const readTime  = Math.max(1, Math.round(wordCount / 300));

  const collection = meta.collection || '';
  return {
    slug, title: meta.title || fname,
    date: dateStr, date_month_day: dateStr.slice(5),
    date_year: dateStr.slice(0, 4),
    tags, collection,
    collection_slug: collection.toLowerCase().replace(/\s+/g, '-'),
    author: meta.author || '老田',
    featured: !!meta.featured,
    excerpt, content_html: contentHtml,
    toc_html: tocHtml, toc_items: tocItems,
    read_time: readTime,
    url: '', // 填入 build 阶段
  };
}

function extractToc(html) {
  const re = /<h(\d)\s+id="([^"]*)"[^>]*>([^<]*)<\/h\1>/gi;
  const items = [];
  let m;
  while ((m = re.exec(html)) !== null) {
    items.push({ level: parseInt(m[1]), id: m[2], text: m[3].replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"') });
  }
  return items;
}

function buildTocHtml(items) {
  return items.map(item => {
    const cls = item.level === 3 ? ' class="toc-h3"' : '';
    return `<li${cls}><a href="#${item.id}">${item.text}</a></li>`;
  }).join('\n');
}

// ─── 合集加载 ─────────────────────────────────────────
function loadCollections() {
  if (!existsSync(COLLECTIONS_FILE)) return {};
  const data = loadYaml(COLLECTIONS_FILE);
  const map = {};
  for (const c of (data.collections || [])) {
    map[c.slug] = c;
  }
  return map;
}

// ─── Nunjucks 环境初始化 ──────────────────────────────
function createEnv(autoescape = false) {
  const env = nunjucks.configure(TMPL_DIR, { autoescape, noCache: true });

  // 自定义 filter
  env.addFilter('pad', (str, len, char = '0') => String(str).padStart(len, char));
  env.addFilter('slice', (str, start, end) => String(str).slice(start, end));
  env.addFilter('format', (v, fmt) => fmt.replace('%s', v));
  env.addFilter('default', (v, fallback) => (v === undefined || v === null || v === '') ? fallback : v);
  env.addFilter('string', v => String(v));

  return env;
}

// ─── MIME 类型 ────────────────────────────────────────
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.xml':  'application/xml; charset=utf-8',
  '.txt':  'text/plain; charset=utf-8',
};

// ══════════════════════════════════════════════════════════
//  构建器
// ══════════════════════════════════════════════════════════

class BlogBuilder {
  constructor(prod = false) {
    this.prod    = prod;
    this.config  = loadYaml(SITE_CONFIG);
    this.env     = createEnv();
    this.collectionsMeta = loadCollections();
    this.baseUrl = this.config.base_url || '/';
    this.domain  = this.config.domain || '';
    this.posts   = [];
    this.collectionsList = [];
  }

  // ── 清理 & 复制静态文件 ──
  cleanAndCopyStatic() {
    if (existsSync(OUT_DIR)) rmSync(OUT_DIR, { recursive: true });
    mkdirSync(OUT_DIR, { recursive: true });
    if (existsSync(STATIC_DIR)) {
      cpSync(STATIC_DIR, join(OUT_DIR, 'static'), { recursive: true });
    }
    console.log('✓ 静态文件已复制');
  }

  // ── 加载所有 MD 文章 ──
  loadPosts() {
    const files = readdirSync(POSTS_DIR).filter(f => f.endsWith('.md')).sort().reverse();
    this.posts = files.map(f => {
      const p = parsePost(join(POSTS_DIR, f));
      p.url = `posts/${p.slug}.html`;
      return p;
    });
    console.log(`✓ 加载了 ${this.posts.length} 篇文章`);
  }

  // ── 渲染页面 ──
  renderPage(templateName, ctx, outPath, depth = 0) {
    const baseTpl    = this.env.getTemplate('base.html');
    const contentTpl = this.env.getTemplate(templateName);

    let staticRoot, rootUrl;
    if (this.prod) {
      staticRoot = this.baseUrl + 'static/';
      rootUrl    = this.baseUrl;
    } else {
      staticRoot = '../'.repeat(depth) + 'static/';
      rootUrl    = '../'.repeat(depth);
    }

    const siteUrl = (this.config.site_url || '').replace(/\/$/, '');
    let relPath = relative(OUT_DIR, outPath).replace(/\\/g, '/');
    const canonical = siteUrl + '/' + relPath;

    const contentHtml = contentTpl.render(ctx);
    const pageHtml = baseTpl.render({
      ...ctx,
      content: contentHtml,
      static_root: staticRoot,
      root_url: rootUrl,
      canonical_url: canonical,
      year: new Date().getFullYear(),
    });

    const dir = dirname(outPath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(outPath, pageHtml, 'utf8');
  }

  // ── 构建文章页 ──
  buildPosts() {
    const postsOut = join(OUT_DIR, 'posts');
    mkdirSync(postsOut, { recursive: true });

    // 按合集分组
    const colMap = {};
    for (const p of this.posts) {
      if (p.collection) {
        if (!colMap[p.collection]) colMap[p.collection] = [];
        colMap[p.collection].push(p);
      }
    }

    for (let i = 0; i < this.posts.length; i++) {
      const post = this.posts[i];
      const colPosts = colMap[post.collection] || [];
      const tocHtml = post.toc_html;

      let prevPost = null, nextPost = null;
      if (i + 1 < this.posts.length) prevPost = this.posts[i + 1];
      if (i > 0) nextPost = this.posts[i - 1];

      const ctx = {
        title: post.title,
        description: post.excerpt,
        og_type: 'article',
        post, toc: tocHtml,
        collection_posts: post.collection ? colPosts : [],
        prev_post: prevPost, next_post: nextPost,
      };
      this.renderPage('post.html', ctx, join(postsOut, `${post.slug}.html`), 1);
    }
    console.log(`✓ 构建了 ${this.posts.length} 篇文章页`);
  }

  // ── 构建合集页 ──
  buildCollections() {
    const colDir = join(OUT_DIR, 'collections');
    mkdirSync(colDir, { recursive: true });

    // 按合集分组
    const colMap = {};
    for (const p of this.posts) {
      if (p.collection) {
        if (!colMap[p.collection]) colMap[p.collection] = [];
        colMap[p.collection].push(p);
      }
    }

    this.collectionsList = [];

    // 处理 yaml 中定义的合集
    for (const [slug, meta] of Object.entries(this.collectionsMeta)) {
      const name     = meta.name || slug;
      const postsIn  = colMap[name] || [];
      const colObj = {
        slug, name, icon: meta.icon || '📚',
        description: meta.description || '',
        count: postsIn.length,
        url: `collections/${slug}.html`,
      };
      this.collectionsList.push(colObj);

      const ctx = {
        title: `合集：${name}`,
        description: meta.description || '',
        collection: colObj,
        posts: postsIn,
      };
      this.renderPage('collection.html', ctx, join(colDir, `${slug}.html`), 1);
    }

    // 补充未定义的合集
    for (const [name, postsIn] of Object.entries(colMap)) {
      const slug = name.toLowerCase().replace(/\s+/g, '-');
      if (this.collectionsMeta[slug]) continue;
      // 也检查是否已由 yaml 定义（通过 name 匹配）
      if (Object.values(this.collectionsMeta).some(m => m.name === name)) continue;

      const colObj = {
        slug, name, icon: '📁',
        description: '', count: postsIn.length,
        url: `collections/${slug}.html`,
      };
      this.collectionsList.push(colObj);

      const ctx = {
        title: `合集：${name}`, description: '',
        collection: colObj, posts: postsIn,
      };
      this.renderPage('collection.html', ctx, join(colDir, `${slug}.html`), 1);
    }

    // 合集索引
    const ctx = {
      title: '文章合集',
      description: '按主题整理的系列文章',
      collections: this.collectionsList,
    };
    this.renderPage('collections_index.html', ctx, join(OUT_DIR, 'collections.html'));
    console.log(`✓ 构建了 ${this.collectionsList.length} 个合集页`);
  }

  // ── 构建首页 ──
  buildIndex() {
    const featured = this.posts.find(p => p.featured) || null;
    const recent   = this.posts.filter(p => p !== featured).slice(0, 6);
    const lastPost = this.posts[this.posts.length - 1];
    const yearsWriting = lastPost ? new Date().getFullYear() - parseInt(lastPost.date.slice(0, 4)) : 0;

    const ctx = {
      title: '首页',
      description: '老田的个人博客，记录从小田变老田的成长历程',
      featured_post: featured,
      recent_posts: recent,
      collections: this.collectionsList.slice(0, 4),
      total_posts: this.posts.length,
      total_collections: this.collectionsList.length,
      years_writing: yearsWriting,
    };
    this.renderPage('index.html', ctx, join(OUT_DIR, 'index.html'));
    console.log('✓ 构建了首页');
  }

  // ── 构建归档页 ──
  buildArchive() {
    const byYear = {};
    const allTags = new Set();
    for (const p of this.posts) {
      const yr = p.date.slice(0, 4);
      if (!byYear[yr]) byYear[yr] = [];
      byYear[yr].push(p);
      p.tags.forEach(t => allTags.add(t));
    }

    const sortedYears = Object.keys(byYear).sort((a, b) => b - a);
    const postsByYear = {};
    for (const yr of sortedYears) postsByYear[yr] = byYear[yr];

    const firstYear = sortedYears.length ? sortedYears[sortedYears.length - 1] : String(new Date().getFullYear());

    const ctx = {
      title: '归档',
      description: '全部文章列表',
      posts_by_year: postsByYear,
      all_tags: [...allTags].sort(),
      total_posts: this.posts.length,
      first_year: firstYear,
    };
    this.renderPage('archive.html', ctx, join(OUT_DIR, 'archive.html'));
    console.log('✓ 构建了归档页');
  }

  // ── 构建关于页 ──
  buildAbout() {
    this.renderPage('about.html', {
      title: '关于老田',
      description: '从小田变老田，一个普通人的成长与记录',
    }, join(OUT_DIR, 'about.html'));
  }

  // ── 构建隐私政策页 ──
  buildPrivacy() {
    const now = new Date();
    const lastUpdated = `${now.getFullYear()} 年 ${String(now.getMonth() + 1).padStart(2, '0')} 月 ${String(now.getDate()).padStart(2, '0')} 日`;
    this.renderPage('privacy.html', {
      title: '隐私政策',
      description: '老田博客隐私政策',
      last_updated: lastUpdated,
    }, join(OUT_DIR, 'privacy.html'));
  }

  // ── sitemap.xml ──
  buildSitemap() {
    const siteUrl = (this.config.site_url || '').replace(/\/$/, '');
    const urls = [
      `${siteUrl}/index.html`, `${siteUrl}/archive.html`,
      `${siteUrl}/collections.html`, `${siteUrl}/about.html`,
    ];
    for (const p of this.posts) urls.push(`${siteUrl}/${p.url}`);
    for (const col of this.collectionsList) urls.push(`${siteUrl}/${col.url}`);

    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
      urls.map(u => `  <url><loc>${u}</loc><changefreq>weekly</changefreq></url>`).join('\n') +
      `\n</urlset>\n`;
    writeFileSync(join(OUT_DIR, 'sitemap.xml'), xml, 'utf8');
    console.log('✓ 生成了 sitemap.xml');
  }

  // ── robots.txt ──
  buildRobots() {
    const siteUrl = (this.config.site_url || '').replace(/\/$/, '');
    writeFileSync(join(OUT_DIR, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${siteUrl}/sitemap.xml\n`, 'utf8');
    console.log('✓ 生成了 robots.txt');
    // 禁止 GitHub Pages 用 Jekyll 处理
    writeFileSync(join(OUT_DIR, '.nojekyll'), '');
    console.log('✓ 生成 .nojekyll');
    // CNAME 自定义域名
    if (this.domain) {
      writeFileSync(join(OUT_DIR, 'CNAME'), this.domain + '\n', 'utf8');
      console.log(`✓ 生成 CNAME → ${this.domain}`);
    }
  }

  // ── 全量构建 ──
  build() {
    const t0 = performance.now();
    console.log('\n🚀 开始构建...\n');
    this.cleanAndCopyStatic();
    this.loadPosts();
    this.buildPosts();
    this.buildCollections();
    this.buildIndex();
    this.buildArchive();
    this.buildAbout();
    this.buildPrivacy();
    this.buildSitemap();
    this.buildRobots();
    const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
    console.log(`\n✅ 构建完成！耗时 ${elapsed}s  →  ${OUT_DIR}\n`);
  }
}

// ─── 本地预览服务器 ───────────────────────────────────
function serve(port = 8080) {
  process.chdir(OUT_DIR);
  const server = createServer((req, res) => {
    let filePath = req.url === '/' ? '/index.html' : req.url;
    const fullPath = join(OUT_DIR, filePath);
    const ext = extname(fullPath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    if (existsSync(fullPath)) {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(readFileSync(fullPath));
    } else {
      res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<h1>404 Not Found</h1>');
    }
  });

  server.listen(port, () => {
    console.log(`📡 预览地址: http://localhost:${port}/index.html\n  Ctrl+C 停止`);
  });
  return server;
}

// ─── 入口 ─────────────────────────────────────────────
const args = process.argv.slice(2);
const isServe = args.includes('--serve') || args.includes('-s');
const isProd  = args.includes('--prod') || args.includes('-p');
const portIdx = args.indexOf('--port');
const port    = portIdx !== -1 ? parseInt(args[portIdx + 1]) || 8080 : 8080;

const builder = new BlogBuilder(isProd);
builder.build();

if (isServe) {
  serve(port);
}
