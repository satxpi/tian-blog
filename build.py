#!/usr/bin/env python3
"""
老田的博客 - 静态站点生成器
用法: python build.py [--serve]
"""

import os
import re
import json
import shutil
import http.server
import threading
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ─── 依赖检查 ─────────────────────────────────────────────
try:
    import markdown
    from markdown.extensions import toc, fenced_code, tables, codehilite
except ImportError:
    print("安装依赖: pip install markdown")
    raise

try:
    import yaml
except ImportError:
    print("安装依赖: pip install pyyaml")
    raise

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("安装依赖: pip install jinja2")
    raise

# ─── 路径配置 ─────────────────────────────────────────────
ROOT        = Path(__file__).parent
CONTENT_DIR = ROOT / "content"
POSTS_DIR   = CONTENT_DIR / "posts"
TMPL_DIR    = ROOT / "templates"
STATIC_DIR  = ROOT / "static"
OUT_DIR     = ROOT / "output"
SITE_CONFIG = ROOT / "config.yaml"

# ─── 站点配置 ─────────────────────────────────────────────
def load_config():
    if SITE_CONFIG.exists():
        with open(SITE_CONFIG, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

# ─── Front Matter 解析 ────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def parse_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta = {}
    body = text
    m = FRONTMATTER_RE.match(text)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        body = text[m.end():]

    # 字段处理
    slug = meta.get("slug") or path.stem
    date_val = meta.get("date")
    if isinstance(date_val, datetime):
        date_str = date_val.strftime("%Y-%m-%d")
    else:
        date_str = str(date_val) if date_val else "1970-01-01"

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    # 生成 HTML
    md = markdown.Markdown(extensions=[
        "markdown.extensions.toc",
        "markdown.extensions.fenced_code",
        "markdown.extensions.tables",
        "markdown.extensions.nl2br",
        "markdown.extensions.meta",
    ], extension_configs={"toc": {"permalink": True}})
    content_html = md.convert(body)
    toc_html     = md.toc if hasattr(md, "toc") else ""

    # 摘要：正文前 120 字
    plain = re.sub(r"<[^>]+>", "", content_html)
    excerpt = meta.get("excerpt") or plain[:120].strip()

    # 阅读时间（中文约 300 字/分钟）
    word_count  = len(re.sub(r"\s+", "", plain))
    read_time   = max(1, round(word_count / 300))

    return {
        "slug":          slug,
        "title":         meta.get("title") or path.stem,
        "date":          date_str,
        "tags":          tags,
        "collection":    meta.get("collection") or "",
        "collection_slug": (meta.get("collection") or "").lower().replace(" ", "-"),
        "author":        meta.get("author") or "老田",
        "featured":      bool(meta.get("featured")),
        "excerpt":       excerpt,
        "content_html":  content_html,
        "toc_html":      toc_html,
        "read_time":     read_time,
        "url":           "",   # 构建时填充
    }

# ─── TOC → Jinja 变量 ─────────────────────────────────────
def build_toc_items(toc_html: str) -> str:
    """把 markdown 生成的 toc div 转成 <li> 列表项"""
    items = re.findall(r'<a href="(#[^"]+)">([^<]+)</a>', toc_html)
    li = []
    for href, label in items:
        cls = "toc-h3" if label.startswith("  ") else ""
        li.append(f'<li class="{cls}"><a href="{href}">{label.strip()}</a></li>')
    return "\n".join(li)

# ─── 合集配置 ─────────────────────────────────────────────
COLLECTIONS_FILE = CONTENT_DIR / "collections.yaml"

def load_collections() -> dict:
    if not COLLECTIONS_FILE.exists():
        return {}
    with open(COLLECTIONS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {c["slug"]: c for c in data.get("collections", [])}

# ─── 构建器 ───────────────────────────────────────────────
class BlogBuilder:
    def __init__(self, prod: bool = False):
        self.prod   = prod
        self.config = load_config()
        self.env    = Environment(loader=FileSystemLoader(str(TMPL_DIR)),
                                  autoescape=False)
        self.env.filters["format"] = lambda v, fmt: fmt % int(v)
        self.env.filters["zfill"] = lambda v, width: str(v).zfill(width)
        self.collections_meta = load_collections()
        self.base_url = self.config.get("base_url", "/")
        self.posts: list[dict] = []

    # ── 清理 & 复制静态文件 ──
    def clean_and_copy_static(self):
        if OUT_DIR.exists():
            shutil.rmtree(OUT_DIR)
        OUT_DIR.mkdir(parents=True)
        if STATIC_DIR.exists():
            shutil.copytree(STATIC_DIR, OUT_DIR / "static")
        print("✓ 静态文件已复制")

    # ── 加载所有 MD 文章 ──
    def load_posts(self):
        posts = []
        for md_file in sorted(POSTS_DIR.glob("*.md"), reverse=True):
            p = parse_post(md_file)
            p["url"] = f"posts/{p['slug']}.html"
            posts.append(p)
        self.posts = posts
        print(f"✓ 加载了 {len(posts)} 篇文章")

    # ── 基础模板渲染 ──
    def render_page(self, template_name: str, ctx: dict, out_path: Path, depth: int = 0):
        base_tmpl = self.env.get_template("base.html")
        content_tmpl = self.env.get_template(template_name)

        if self.prod:
            static_root = self.base_url + "static/"
            root_url    = self.base_url
        else:
            static_root = "../" * depth + "static/"
            root_url    = "../" * depth

        site_url = self.config.get("site_url", "")
        canonical = site_url.rstrip("/") + "/" + str(out_path.relative_to(OUT_DIR)).replace("\\", "/")

        content_html = content_tmpl.render(**ctx)
        page_html    = base_tmpl.render(
            content=content_html,
            static_root=static_root,
            root_url=root_url,
            canonical_url=canonical,
            year=datetime.now().year,
            **{k: v for k, v in ctx.items() if k not in ("content",)},
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

    # ── 构建文章页 ──
    def build_posts(self):
        posts_out = OUT_DIR / "posts"
        posts_out.mkdir(exist_ok=True)
        col_map: dict[str, list] = defaultdict(list)
        for p in self.posts:
            if p["collection"]:
                col_map[p["collection"]].append(p)

        for i, post in enumerate(self.posts):
            col_posts = col_map.get(post["collection"], [])
            toc_items = build_toc_items(post["toc_html"])
            ctx = {
                "title":           post["title"],
                "description":     post["excerpt"],
                "og_type":         "article",
                "post":            post,
                "toc":             toc_items,
                "collection_posts": col_posts if post["collection"] else [],
                "prev_post":       self.posts[i + 1] if i + 1 < len(self.posts) else None,
                "next_post":       self.posts[i - 1] if i > 0 else None,
            }
            self.render_page("post.html", ctx, posts_out / f"{post['slug']}.html", depth=1)
        print(f"✓ 构建了 {len(self.posts)} 篇文章页")

    # ── 构建合集页 ──
    def build_collections(self):
        col_dir = OUT_DIR / "collections"
        col_dir.mkdir(exist_ok=True)

        col_map: dict[str, list] = defaultdict(list)
        for p in self.posts:
            if p["collection"]:
                col_map[p["collection"]].append(p)

        collections_list = []
        for slug, meta in self.collections_meta.items():
            name = meta.get("name", slug)
            posts_in = col_map.get(name, [])
            col_obj = {
                "slug":        slug,
                "name":        name,
                "icon":        meta.get("icon", "📚"),
                "description": meta.get("description", ""),
                "count":       len(posts_in),
                "url":         f"collections/{slug}.html",
            }
            collections_list.append(col_obj)
            # 合集详情页
            ctx = {
                "title":       f"合集：{name}",
                "description": meta.get("description", ""),
                "collection":  col_obj,
                "posts":       posts_in,
            }
            self.render_page("collection.html", ctx, col_dir / f"{slug}.html", depth=1)

        # 补充未在 collections.yaml 中定义的合集
        for name, posts_in in col_map.items():
            slug = name.lower().replace(" ", "-")
            if slug not in self.collections_meta:
                col_obj = {
                    "slug": slug, "name": name, "icon": "📁",
                    "description": "", "count": len(posts_in),
                    "url": f"collections/{slug}.html",
                }
                collections_list.append(col_obj)
                ctx = {
                    "title": f"合集：{name}", "description": "",
                    "collection": col_obj, "posts": posts_in,
                }
                self.render_page("collection.html", ctx, col_dir / f"{slug}.html", depth=1)

        self.collections_list = collections_list
        # 合集索引
        ctx = {
            "title":       "文章合集",
            "description": "按主题整理的系列文章",
            "collections": collections_list,
        }
        self.render_page("collections_index.html", ctx, OUT_DIR / "collections.html")
        print(f"✓ 构建了 {len(collections_list)} 个合集页")

    # ── 构建首页 ──
    def build_index(self):
        featured = next((p for p in self.posts if p["featured"]), None)
        recent   = [p for p in self.posts if p is not featured][:6]
        years_writing = (datetime.now().year - int(self.posts[-1]["date"][:4])) if self.posts else 0
        ctx = {
            "title":             "首页",
            "description":       "老田的个人博客，记录从小田变老田的成长历程",
            "featured_post":     featured,
            "recent_posts":      recent,
            "collections":       getattr(self, "collections_list", [])[:4],
            "total_posts":       len(self.posts),
            "total_collections": len(getattr(self, "collections_list", [])),
            "years_writing":     years_writing,
        }
        self.render_page("index.html", ctx, OUT_DIR / "index.html")
        print("✓ 构建了首页")

    # ── 构建归档页 ──
    def build_archive(self):
        by_year = defaultdict(list)
        all_tags = set()
        for p in self.posts:
            yr = p["date"][:4]
            by_year[yr].append(p)
            all_tags.update(p["tags"])

        first_year = min(by_year.keys()) if by_year else str(datetime.now().year)
        ctx = {
            "title":         "归档",
            "description":   "全部文章列表",
            "posts_by_year": dict(sorted(by_year.items(), reverse=True)),
            "all_tags":      sorted(all_tags),
            "total_posts":   len(self.posts),
            "first_year":    first_year,
        }
        self.render_page("archive.html", ctx, OUT_DIR / "archive.html")
        print("✓ 构建了归档页")

    # ── 构建关于页 ──
    def build_about(self):
        ctx = {
            "title":       "关于老田",
            "description": "从小田变老田，一个普通人的成长与记录",
        }
        self.render_page("about.html", ctx, OUT_DIR / "about.html")

    # ── 构建隐私政策页 ──
    def build_privacy(self):
        ctx = {
            "title":        "隐私政策",
            "description":  "老田博客隐私政策",
            "last_updated": datetime.now().strftime("%Y 年 %m 月 %d 日"),
        }
        self.render_page("privacy.html", ctx, OUT_DIR / "privacy.html")

    # ── 生成 sitemap.xml ──
    def build_sitemap(self):
        site_url = self.config.get("site_url", "").rstrip("/")
        urls = [site_url + "/index.html",
                site_url + "/archive.html",
                site_url + "/collections.html",
                site_url + "/about.html"]
        for p in self.posts:
            urls.append(f"{site_url}/{p['url']}")
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            lines.append(f"  <url><loc>{u}</loc><changefreq>weekly</changefreq></url>")
        lines.append("</urlset>")
        (OUT_DIR / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
        print("✓ 生成了 sitemap.xml")

    # ── 生成 robots.txt ──
    def build_robots(self):
        site_url = self.config.get("site_url", "").rstrip("/")
        txt = f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n"
        (OUT_DIR / "robots.txt").write_text(txt, encoding="utf-8")
        print("✓ 生成了 robots.txt")

    # ── 全量构建 ──
    def build(self):
        print("\n🚀 开始构建...\n")
        t0 = datetime.now()
        self.clean_and_copy_static()
        self.load_posts()
        self.build_posts()
        self.build_collections()
        self.build_index()
        self.build_archive()
        self.build_about()
        self.build_privacy()
        self.build_sitemap()
        self.build_robots()
        elapsed = (datetime.now() - t0).total_seconds()
        print(f"\n✅ 构建完成！耗时 {elapsed:.2f}s  →  {OUT_DIR}\n")


# ─── 本地预览服务器 ────────────────────────────────────────
def serve(port=8080):
    os.chdir(OUT_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    httpd   = http.server.HTTPServer(("", port), handler)
    print(f"📡  预览地址: http://localhost:{port}/index.html\n  Ctrl+C 停止")
    httpd.serve_forever()


# ─── 入口 ─────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="老田博客构建器")
    parser.add_argument("--serve", action="store_true", help="构建后启动预览服务器")
    parser.add_argument("--prod", action="store_true", help="生产环境构建（使用绝对路径 base_url）")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    BlogBuilder(prod=args.prod).build()

    if args.serve:
        serve(args.port)
