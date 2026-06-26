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

// ═══════════════════════════════════════════
// 文章搜索
// ═══════════════════════════════════════════
(function () {
  const overlay   = document.getElementById('search-overlay');
  const trigger   = document.getElementById('search-trigger');
  const closeBtn  = document.getElementById('search-close');
  const input     = document.getElementById('search-input');
  const results   = document.getElementById('search-results');
  const hint      = document.getElementById('search-hint');

  if (!overlay || !trigger) return;

  let searchIndex = null;
  let indexLoaded = false;

  // ── 加载搜索索引 ──
  async function loadIndex() {
    if (indexLoaded) return;
    try {
      const base = document.querySelector('meta[name="search-index"]')
        ? document.querySelector('meta[name="search-index"]').content
        : (location.pathname.includes('/posts/') ? '../search.json' : 'search.json');
      const resp = await fetch(base);
      searchIndex = await resp.json();
      indexLoaded = true;
    } catch (e) {
      searchIndex = [];
      indexLoaded = true;
    }
  }

  // ── 开/关弹窗 ──
  function openSearch() {
    overlay.classList.add('active');
    input.focus();
    input.select();
    loadIndex();
  }

  function closeSearch() {
    overlay.classList.remove('active');
    input.value = '';
    results.innerHTML = '';
    hint.classList.remove('hidden');
  }

  trigger.addEventListener('click', openSearch);
  closeBtn.addEventListener('click', closeSearch);
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeSearch();
  });

  // 键盘快捷键 Ctrl+K / Cmd+K
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      overlay.classList.contains('active') ? closeSearch() : openSearch();
    }
    if (e.key === 'Escape' && overlay.classList.contains('active')) {
      closeSearch();
    }
  });

  // ── 搜索逻辑 ──
  function fuzzyMatch(text, query) {
    if (!text || !query) return 0;
    const t = text.toLowerCase();
    const q = query.toLowerCase();
    if (t === q) return 100;
    if (t.startsWith(q)) return 80;
    if (t.includes(q)) return 60;
    // 模糊：逐字匹配
    let qi = 0, score = 0, consecutive = 0;
    for (let i = 0; i < t.length && qi < q.length; i++) {
      if (t[i] === q[qi]) {
        qi++;
        consecutive++;
        score += consecutive * 2;
      } else {
        consecutive = 0;
      }
    }
    return qi === q.length ? score : 0;
  }

  function search(query) {
    if (!searchIndex || !query.trim()) {
      results.innerHTML = '';
      hint.classList.remove('hidden');
      return;
    }
    const q = query.trim();
    const scored = searchIndex.map(item => {
      let score = 0;
      let matchField = '';

      const titleScore = fuzzyMatch(item.title, q);
      if (titleScore > score) { score = titleScore; matchField = 'title'; }

      const excerptScore = fuzzyMatch(item.excerpt, q);
      if (excerptScore > score) { score = excerptScore; matchField = 'excerpt'; }

      // 标签：精准匹配加分最多
      const tagHit = item.tags.some(t => t.toLowerCase().includes(q.toLowerCase()));
      if (tagHit) { score = Math.max(score, 90); matchField = 'tag'; }

      // 全文搜索
      if (item.text) {
        const textScore = fuzzyMatch(item.text, q);
        if (textScore > score) { score = textScore; matchField = 'content'; }
      }

      // 合集名匹配
      if (item.collection && item.collection.toLowerCase().includes(q.toLowerCase())) {
        score = Math.max(score, 70);
        matchField = 'collection';
      }

      return { ...item, score, matchField };
    });

    const filtered = scored.filter(s => s.score > 0).sort((a, b) => b.score - a.score);
    renderResults(filtered, q);
  }

  function highlightText(text, query, maxLen) {
    if (!query || !text) return text.slice(0, maxLen || 200);
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(${escaped})`, 'gi');
    let result = text.replace(re, '<em>$1</em>');
    if (maxLen && result.length > maxLen) {
      // 截取第一处高亮附近
      const idx = result.indexOf('<em>');
      const start = Math.max(0, idx - 40);
      result = (start > 0 ? '…' : '') + result.slice(start, start + maxLen) + (result.length > start + maxLen ? '…' : '');
    }
    return result;
  }

  function renderResults(items, query) {
    hint.classList.add('hidden');
    if (!items.length) {
      results.innerHTML = `<div class="search-empty">没有找到与 <strong>${query}</strong> 相关的文章</div>`;
      return;
    }

    const matchLabels = { title: '标题', tag: '标签', content: '正文', excerpt: '摘要', collection: '合集' };
    results.innerHTML = items.map(item => `
      <a href="${item.url}" class="search-result-card">
        <div class="search-result-title">
          ${highlightText(item.title, query, 80)}
          <span class="match-tag">${matchLabels[item.matchField] || '匹配'}</span>
        </div>
        <div class="search-result-excerpt">
          ${highlightText(item.excerpt || (item.text || '').slice(0, 120), query, 160)}
        </div>
        <div class="search-result-meta">
          <span>${item.date}</span>
          ${item.collection ? `<span>📂 ${item.collection}</span>` : ''}
          ${item.tags.length ? `<span>🏷 ${item.tags.slice(0, 3).join(', ')}</span>` : ''}
        </div>
      </a>
    `).join('');
  }

  // 防抖输入
  let debounceTimer;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => search(input.value), 200);
  });

  // 标签点击 → 触发搜索
  document.addEventListener('click', e => {
    const tagEl = e.target.closest('.tag-pill');
    if (tagEl) {
      e.preventDefault();
      const tag = tagEl.textContent.trim();
      openSearch();
      input.value = tag;
      search(tag);
    }
  });
})();
