/**
 * 老田的博客 - 主 JS
 */

// ── Cookie 同意 ──
(function () {
  const banner = document.getElementById('cookie-banner');
  if (!banner) return;
  if (localStorage.getItem('cookie_ok')) {
    banner.remove();
    return;
  }
  document.getElementById('btn-accept-cookie').addEventListener('click', () => {
    localStorage.setItem('cookie_ok', '1');
    banner.style.opacity = '0';
    banner.style.transition = 'opacity 0.3s';
    setTimeout(() => banner.remove(), 300);
  });
})();

// ── 目录（TOC）高亮 ──
(function () {
  const tocLinks = document.querySelectorAll('.toc-list a');
  if (!tocLinks.length) return;

  const headings = Array.from(document.querySelectorAll('.article-body h2, .article-body h3'));
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        tocLinks.forEach(l => l.classList.remove('active'));
        const id = entry.target.id;
        const link = document.querySelector(`.toc-list a[href="#${id}"]`);
        if (link) link.classList.add('active');
      }
    });
  }, { rootMargin: '0px 0px -60% 0px' });

  headings.forEach(h => observer.observe(h));
})();

// ── 给标题自动生成 id（供 TOC 跳转） ──
(function () {
  const body = document.querySelector('.article-body');
  if (!body) return;
  const headings = body.querySelectorAll('h2, h3');
  headings.forEach((h, i) => {
    if (!h.id) {
      h.id = 'section-' + i;
    }
  });
})();

// ── 阅读进度条 ──
(function () {
  const bar = document.createElement('div');
  bar.id = 'reading-progress';
  bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;background:#ff4d00;width:0%;z-index:9999;transition:width 0.1s;';
  document.body.prepend(bar);

  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    const total = document.body.scrollHeight - window.innerHeight;
    const pct = total > 0 ? (scrolled / total) * 100 : 0;
    bar.style.width = pct + '%';
  });
})();

// ── 导航当前页高亮 ──
(function () {
  const links = document.querySelectorAll('nav.main-nav a');
  const path = window.location.pathname;
  links.forEach(l => {
    const href = l.getAttribute('href');
    if (href && (path === href || (href !== '/' && path.startsWith(href.replace('.html', ''))))) {
      l.classList.add('active');
    }
  });
})();

// ── 平滑跳转内链 ──
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const id = a.getAttribute('href').slice(1);
    const el = document.getElementById(id);
    if (el) {
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});
