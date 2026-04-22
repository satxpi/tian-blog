/* ============================================================
   股票日记 — 前端逻辑
   数据全部从 SQLite 数据库读写（通过 server.py REST API）
   ============================================================ */

const API = '/stock';   // 路径前缀，所有 API 请求使用 /stock/api/...

/* ========== 状态 ========== */
const state = {
  currentPage: 'daily',
  dailyDate: new Date(),
  weeklyDate: new Date(),
  currentEditor: null,
  currentSentiment: 'neutral',
  mrSentiment: 'neutral',
  afSentiment: 'neutral',
  wkSentiment: 'neutral',
  editingHoldingId: null,
  holdings: []
};

/* ========== 工具函数 ========== */
function formatDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function formatDateCN(d) {
  const weekdays = ['日','一','二','三','四','五','六'];
  return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日 周${weekdays[d.getDay()]}`;
}
function getWeekKey(d) {
  const tmp = new Date(d);
  tmp.setHours(0,0,0,0);
  const day = tmp.getDay() || 7;
  tmp.setDate(tmp.getDate() - day + 1);
  return formatDate(tmp);
}
function getWeekRange(d) {
  const tmp = new Date(d);
  const day = tmp.getDay() || 7;
  const mon = new Date(tmp); mon.setDate(tmp.getDate() - day + 1);
  const sun = new Date(tmp); sun.setDate(tmp.getDate() - day + 7);
  return `${mon.getMonth()+1}月${mon.getDate()}日 — ${sun.getMonth()+1}月${sun.getDate()}日`;
}
function sentimentLabel(s) {
  return { bullish:'看多', neutral:'中性', bearish:'看空' }[s] || '中性';
}
function sentimentIcon(s) {
  return { bullish:'fa-arrow-trend-up', neutral:'fa-minus', bearish:'fa-arrow-trend-down' }[s] || 'fa-minus';
}
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  return String(str).replace(/"/g,'&quot;');
}
function showToast(msg, duration = 2500) {
  let el = document.getElementById('__toast__');
  if (!el) {
    el = document.createElement('div');
    el.id = '__toast__';
    el.style.cssText = [
      'position:fixed','bottom:32px','left:50%','transform:translateX(-50%) translateY(20px)',
      'background:rgba(30,34,44,0.92)','color:#e2e8f0','padding:10px 22px',
      'border-radius:20px','font-size:14px','z-index:9999','pointer-events:none',
      'transition:opacity .3s,transform .3s','opacity:0','white-space:nowrap',
      'box-shadow:0 4px 16px rgba(0,0,0,0.3)'
    ].join(';');
    document.body.appendChild(el);
  }
  el.textContent = msg;
  clearTimeout(el._timer);
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateX(-50%) translateY(0)';
  });
  el._timer = setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(-50%) translateY(20px)';
  }, duration);
}
function val(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}
function setVal(id, v) {
  const el = document.getElementById(id);
  if (el) el.value = v || '';
}

/* ========== 通用 API fetch ========== */
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ========== 市场状态 ========== */
function updateMarketStatus() {
  const now = new Date();
  const h = now.getHours(), m = now.getMinutes();
  const totalMin = h * 60 + m;
  const day = now.getDay();
  const dot = document.querySelector('.status-dot');
  const txt = document.getElementById('statusText');
  const isWeekday = day >= 1 && day <= 5;
  const isOpen = isWeekday && (
    (totalMin >= 9*60+30 && totalMin < 11*60+30) ||
    (totalMin >= 13*60   && totalMin < 15*60)
  );
  if (isOpen) {
    dot.className = 'status-dot open';
    txt.textContent = '交易中';
  } else {
    dot.className = 'status-dot closed';
    txt.textContent = isWeekday ? '已收盘' : '休市';
  }
}

/* ========== 导航 ========== */
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    switchPage(item.dataset.page);
  });
});

function switchPage(page) {
  state.currentPage = page;
  document.querySelectorAll('.nav-item').forEach(i => i.classList.toggle('active', i.dataset.page === page));
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === `page-${page}`));
  const titles = { daily:'日报', weekly:'周报', watchlist:'关注板块' };
  document.getElementById('pageTitle').textContent = titles[page];
  if (page === 'daily')     renderDaily();
  if (page === 'weekly')    renderWeekly();
  if (page === 'watchlist') renderWatchlist();
}

/* ========================================================
   日报
   ======================================================== */
document.getElementById('prevDay').addEventListener('click', () => {
  state.dailyDate.setDate(state.dailyDate.getDate() - 1);
  renderDaily();
});
document.getElementById('nextDay').addEventListener('click', () => {
  state.dailyDate.setDate(state.dailyDate.getDate() + 1);
  renderDaily();
});

async function renderDaily() {
  const d = state.dailyDate;
  document.getElementById('dailyCurrentDate').textContent = formatDateCN(d);
  document.getElementById('pageDate').textContent = formatDate(d);
  const date = formatDate(d);

  showReportLoading('morning');
  showReportLoading('afternoon');

  try {
    const data = await apiFetch(`/stock/api/daily?date=${date}`);
    renderMorningCard(data.morning);
    renderAfternoonCard(data.afternoon);
  } catch(e) {
    renderMorningCard(null);
    renderAfternoonCard(null);
  }
  renderDailyHistory();
}

function showReportLoading(type) {
  document.getElementById(`${type}Empty`).classList.add('hidden');
  const report = document.getElementById(`${type}Report`);
  report.classList.remove('hidden');
  report.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载中...</div>';
}

function renderReport(type, data) {
  const empty  = document.getElementById(`${type}Empty`);
  const report = document.getElementById(`${type}Report`);
  if (!data || (!data.title && !data.content)) {
    empty.classList.remove('hidden');
    report.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  report.classList.remove('hidden');
  const s = data.sentiment || 'neutral';
  report.innerHTML = `
    <div class="report-title">${escHtml(data.title || '无标题')}</div>
    <div class="report-meta">
      <span><i class="fa-regular fa-clock"></i> ${escHtml(data.time || '')}</span>
      <span class="sentiment-tag sentiment-${s}">
        <i class="fa-solid ${sentimentIcon(s)}"></i> ${sentimentLabel(s)}
      </span>
    </div>
    <div class="report-body">${escHtml(data.content || '')}</div>
  `;
}

/* 早报卡片展示（结构化） */
function renderMorningCard(data) {
  const empty  = document.getElementById('morningEmpty');
  const report = document.getElementById('morningReport');
  if (!data || (!data.title && !data.content && (!data.structured_data || !Object.keys(data.structured_data).length))) {
    empty.classList.remove('hidden');
    report.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  report.classList.remove('hidden');
  const s  = data.sentiment || 'neutral';
  const sd = data.structured_data || {};

  let html = `
    <div class="report-title">${escHtml(data.title || '今日早报')}</div>
    <div class="report-meta">
      <span><i class="fa-regular fa-clock"></i> ${escHtml(data.time || '')}</span>
      <span class="sentiment-tag sentiment-${s}">
        <i class="fa-solid ${sentimentIcon(s)}"></i> ${sentimentLabel(s)}
      </span>
    </div>
  `;

  // 一、外围市场摘要
  if (sd.section1_overseas) {
    const ov = sd.section1_overseas;
    const allItems = [...(ov.us_markets||[]), ...(ov.other_markets||[])];
    if (allItems.length) {
      html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">一</span> 外围市场</div>
        <div class="mini-indices">`;
      allItems.forEach(it => {
        const pct = parseFloat(it.change_pct) || 0;
        const cls  = pct > 0 ? 'up' : pct < 0 ? 'down' : 'flat';
        const sign = pct > 0 ? '+' : '';
        html += `<span class="mini-idx"><b>${escHtml(it.name)}</b> <span class="${cls}">${sign}${escHtml(String(it.change_pct||''))}%</span></span>`;
      });
      html += `</div>`;
      if (ov.summary) html += `<p style="font-size:12px;color:var(--text-sub);margin-top:6px">${escHtml(ov.summary)}</p>`;
      html += `</div>`;
    }
  }

  // 二、昨日财经大事
  if (sd.section2_events && sd.section2_events.items && sd.section2_events.items.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">二</span> 财经大事</div>`;
    sd.section2_events.items.slice(0, 3).forEach(ev => {
      const impCls = ev.impact === 'positive' ? 'up' : ev.impact === 'negative' ? 'down' : '';
      html += `<div class="mini-sector"><b class="${impCls}">${ev.impact === 'positive' ? '▲' : ev.impact === 'negative' ? '▼' : '●'}</b> ${escHtml(ev.event)}</div>`;
    });
    html += `</div>`;
  }

  // 三、今日关注方向
  if (sd.section3_focus) {
    const fc = sd.section3_focus;
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">三</span> 今日关注</div>`;
    if (fc.watch_sectors && fc.watch_sectors.length) {
      html += `<p style="font-size:12px;margin:2px 0"><span style="color:var(--up)">▲ 关注：</span>`;
      html += fc.watch_sectors.map(s => `<b title="${escHtml(s.reason||'')}">${escHtml(s.name)}</b>`).join('、');
      html += `</p>`;
    }
    if (fc.warn_sectors && fc.warn_sectors.length) {
      html += `<p style="font-size:12px;margin:2px 0"><span style="color:var(--down)">▼ 注意：</span>`;
      html += fc.warn_sectors.map(s => `<b title="${escHtml(s.reason||'')}">${escHtml(s.name)}</b>`).join('、');
      html += `</p>`;
    }
    if ((!fc.watch_sectors || !fc.watch_sectors.length) && (!fc.warn_sectors || !fc.warn_sectors.length)) {
      html += `<p style="font-size:12px;color:var(--text-muted)">暂无数据（需先有昨日盘后总结），或点击编辑手动填写</p>`;
    }
    if (fc.summary) html += `<p style="font-size:11px;color:var(--text-muted);margin-top:4px">${escHtml(fc.summary)}</p>`;
    html += `</div>`;
  }

  // 四、操作建议
  if (sd.section4_advice) {
    const ad = sd.section4_advice;
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">四</span> 操作建议</div>`;
    if (ad.buy_strength)  html += `<p style="font-size:12px"><i class="fa-solid fa-arrow-up-right-dots"></i> 补仓：${escHtml(ad.buy_strength)}</p>`;
    if (ad.sell_strength) html += `<p style="font-size:12px"><i class="fa-solid fa-arrow-down-right-dots"></i> 止盈：${escHtml(ad.sell_strength)}</p>`;
    if (ad.risk_note)     html += `<p style="font-size:12px"><i class="fa-solid fa-shield-halved"></i> 风险：${escHtml(ad.risk_note)}</p>`;
    // 逐股详细分析
    if (ad.buy_advice) {
      const lines = ad.buy_advice.split('\n').filter(l => l.trim());
      if (lines.length) {
        html += `<div style="margin-top:6px">`;
        lines.forEach(line => {
          // 根据操作标签着色
          const isRisk = line.includes('止损') || line.includes('减仓') || line.includes('⚠');
          const isGood = line.includes('止盈') || line.includes('💰') || line.includes('锁利') || line.includes('✅');
          const isWait = line.includes('待完善') || line.includes('📋');
          const color  = isRisk ? 'var(--down)' : (isGood ? 'var(--up)' : (isWait ? 'var(--text-muted)' : 'inherit'));
          html += `<div class="mini-sector" style="color:${color};font-size:12px">${escHtml(line)}</div>`;
        });
        html += `</div>`;
      }
    }
    if (!ad.buy_strength && !ad.sell_strength && !ad.risk_note && !ad.buy_advice) {
      html += `<p style="font-size:12px;color:var(--text-muted)">暂无持仓数据，请先在持仓管理中录入股票及成本</p>`;
    }
    html += `</div>`;
  }

  // 五、今日计划
  if (sd.section5_plan && sd.section5_plan.items && sd.section5_plan.items.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">五</span> 今日计划</div>`;
    sd.section5_plan.items.forEach(p => {
      const statusIcon = p.done ? '✅' : '⬜';
      html += `<div class="mini-sector">${statusIcon} <b>${escHtml(p.type||'')}</b>${p.content ? '：' + escHtml(p.content) : ''}</div>`;
    });
    html += `</div>`;
  }

  if (data.content) {
    html += `<div class="report-body" style="margin-top:12px">${escHtml(data.content)}</div>`;
  }

  report.innerHTML = html;
}

/* 盘后总结卡片展示（结构化） */
function renderAfternoonCard(data) {
  const empty  = document.getElementById('afternoonEmpty');
  const report = document.getElementById('afternoonReport');
  if (!data || (!data.title && !data.content && (!data.structured_data || !Object.keys(data.structured_data).length))) {
    empty.classList.remove('hidden');
    report.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  report.classList.remove('hidden');
  const s  = data.sentiment || 'neutral';
  const sd = data.structured_data || {};

  // 当天及以前都可删除（方便调试重采）
  const dateStr = formatDate(state.dailyDate);
  const today   = formatDate(new Date());
  const canDelete = dateStr <= today;

  let html = `
    <div class="report-title">${escHtml(data.title || '盘后复盘')}`;
  if (canDelete) {
    html += ` <button class="btn-delete-weekly" onclick="deleteAfternoonReport()" title="删除本日盘后数据（可重新采集）">
      <i class="fa-solid fa-trash-can"></i> 删除
    </button>`;
  }
  html += `</div>
    <div class="report-meta">
      <span><i class="fa-regular fa-clock"></i> ${escHtml(data.time || '')}</span>
      <span class="sentiment-tag sentiment-${s}">
        <i class="fa-solid ${sentimentIcon(s)}"></i> ${sentimentLabel(s)}
      </span>
    </div>
  `;

  // 一、指数数据
  if (sd.section1_indices && sd.section1_indices.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">一</span> 盘后数据</div>
      <div class="mini-indices">`;
    sd.section1_indices.forEach(idx => {
      const chgClass = parseFloat(idx.change_pct) > 0 ? 'up' : parseFloat(idx.change_pct) < 0 ? 'down' : 'flat';
      const sign = parseFloat(idx.change_pct) > 0 ? '+' : '';
      html += `<span class="mini-idx"><b>${escHtml(idx.name)}</b> <span class="${chgClass}">${sign}${escHtml(String(idx.change_pct||''))}%</span></span>`;
    });
    html += `</div></div>`;
  }

  // 二、市场分析摘要（只要 section2_market 存在就渲染）
  if (sd.section2_market) {
    const m = sd.section2_market;
    const hasAny = m.trend || m.fund_north || m.fund_main || m.sentiment_level || m.volume || m.advance || m.decline || m.trend_detail;
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">二</span> 市场分析</div>`;
    if (m.trend) {
      html += `<p><i class="fa-solid fa-chart-line"></i> 趋势：<b>${escHtml(m.trend)}</b>`;
      if (m.trend_detail) html += `<span style="color:var(--text-sub);font-size:12px"> — ${escHtml(m.trend_detail)}</span>`;
      html += `</p>`;
    } else if (m.trend_detail) {
      html += `<p style="color:var(--text-sub);font-size:12px"><i class="fa-solid fa-circle-info"></i> ${escHtml(m.trend_detail)}</p>`;
    }
    if (m.fund_north || m.fund_main) {
      html += `<p><i class="fa-solid fa-money-bill-transfer"></i> 资金：北向 ${escHtml(m.fund_north||'—')}，主力 ${escHtml(m.fund_main||'—')}</p>`;
    }
    if (m.volume || m.advance || m.decline || m.sentiment_level) {
      html += `<p><i class="fa-solid fa-bar-chart"></i>`;
      if (m.sentiment_level) html += ` 情绪：${escHtml(m.sentiment_level)}`;
      if (m.volume)   html += `　成交：${escHtml(m.volume)}`;
      if (m.advance || m.decline) html += `　涨跌家数：<span class="up">${escHtml(m.advance||'—')}</span>/<span class="down">${escHtml(m.decline||'—')}</span>`;
      html += `</p>`;
    }
    if (!hasAny) {
      html += `<p style="color:var(--text-muted);font-size:12px">市场分析待填写，点击右上角编辑按钮补充</p>`;
    }
    html += `</div>`;
  }

  // 三、板块分析（领涨前三 + 领跌前三）
  if (sd.section3_sectors) {
    const s3 = sd.section3_sectors;
    const tops    = s3.top_sectors    || [];
    const bottoms = s3.bottom_sectors || [];
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">三</span> 板块分析</div>`;
    if (tops.length) {
      html += `<p style="font-size:12px;font-weight:600;color:var(--up);margin:4px 0 2px">▲ 领涨板块</p>`;
      tops.forEach((sec, i) => {
        html += `<div class="mini-sector"><b class="up">${i+1}. ${escHtml(sec.name)}</b>`;
        if (sec.reason) html += ` — <span style="color:var(--text-sub)">${escHtml(sec.reason)}</span>`;
        html += `</div>`;
      });
    }
    if (bottoms.length) {
      html += `<p style="font-size:12px;font-weight:600;color:var(--down);margin:8px 0 2px">▼ 领跌板块</p>`;
      bottoms.forEach((sec, i) => {
        html += `<div class="mini-sector"><b class="down">${i+1}. ${escHtml(sec.name)}</b>`;
        if (sec.reason) html += ` — <span style="color:var(--text-sub)">${escHtml(sec.reason)}</span>`;
        html += `</div>`;
      });
    }
    if (!tops.length && !bottoms.length) {
      html += `<p style="color:var(--text-muted);font-size:12px">板块数据待填写，点击右上角编辑按钮补充</p>`;
    }
    if (s3.linkage) html += `<p style="font-size:12px;margin-top:6px"><i class="fa-solid fa-link"></i> 联动：${escHtml(s3.linkage)}</p>`;
    if (s3.rotation) html += `<p style="font-size:12px"><i class="fa-solid fa-rotate"></i> 轮动：${escHtml(s3.rotation)}</p>`;
    html += `</div>`;
  }

  // 四、关注个股
  if (sd.section4_stocks && sd.section4_stocks.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">四</span> 关注个股回顾</div>`;
    sd.section4_stocks.forEach(st => {
      html += `<div class="mini-stock-detail">
        <div class="msd-title"><b>${escHtml(st.name||st.code||'-')}</b> <span class="msd-code">${escHtml(st.code||'')}</span></div>`;
      if (st.minute_analysis) html += `<div class="msd-row"><i class="fa-solid fa-chart-area msd-icon"></i><span><b>分时：</b>${escHtml(st.minute_analysis)}</span></div>`;
      if (st.kline_analysis)  html += `<div class="msd-row"><i class="fa-solid fa-chart-candlestick msd-icon"></i><span><b>K线：</b>${escHtml(st.kline_analysis)}</span></div>`;
      if (st.news_analysis)   html += `<div class="msd-row"><i class="fa-solid fa-newspaper msd-icon"></i><span><b>消息：</b>${escHtml(st.news_analysis)}</span></div>`;
      html += `</div>`;
    });
    html += `</div>`;
  }

  // 五、次日计划
  if (sd.section5_plan) {
    const p = sd.section5_plan;
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">五</span> 次日计划</div>`;
    if (p.target_sectors) html += `<p><i class="fa-solid fa-crosshairs"></i> 目标：${escHtml(p.target_sectors)}</p>`;
    if (p.risk_warning)   html += `<p><i class="fa-solid fa-shield-halved"></i> 风险：${escHtml(p.risk_warning)}</p>`;
    html += `</div>`;
  }

  if (data.content) {
    html += `<div class="report-body" style="margin-top:12px">${escHtml(data.content)}</div>`;
  }

  report.innerHTML = html;
}

async function renderDailyHistory() {
  const list = document.getElementById('dailyRecordsList');
  list.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载历史...</div>';
  try {
    const entries = await apiFetch('/stock/api/daily/list?limit=10');
    if (!entries.length) {
      list.innerHTML = `<div class="empty-state"><i class="fa-solid fa-book-open empty-icon"></i><p>暂无历史日报</p></div>`;
      return;
    }
    list.innerHTML = entries.map(item => {
      const tags = (item.types || []).map(t =>
        t === 'morning'
          ? `<span class="tag tag-morning"><i class="fa-solid fa-sun"></i> 早盘</span>`
          : `<span class="tag tag-afternoon"><i class="fa-solid fa-moon"></i> 盘后</span>`
      ).join('');
      return `
        <div class="record-item" onclick="jumpToDate('${item.date}')">
          <span class="record-date">${item.date}</span>
          <span class="record-preview">${escHtml(item.preview||'')}...</span>
          <div class="record-tags">${tags}</div>
        </div>
      `;
    }).join('');
  } catch(e) {
    list.innerHTML = `<div class="empty-state"><p>历史日报加载失败</p></div>`;
  }
}

function jumpToDate(dateStr) {
  const [y,m,d] = dateStr.split('-').map(Number);
  state.dailyDate = new Date(y, m-1, d);
  renderDaily();
  window.scrollTo(0, 0);
}

/* ========================================================
   周报
   ======================================================== */
document.getElementById('prevWeek').addEventListener('click', () => {
  state.weeklyDate.setDate(state.weeklyDate.getDate() - 7);
  renderWeekly();
});
document.getElementById('nextWeek').addEventListener('click', () => {
  state.weeklyDate.setDate(state.weeklyDate.getDate() + 7);
  renderWeekly();
});

async function renderWeekly() {
  const wk = getWeekKey(state.weeklyDate);
  document.getElementById('weeklyCurrentDate').textContent = getWeekRange(state.weeklyDate);

  const sumEmpty  = document.getElementById('weeklySummaryEmpty');
  const sumReport = document.getElementById('weeklySummaryReport');
  sumEmpty.classList.add('hidden');
  sumReport.classList.remove('hidden');
  sumReport.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载中...</div>';

  try {
    const data = await apiFetch(`/stock/api/weekly?week=${wk}`);

    if (data.summary && (data.summary.content || data.summary.title)) {
      renderWeeklySummaryCard(data.summary);
    } else {
      sumEmpty.classList.remove('hidden');
      sumReport.classList.add('hidden');
    }
    renderRecommendList(data.recommend || []);
  } catch(e) {
    sumEmpty.classList.remove('hidden');
    sumReport.classList.add('hidden');
    renderRecommendList([]);
  }
  renderWeeklyHistory();
}

function renderWeeklySummaryCard(data) {
  const sumEmpty  = document.getElementById('weeklySummaryEmpty');
  const sumReport = document.getElementById('weeklySummaryReport');
  sumEmpty.classList.add('hidden');
  sumReport.classList.remove('hidden');

  const s  = data.sentiment || 'neutral';
  const sd = data.structured_data || {};

  // 判断是否为当前周（当前周才显示删除按钮）
  const wk = getWeekKey(state.weeklyDate);
  const isCurrentWeek = (wk === getWeekKey(new Date()));

  let html = `
    <div class="report-title">${escHtml(data.title || '本周总结')}`;
  if (isCurrentWeek) {
    html += ` <button class="btn-delete-weekly" onclick="deleteWeeklySummary()" title="删除本周总结数据">
      <i class="fa-solid fa-trash-can"></i> 删除
    </button>`;
  }
  html += `</div>
    <div class="report-meta">
      <span><i class="fa-regular fa-clock"></i> ${escHtml(data.time || '')}</span>
      <span class="sentiment-tag sentiment-${s}">
        <i class="fa-solid ${sentimentIcon(s)}"></i> ${sentimentLabel(s)}
      </span>
    </div>
  `;

  // 一、本周指数数据
  if (sd.section1_indices && sd.section1_indices.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">一</span> 本周指数</div>
      <div class="mini-indices">`;
    sd.section1_indices.forEach(idx => {
      const pct = parseFloat(idx.change_pct) || 0;
      const cls  = pct > 0 ? 'up' : pct < 0 ? 'down' : 'flat';
      const sign = pct > 0 ? '+' : '';
      html += `<span class="mini-idx"><b>${escHtml(idx.name)}</b> <span class="${cls}">${sign}${escHtml(String(idx.change_pct||''))}%</span></span>`;
    });
    html += `</div></div>`;
  }

  // 二、本周市场分析
  if (sd.section2_market) {
    const m = sd.section2_market;
    const hasAny = m.trend || m.fund_north || m.fund_main || m.volume || m.trend_detail;
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">二</span> 本周市场</div>`;
    if (m.trend) {
      html += `<p><i class="fa-solid fa-chart-line"></i> 趋势：<b>${escHtml(m.trend)}</b>`;
      if (m.trend_detail) html += `<span style="color:var(--text-sub);font-size:12px"> — ${escHtml(m.trend_detail)}</span>`;
      html += `</p>`;
    }
    if (m.fund_north || m.fund_main) {
      html += `<p><i class="fa-solid fa-money-bill-transfer"></i> 资金：北向 <b>${escHtml(m.fund_north||'—')}</b>，主力 <b>${escHtml(m.fund_main||'—')}</b></p>`;
    }
    if (m.volume) {
      html += `<p><i class="fa-solid fa-bar-chart"></i> 周成交量：${escHtml(m.volume)}</p>`;
    }
    if (!hasAny) {
      html += `<p style="color:var(--text-muted);font-size:12px">市场分析待填写，点击右上角编辑按钮补充</p>`;
    }
    html += `</div>`;
  }

  // 三、板块分析（本周领涨 + 领跌）
  if (sd.section3_sectors) {
    const s3 = sd.section3_sectors;
    const tops    = s3.top_sectors    || [];
    const bottoms = s3.bottom_sectors || [];
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">三</span> 板块表现</div>`;
    if (tops.length) {
      html += `<p style="font-size:12px;font-weight:600;color:var(--up);margin:4px 0 2px">▲ 本周领涨板块</p>`;
      tops.forEach((sec, i) => {
        html += `<div class="mini-sector"><b class="up">${i+1}. ${escHtml(sec.name)}</b>`;
        if (sec.reason) html += ` — <span style="color:var(--text-sub)">${escHtml(sec.reason)}</span>`;
        html += `</div>`;
      });
    }
    if (bottoms.length) {
      html += `<p style="font-size:12px;font-weight:600;color:var(--down);margin:8px 0 2px">▼ 本周领跌板块</p>`;
      bottoms.forEach((sec, i) => {
        html += `<div class="mini-sector"><b class="down">${i+1}. ${escHtml(sec.name)}</b>`;
        if (sec.reason) html += ` — <span style="color:var(--text-sub)">${escHtml(sec.reason)}</span>`;
        html += `</div>`;
      });
    }
    if (!tops.length && !bottoms.length) {
      html += `<p style="color:var(--text-muted);font-size:12px">板块数据待填写，点击右上角编辑按钮补充</p>`;
    }
    if (s3.linkage)  html += `<p style="font-size:12px;margin-top:6px"><i class="fa-solid fa-link"></i> 联动：${escHtml(s3.linkage)}</p>`;
    if (s3.rotation) html += `<p style="font-size:12px"><i class="fa-solid fa-rotate"></i> 轮动：${escHtml(s3.rotation)}</p>`;
    html += `</div>`;
  }

  // 四、关注个股本周回顾
  if (sd.section4_stocks && sd.section4_stocks.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">四</span> 关注个股回顾</div>`;
    sd.section4_stocks.forEach(st => {
      html += `<div class="mini-stock-detail">
        <div class="msd-title"><b>${escHtml(st.name||st.code||'-')}</b> <span class="msd-code">${escHtml(st.code||'')}</span></div>`;
      if (st.minute_analysis) html += `<div class="msd-row"><i class="fa-solid fa-chart-area msd-icon"></i><span><b>分时：</b>${escHtml(st.minute_analysis)}</span></div>`;
      if (st.kline_analysis)  html += `<div class="msd-row"><i class="fa-solid fa-chart-candlestick msd-icon"></i><span><b>K线：</b>${escHtml(st.kline_analysis)}</span></div>`;
      if (st.news_analysis)   html += `<div class="msd-row"><i class="fa-solid fa-newspaper msd-icon"></i><span><b>消息：</b>${escHtml(st.news_analysis)}</span></div>`;
      html += `</div>`;
    });
    html += `</div>`;
  }

  // 五、下周计划
  if (sd.section5_plan && (sd.section5_plan.target_sectors || sd.section5_plan.buy_plan || sd.section5_plan.risk_warning)) {
    const p = sd.section5_plan;
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">五</span> 下周计划</div>`;
    if (p.target_sectors) html += `<p><i class="fa-solid fa-crosshairs"></i> 目标方向：${escHtml(p.target_sectors)}</p>`;
    if (p.buy_plan)       html += `<p><i class="fa-solid fa-cart-plus"></i> 买入计划：${escHtml(p.buy_plan)}</p>`;
    if (p.sell_plan)      html += `<p><i class="fa-solid fa-hand-holding-dollar"></i> 减仓计划：${escHtml(p.sell_plan)}</p>`;
    if (p.risk_warning)   html += `<p><i class="fa-solid fa-shield-halved"></i> 风险提示：${escHtml(p.risk_warning)}</p>`;
    html += `</div>`;
  }

  // 六、AI 自动选出下周潜力股
  if (sd.section6_recommend && sd.section6_recommend.length) {
    html += `<div class="se-card-section"><div class="se-card-title"><span class="se-num">六</span> 下周潜力股 <span style="font-size:11px;color:var(--text-muted);font-weight:400">（自动筛选 · 仅供参考）</span></div>`;
    sd.section6_recommend.forEach((st, i) => {
      const chg = parseFloat(st.chg) || 0;
      const chgCls  = chg > 0 ? 'up' : chg < 0 ? 'down' : 'flat';
      const chgSign = chg > 0 ? '+' : '';
      html += `
        <div class="wk-rec-card">
          <div class="wk-rec-header">
            <span class="wk-rec-rank">#${i+1}</span>
            <span class="wk-rec-name">${escHtml(st.name)}</span>
            <span class="wk-rec-code">${escHtml(st.code)}</span>
            <span class="wk-rec-price">¥${escHtml(String(st.price||''))} <span class="${chgCls}">${chgSign}${chg.toFixed(2)}%</span></span>
            <span class="wk-rec-inflow" style="color:var(--up)">主力 +${escHtml(String(st.inflow||''))}亿</span>
          </div>`;
      if (st.reason) {
        // 解析四维分析
        const parts = st.reason.split('|').map(p => p.trim());
        if (parts.length >= 4) {
          html += `<div class="wk-rec-analysis">`;
          parts.forEach(p => {
            const match = p.match(/^【(.+?)】(.+)$/);
            if (match) {
              const dim = match[1];
              const desc = match[2];
              const dimIcon = {
                '政策面': 'fa-landmark', '技术面': 'fa-chart-candlestick',
                '情绪面': 'fa-face-smile', '资金面': 'fa-coins'
              }[dim] || 'fa-circle-dot';
              html += `<div class="wk-rec-dim"><i class="fa-solid ${dimIcon}"></i> <b>${escHtml(dim)}：</b>${escHtml(desc)}</div>`;
            }
          });
          html += `</div>`;
        } else {
          html += `<div class="wk-rec-reason">${escHtml(st.reason)}</div>`;
        }
      }
      html += `</div>`;
    });
    html += `<p style="font-size:11px;color:var(--text-muted);margin-top:6px;padding:0 4px"><i class="fa-solid fa-circle-exclamation"></i> 以上为系统基于主力资金流向自动筛选，非投资建议，请结合自身判断使用</p>`;
    html += `</div>`;
  }

  if (data.content) {
    html += `<div class="report-body" style="margin-top:12px">${escHtml(data.content)}</div>`;
  }

  sumReport.innerHTML = html;
}

function renderRecommendList(stocks) {
  const empty = document.getElementById('recommendEmpty');
  const list  = document.getElementById('recommendStockList');
  if (!stocks.length) {
    empty.classList.remove('hidden');
    list.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  list.classList.remove('hidden');
  const wk = getWeekKey(state.weeklyDate);
  list.innerHTML = stocks.map((s, i) => `
    <div class="stock-card" id="wrec-card-${s.id||i}" data-id="${s.id||''}" data-code="${escHtml(s.code)}" data-name="${escHtml(s.name)}" data-market="${escHtml(s.market||'A')}" data-reason="${escHtml(s.reason||'')}">
      <div class="stock-rank">${i+1}</div>
      <div class="stock-info" style="flex:1;min-width:0">
        <div class="stock-name">${escHtml(s.name)}</div>
        <div class="stock-code">${escHtml(s.code)}</div>
        ${s.reason ? `<div class="stock-reason">${escHtml(s.reason)}</div>` : ''}
        ${s.advice ? `<div class="ws-advice wrec-advice-display" id="wrec-advice-${s.id||i}"><i class="fa-solid fa-lightbulb"></i> ${escHtml(s.advice)}</div>` : `<div class="wrec-advice-display" id="wrec-advice-${s.id||i}" style="display:none"></div>`}
        <div class="wrec-advice-edit" id="wrec-advice-edit-${s.id||i}" style="display:none">
          <input type="text" class="form-input wrec-advice-input" placeholder="输入操盘建议…" value="${escHtml(s.advice||'')}">
          <div style="display:flex;gap:6px;margin-top:6px">
            <button class="btn btn-primary" style="padding:4px 12px;font-size:12px" onclick="saveWrecAdvice(${s.id||0},'${wk}')">保存</button>
            <button class="btn btn-outline" style="padding:4px 10px;font-size:12px" onclick="cancelWrecAdvice(${s.id||0})">取消</button>
          </div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0">
        <button class="btn-del-rec" onclick="deleteWeeklyRecommend('${escHtml(s.code)}','${wk}')" title="删除此推荐股">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <button class="btn-watch-add" onclick="addWrecToWatch(this)" title="加入关注"
          data-id="${s.id||''}" data-code="${escHtml(s.code)}" data-name="${escHtml(s.name)}" data-market="${escHtml(s.market||'A')}" data-reason="${escHtml(s.reason||'')}">
          <i class="fa-solid fa-star"></i>
        </button>
        <button class="btn-edit-advice" onclick="editWrecAdvice(${s.id||0})" title="编辑操盘建议">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
      </div>
    </div>
  `).join('');
}

async function renderWeeklyHistory() {
  const list = document.getElementById('weeklyRecordsList');
  list.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载历史...</div>';
  try {
    const entries = await apiFetch('/stock/api/weekly/list?limit=8');
    if (!entries.length) {
      list.innerHTML = `<div class="empty-state"><i class="fa-solid fa-calendar-week empty-icon"></i><p>暂无历史周报</p></div>`;
      return;
    }
    list.innerHTML = entries.map(item => {
      const [y,m,d] = item.week.split('-').map(Number);
      const mon = new Date(y, m-1, d);
      const sun = new Date(y, m-1, d+6);
      const range = `${mon.getMonth()+1}/${mon.getDate()} — ${sun.getMonth()+1}/${sun.getDate()}`;
      return `
        <div class="record-item" onclick="jumpToWeek('${item.week}')">
          <span class="record-date">${range}</span>
          <span class="record-preview">${escHtml(item.summary_preview||'')}...</span>
          <div class="record-tags">
            ${item.summary_preview ? `<span class="tag tag-week"><i class="fa-solid fa-chart-bar"></i> 总结</span>` : ''}
            ${item.rec_count ? `<span class="tag tag-blue"><i class="fa-solid fa-rocket"></i> 推荐 ${item.rec_count}</span>` : ''}
          </div>
        </div>
      `;
    }).join('');
  } catch(e) {
    list.innerHTML = `<div class="empty-state"><p>历史周报加载失败</p></div>`;
  }
}

function jumpToWeek(dateStr) {
  const [y,m,d] = dateStr.split('-').map(Number);
  state.weeklyDate = new Date(y, m-1, d);
  renderWeekly();
  window.scrollTo(0, 0);
}

/* ========================================================
   关注板块
   ======================================================== */
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    if (tab.dataset.tab === 'holdings') fetchHoldingQuotes();
  });
});

async function renderWatchlist() {
  await renderWatchlistRecommended();
  await renderHoldings();
  setTimeout(fetchHoldingQuotes, 300);
}

async function renderWatchlistRecommended() {
  const container = document.getElementById('watchlistRecommended');
  container.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载中...</div>';
  try {
    const stocks = await apiFetch('/stock/api/watch/recommend');
    document.getElementById('recommendCount').textContent = stocks.length;

    if (!stocks.length) {
      container.innerHTML = `<div class="empty-state">
        <i class="fa-solid fa-rocket empty-icon"></i>
        <p>暂无关注股票，点击右上角"添加"按钮手动添加</p>
      </div>`;
      return;
    }

    container.innerHTML = stocks.map((s, i) => `
      <div class="watchlist-stock-card" id="ws-card-${s.id||i}">
        <div class="ws-header">
          <div>
            <div class="ws-name">${escHtml(s.name)}</div>
            <div class="ws-code">${escHtml(s.code)} · ${escHtml(s.market||'A')}股</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="ws-from">关注 #${i+1}</span>
            <button class="btn-edit-advice" onclick="editWatchAdvice(${s.id||0})" title="编辑操盘建议">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <button class="btn-del-rec" onclick="deleteWatchRecommend(${s.id||0})" title="删除此关注股">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        </div>
        <div class="ws-quote" id="ws-quote-${escHtml(s.code)}">
          <span class="ws-quote-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载报价中...</span>
        </div>
        ${s.reason ? `<div class="ws-reason">${escHtml(s.reason)}</div>` : ''}
        ${s.advice
          ? `<div class="ws-advice watch-advice-display" id="watch-advice-${s.id||i}"><i class="fa-solid fa-lightbulb"></i> ${escHtml(s.advice)}</div>`
          : `<div class="watch-advice-display" id="watch-advice-${s.id||i}" style="display:none"></div>`}
        <div class="wrec-advice-edit" id="watch-advice-edit-${s.id||i}" style="display:none">
          <input type="text" class="form-input wrec-advice-input" placeholder="输入操盘建议…" value="${escHtml(s.advice||'')}">
          <div style="display:flex;gap:6px;margin-top:6px">
            <button class="btn btn-primary" style="padding:4px 12px;font-size:12px" onclick="saveWatchAdvice(${s.id||0})">保存</button>
            <button class="btn btn-outline" style="padding:4px 10px;font-size:12px" onclick="cancelWatchAdvice(${s.id||0})">取消</button>
          </div>
        </div>
      </div>
    `).join('');

    fetchWatchlistQuotes(stocks);
  } catch(e) {
    container.innerHTML = `<div class="empty-state"><p>推荐股票加载失败</p></div>`;
  }
}

async function renderHoldings() {
  const container = document.getElementById('holdingsTable');
  container.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载中...</div>';
  try {
    const holdings = await apiFetch('/stock/api/holdings');
    state.holdings = holdings;
    _renderHoldingsTable(holdings);
  } catch(e) {
    container.innerHTML = `<div class="empty-state"><p>持仓加载失败</p></div>`;
  }
}

function _renderHoldingsTable(holdings) {
  const container = document.getElementById('holdingsTable');
  if (!holdings.length) {
    container.innerHTML = `<div class="empty-state">
      <i class="fa-solid fa-briefcase empty-icon"></i>
      <p>暂无持仓记录</p>
      <button class="btn-write" onclick="openHoldingEditor()">添加持仓</button>
    </div>`;
    return;
  }
  const rows = holdings.map((h, idx) => {
    const cost   = parseFloat(h.cost) || 0;
    const cur    = parseFloat(h.current_price) || 0;
    const shares = parseInt(h.shares) || 0;
    const pnl    = (cur - cost) * shares;
    const pnlPct = cost > 0 ? ((cur - cost) / cost * 100) : 0;
    const pnlClass = pnl > 0 ? 'pnl-positive' : pnl < 0 ? 'pnl-negative' : 'pnl-zero';
    const pnlSign  = pnl > 0 ? '+' : '';
    return `
      <tr id="holding-row-${idx}">
        <td><strong>${escHtml(h.name)}</strong></td>
        <td>${escHtml(h.code)}</td>
        <td><span class="tag tag-blue">${escHtml(h.market||'A')}</span></td>
        <td id="h-price-${idx}">${cur.toFixed(2)}</td>
        <td>${cost.toFixed(2)}</td>
        <td>${shares.toLocaleString()}</td>
        <td id="h-pnl-${idx}"  class="${pnlClass}">${pnlSign}${pnl.toFixed(0)}</td>
        <td id="h-pnlp-${idx}" class="${pnlClass}">${pnlSign}${pnlPct.toFixed(2)}%</td>
        <td>${escHtml(h.note||'—')}</td>
        <td>
          <div class="holding-actions">
            <button class="btn-icon" onclick="editHolding(${h.id})" title="编辑"><i class="fa-solid fa-pen"></i></button>
            <button class="btn-icon delete" onclick="deleteHolding(${h.id})" title="删除"><i class="fa-solid fa-trash"></i></button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <table class="holdings-table">
      <thead>
        <tr>
          <th>股票名称</th><th>代码</th><th>市场</th>
          <th>现价</th><th>成本</th><th>持仓股数</th>
          <th>盈亏金额</th><th>盈亏比例</th><th>备注</th><th>操作</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
      <tfoot>
        <tr style="background:var(--bg3)">
          <td colspan="6" style="font-weight:700;padding:10px 14px">合计</td>
          <td id="h-total-pnl"  style="padding:10px 14px;font-weight:700">—</td>
          <td id="h-total-pnlp" style="padding:10px 14px;font-weight:700">—</td>
          <td colspan="2"></td>
        </tr>
      </tfoot>
    </table>
  `;
  updateHoldingsSummary();
}

function updateHoldingsSummary() {
  const holdings = state.holdings || [];
  let totalMarket = 0, totalCost = 0;
  holdings.forEach((h, idx) => {
    const priceEl = document.getElementById(`h-price-${idx}`);
    const cur    = priceEl ? parseFloat(priceEl.textContent) || 0 : (parseFloat(h.current_price) || 0);
    const cost   = parseFloat(h.cost) || 0;
    const shares = parseInt(h.shares) || 0;
    totalMarket += cur * shares;
    totalCost   += cost * shares;
  });
  const totalPnl = totalMarket - totalCost;
  const totalPct = totalCost > 0 ? (totalPnl / totalCost * 100) : 0;
  const cls  = totalPnl >= 0 ? 'pnl-positive' : 'pnl-negative';
  const sign = totalPnl >= 0 ? '+' : '';
  const pnlEl  = document.getElementById('h-total-pnl');
  const pnlpEl = document.getElementById('h-total-pnlp');
  if (pnlEl)  { pnlEl.textContent  = `${sign}${totalPnl.toFixed(0)}`;   pnlEl.className  = cls; }
  if (pnlpEl) { pnlpEl.textContent = `${sign}${totalPct.toFixed(2)}%`;  pnlpEl.className = cls; }
}

/* ========================================================
   早报结构化编辑器
   ======================================================== */
function setMrSentiment(v) {
  state.mrSentiment = v;
  document.querySelectorAll('#morningModal .sentiment-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.value === v);
  });
}

async function openMorningEditor() {
  state.mrSentiment = 'neutral';
  _initMorningEditor();

  const date = formatDate(state.dailyDate);
  try {
    const data = await apiFetch(`/stock/api/daily?date=${date}`);
    const mr = data.morning;
    if (mr) {
      setVal('mrTitle', mr.title);
      setMrSentiment(mr.sentiment || 'neutral');
      const sd = mr.structured_data || {};
      _fillMorningFields(sd);
    }
  } catch(e) {}

  openModal('morningModal');
}

function _initMorningEditor() {
  // 一、外围市场 - 美股三大
  const usGrid = document.getElementById('mrOverseasGrid');
  usGrid.innerHTML = '';
  [['道琼斯',''],['纳斯达克',''],['标普500','']].forEach(([name]) => addOverseasRow(name));

  // 一、港股/期货/商品
  const otherGrid = document.getElementById('mrOtherGrid');
  otherGrid.innerHTML = '';
  [['恒生指数',''],['黄金',''],['原油','']].forEach(([name]) => addOtherRow(name));

  // 二、财经大事
  document.getElementById('mrEventsList').innerHTML = '';
  addEventItem();

  // 三、关注方向
  document.getElementById('mrWatchSectors').innerHTML = '';
  document.getElementById('mrWarnSectors').innerHTML = '';
  addWatchSector(); addWatchSector();
  addWarnSector();

  // 五、今日计划
  document.getElementById('mrPlanList').innerHTML = '';
  addPlanItem('买入');

  // 清空文本字段
  ['mrTitle','mrOverseasSummary','mrEventsSummary','mrFocusSummary',
   'mrBuyStrength','mrBuyAdvice','mrSellStrength','mrSellAdvice',
   'mrRiskNote','mrPreOpenCheck'].forEach(id => setVal(id, ''));
}

function _fillMorningFields(sd) {
  // 一、外围市场
  if (sd.section1_overseas) {
    const ov = sd.section1_overseas;
    const usGrid = document.getElementById('mrOverseasGrid');
    usGrid.innerHTML = '';
    (ov.us_markets || []).forEach(it => addOverseasRow(it.name, it.close, it.change, it.change_pct));
    if (!ov.us_markets || !ov.us_markets.length) [['道琼斯',''],['纳斯达克',''],['标普500','']].forEach(([n]) => addOverseasRow(n));

    const otherGrid = document.getElementById('mrOtherGrid');
    otherGrid.innerHTML = '';
    (ov.other_markets || []).forEach(it => addOtherRow(it.name, it.close, it.change, it.change_pct));
    if (!ov.other_markets || !ov.other_markets.length) [['恒生指数',''],['黄金',''],['原油','']].forEach(([n]) => addOtherRow(n));

    setVal('mrOverseasSummary', ov.summary || '');
  }

  // 二、财经大事
  if (sd.section2_events) {
    const ev = sd.section2_events;
    document.getElementById('mrEventsList').innerHTML = '';
    (ev.items || []).forEach(it => addEventItem(it.event, it.impact, it.affected_sectors));
    if (!ev.items || !ev.items.length) addEventItem();
    setVal('mrEventsSummary', ev.summary || '');
  }

  // 三、关注方向
  if (sd.section3_focus) {
    const fc = sd.section3_focus;
    document.getElementById('mrWatchSectors').innerHTML = '';
    (fc.watch_sectors || []).forEach(it => addWatchSector(it.name, it.reason));
    if (!fc.watch_sectors || !fc.watch_sectors.length) { addWatchSector(); addWatchSector(); }
    document.getElementById('mrWarnSectors').innerHTML = '';
    (fc.warn_sectors || []).forEach(it => addWarnSector(it.name, it.reason));
    if (!fc.warn_sectors || !fc.warn_sectors.length) addWarnSector();
    setVal('mrFocusSummary', fc.summary || '');
  }

  // 四、操作建议
  if (sd.section4_advice) {
    const ad = sd.section4_advice;
    setVal('mrBuyStrength', ad.buy_strength || '');
    setVal('mrBuyAdvice',   ad.buy_advice   || '');
    setVal('mrSellStrength',ad.sell_strength|| '');
    setVal('mrSellAdvice',  ad.sell_advice  || '');
    setVal('mrRiskNote',    ad.risk_note    || '');
  }

  // 五、今日计划
  if (sd.section5_plan) {
    const pl = sd.section5_plan;
    document.getElementById('mrPlanList').innerHTML = '';
    (pl.items || []).forEach(it => addPlanItem(it.type, it.content, it.done));
    if (!pl.items || !pl.items.length) addPlanItem('买入');
    setVal('mrPreOpenCheck', pl.pre_open_check || '');
  }
}

/* ---- 动态行：外围市场（美股） ---- */
function addOverseasRow(name='', close='', change='', changePct='') {
  const grid = document.getElementById('mrOverseasGrid');
  const div  = document.createElement('div');
  div.className = 'idx-input-row';
  div.innerHTML = `
    <input type="text" class="form-input" placeholder="指数名" value="${escAttr(name)}" data-field="name" style="flex:1.5">
    <input type="text" class="form-input" placeholder="收盘价" value="${escAttr(close)}" data-field="close" style="flex:1">
    <input type="text" class="form-input" placeholder="涨跌" value="${escAttr(change)}" data-field="change" style="flex:1">
    <input type="text" class="form-input" placeholder="涨跌%" value="${escAttr(changePct)}" data-field="change_pct" style="flex:1">
    <button class="btn-icon-sm" onclick="this.closest('.idx-input-row').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
  `;
  grid.appendChild(div);
}

/* ---- 动态行：港股/期货/商品 ---- */
function addOtherRow(name='', close='', change='', changePct='') {
  const grid = document.getElementById('mrOtherGrid');
  const div  = document.createElement('div');
  div.className = 'idx-input-row';
  div.innerHTML = `
    <input type="text" class="form-input" placeholder="品种名" value="${escAttr(name)}" data-field="name" style="flex:1.5">
    <input type="text" class="form-input" placeholder="收盘价" value="${escAttr(close)}" data-field="close" style="flex:1">
    <input type="text" class="form-input" placeholder="涨跌" value="${escAttr(change)}" data-field="change" style="flex:1">
    <input type="text" class="form-input" placeholder="涨跌%" value="${escAttr(changePct)}" data-field="change_pct" style="flex:1">
    <button class="btn-icon-sm" onclick="this.closest('.idx-input-row').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
  `;
  grid.appendChild(div);
}

/* ---- 动态行：财经大事 ---- */
function addEventItem(event='', impact='', affectedSectors='') {
  const list = document.getElementById('mrEventsList');
  const div  = document.createElement('div');
  div.className = 'mr-event-item';
  div.innerHTML = `
    <div class="mr-event-row">
      <select class="form-input event-impact-select" style="flex:0 0 100px">
        <option value="" ${!impact?'selected':''}>影响性质</option>
        <option value="positive" ${impact==='positive'?'selected':''}>▲ 利好</option>
        <option value="negative" ${impact==='negative'?'selected':''}>▼ 利空</option>
        <option value="neutral"  ${impact==='neutral' ?'selected':''}>● 中性</option>
      </select>
      <input type="text" class="form-input event-content" placeholder="财经事件描述" value="${escAttr(event)}" style="flex:1">
      <button class="btn-icon-sm" onclick="this.closest('.mr-event-item').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <input type="text" class="form-input event-sectors" placeholder="相关板块（如：银行、券商）" value="${escAttr(affectedSectors)}" style="margin-top:6px;font-size:12px">
  `;
  list.appendChild(div);
}

/* ---- 动态行：关注板块 ---- */
function addWatchSector(name='', reason='') {
  const container = document.getElementById('mrWatchSectors');
  const div = document.createElement('div');
  div.className = 'focus-sector-item watch-item';
  div.innerHTML = `
    <input type="text" class="form-input" placeholder="板块名称" value="${escAttr(name)}" data-field="name">
    <input type="text" class="form-input" placeholder="关注原因（可选）" value="${escAttr(reason)}" data-field="reason" style="font-size:12px">
    <button class="btn-icon-sm" onclick="this.closest('.focus-sector-item').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
  `;
  container.appendChild(div);
}

/* ---- 动态行：注意板块 ---- */
function addWarnSector(name='', reason='') {
  const container = document.getElementById('mrWarnSectors');
  const div = document.createElement('div');
  div.className = 'focus-sector-item warn-item';
  div.innerHTML = `
    <input type="text" class="form-input" placeholder="板块名称" value="${escAttr(name)}" data-field="name">
    <input type="text" class="form-input" placeholder="注意原因（可选）" value="${escAttr(reason)}" data-field="reason" style="font-size:12px">
    <button class="btn-icon-sm" onclick="this.closest('.focus-sector-item').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
  `;
  container.appendChild(div);
}

/* ---- 动态行：今日计划 ---- */
function addPlanItem(type='', content='', done=false) {
  const list = document.getElementById('mrPlanList');
  const div  = document.createElement('div');
  div.className = 'mr-plan-item';
  const typeOptions = ['买入','卖出','观察','调研','其他'].map(t =>
    `<option value="${t}" ${type===t?'selected':''}>${t}</option>`
  ).join('');
  div.innerHTML = `
    <div class="mr-plan-row">
      <label class="plan-done-check" title="标记完成">
        <input type="checkbox" ${done?'checked':''}>
      </label>
      <select class="form-input plan-type-select" style="flex:0 0 80px">
        <option value="" ${!type?'selected':''}>类型</option>
        ${typeOptions}
      </select>
      <input type="text" class="form-input plan-content" placeholder="计划内容（标的/条件/价格）" value="${escAttr(content)}" style="flex:1">
      <button class="btn-icon-sm" onclick="this.closest('.mr-plan-item').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
    </div>
  `;
  list.appendChild(div);
}

/* ---- 收集并保存早报 ---- */
function _collectOverseasRows(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} .idx-input-row`)).map(row => ({
    name:       row.querySelector('[data-field="name"]')?.value.trim()       || '',
    close:      row.querySelector('[data-field="close"]')?.value.trim()      || '',
    change:     row.querySelector('[data-field="change"]')?.value.trim()     || '',
    change_pct: row.querySelector('[data-field="change_pct"]')?.value.trim() || '',
  })).filter(r => r.name);
}

function _collectEventItems() {
  return Array.from(document.querySelectorAll('#mrEventsList .mr-event-item')).map(div => ({
    impact:           div.querySelector('.event-impact-select')?.value || '',
    event:            div.querySelector('.event-content')?.value.trim() || '',
    affected_sectors: div.querySelector('.event-sectors')?.value.trim() || '',
  })).filter(r => r.event);
}

function _collectFocusSectors(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} .focus-sector-item`)).map(div => ({
    name:   div.querySelector('[data-field="name"]')?.value.trim()   || '',
    reason: div.querySelector('[data-field="reason"]')?.value.trim() || '',
  })).filter(r => r.name);
}

function _collectPlanItems() {
  return Array.from(document.querySelectorAll('#mrPlanList .mr-plan-item')).map(div => ({
    done:    div.querySelector('input[type="checkbox"]')?.checked || false,
    type:    div.querySelector('.plan-type-select')?.value  || '',
    content: div.querySelector('.plan-content')?.value.trim() || '',
  })).filter(r => r.content || r.type);
}

async function saveMorning() {
  const title = val('mrTitle');
  const now   = new Date();
  const time  = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

  const sd = {
    section1_overseas: {
      us_markets:    _collectOverseasRows('mrOverseasGrid'),
      other_markets: _collectOverseasRows('mrOtherGrid'),
      summary:       val('mrOverseasSummary'),
    },
    section2_events: {
      items:   _collectEventItems(),
      summary: val('mrEventsSummary'),
    },
    section3_focus: {
      watch_sectors: _collectFocusSectors('mrWatchSectors'),
      warn_sectors:  _collectFocusSectors('mrWarnSectors'),
      summary:       val('mrFocusSummary'),
    },
    section4_advice: {
      buy_strength:  val('mrBuyStrength'),
      buy_advice:    val('mrBuyAdvice'),
      sell_strength: val('mrSellStrength'),
      sell_advice:   val('mrSellAdvice'),
      risk_note:     val('mrRiskNote'),
    },
    section5_plan: {
      items:          _collectPlanItems(),
      pre_open_check: val('mrPreOpenCheck'),
    },
  };

  // 生成摘要文字
  const watchNames = (sd.section3_focus.watch_sectors || []).map(s => s.name).filter(Boolean).join('、');
  const warnNames  = (sd.section3_focus.warn_sectors  || []).map(s => s.name).filter(Boolean).join('、');
  const usSummary  = (sd.section1_overseas.us_markets || []).map(m => `${m.name} ${m.change_pct}%`).filter(m => m.trim() !== '%').join('  ');
  const planCount  = sd.section5_plan.items.length;
  let content = '';
  if (usSummary)   content += `外围：${usSummary}\n`;
  if (watchNames)  content += `关注：${watchNames}\n`;
  if (warnNames)   content += `注意：${warnNames}\n`;
  if (sd.section4_advice.buy_strength) content += `操作：${sd.section4_advice.buy_strength}\n`;
  if (planCount)   content += `今日计划 ${planCount} 条`;

  try {
    await apiFetch('/stock/api/daily', {
      method: 'POST',
      body: JSON.stringify({
        date: formatDate(state.dailyDate),
        type: 'morning',
        title: title || '早盘报道',
        content: content.trim(),
        sentiment: state.mrSentiment || 'neutral',
        time,
        structured_data: sd
      })
    });
    closeModal('morningModal');
    renderDaily();
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

/* ========================================================
   早盘编辑器（简单版，保留备用）
   ======================================================== */
async function openEditor(type) {
  state.currentEditor = type;
  let existing = null;
  const date = formatDate(state.dailyDate);
  try {
    const data = await apiFetch(`/stock/api/daily?date=${date}`);
    existing = data[type] || null;
  } catch(e) {}

  const titles = { morning:'早盘报道', afternoon:'盘后总结（简）', weeklySummary:'本周总结（简）' };
  document.getElementById('modalTitle').textContent = titles[type] || '编辑记录';
  document.getElementById('editorTitle').value   = existing?.title   || '';
  document.getElementById('editorContent').value = existing?.content || '';
  setSentiment(existing?.sentiment || 'neutral');
  openModal('editorModal');
}

function setSentiment(val) {
  state.currentSentiment = val;
  document.querySelectorAll('.sentiment-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.value === val);
  });
}

async function saveReport() {
  const title   = document.getElementById('editorTitle').value.trim();
  const content = document.getElementById('editorContent').value.trim();
  if (!content) { alert('请填写内容'); return; }
  const now  = new Date();
  const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  const type = state.currentEditor;
  try {
    await apiFetch('/stock/api/daily', {
      method: 'POST',
      body: JSON.stringify({
        date: formatDate(state.dailyDate),
        type, title, content,
        sentiment: state.currentSentiment, time
      })
    });
    closeModal('editorModal');
    renderDaily();
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

function insertTemplate(type) {
  const templates = {
    morning:   `【大盘研判】\n今日大盘预计走势：\n\n【重点关注个股】\n1. \n2. \n3. \n\n【操作计划】\n`,
    afternoon: `【大盘复盘】\n今日大盘表现：\n\n【持仓情况】\n盈亏情况：\n\n【今日操作】\n买入：\n卖出：\n\n【经验总结】\n`
  };
  const tpl = templates[type === 'morning' ? 'morning' : 'afternoon'];
  const ta = document.getElementById('editorContent');
  ta.value = tpl;
  ta.focus();
}

/* ========================================================
   盘后结构化编辑器
   ======================================================== */
function setAfSentiment(v) {
  state.afSentiment = v;
  document.querySelectorAll('#afternoonModal .sentiment-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.value === v);
  });
}

async function openAfternoonEditor() {
  state.afSentiment = 'neutral';

  // 初始化 UI
  _initAfternoonEditor();

  // 读取已存内容
  const date = formatDate(state.dailyDate);
  try {
    const data = await apiFetch(`/stock/api/daily?date=${date}`);
    const af = data.afternoon;
    if (af) {
      setVal('afTitle', af.title);
      setAfSentiment(af.sentiment || 'neutral');
      const sd = af.structured_data || {};
      _fillAfternoonFields(sd);
    }
  } catch(e) {}

  openModal('afternoonModal');
}

function _initAfternoonEditor() {
  // 初始化默认指数行
  const grid = document.getElementById('afIndicesGrid');
  grid.innerHTML = '';
  ['上证指数','深证成指','创业板指','北证50'].forEach(name => addIndexRow(name));

  // 清空板块
  document.getElementById('afTopSectors').innerHTML = '';
  addTopSector(); addTopSector(); addTopSector();
  document.getElementById('addSectorBtn').style.display = '';

  // 清空个股
  document.getElementById('afStockReviews').innerHTML = '';

  // 清空表单
  ['afTrend','afNorthFund','afMainFund','afFundDetail','afSentimentLevel',
   'afVolume','afAdvance','afDecline','afSentimentDetail','afTrendDetail',
   'afLinkage','afLinkageDetail','afRotation',
   'afTargetSectors','afBuyPlan','afSellPlan','afRiskWarning','afTitle'].forEach(id => setVal(id, ''));
}

function _fillAfternoonFields(sd) {
  // 一、指数
  if (sd.section1_indices && sd.section1_indices.length) {
    const grid = document.getElementById('afIndicesGrid');
    grid.innerHTML = '';
    sd.section1_indices.forEach(idx => {
      addIndexRow(idx.name, idx.close, idx.change, idx.change_pct, idx.vol);
    });
  }
  // 二、市场分析
  if (sd.section2_market) {
    const m = sd.section2_market;
    setVal('afTrend', m.trend);
    setVal('afTrendDetail', m.trend_detail);
    setVal('afNorthFund', m.fund_north);
    setVal('afMainFund', m.fund_main);
    setVal('afFundDetail', m.fund_detail);
    setVal('afSentimentLevel', m.sentiment_level);
    setVal('afVolume', m.volume);
    setVal('afAdvance', m.advance);
    setVal('afDecline', m.decline);
    setVal('afSentimentDetail', m.sentiment_detail);
  }
  // 三、板块
  if (sd.section3_sectors) {
    const s3 = sd.section3_sectors;
    const container = document.getElementById('afTopSectors');
    container.innerHTML = '';
    if (s3.top_sectors && s3.top_sectors.length) {
      s3.top_sectors.forEach(sec => addTopSector(sec));
    } else {
      addTopSector(); addTopSector(); addTopSector();
    }
    setVal('afLinkage', s3.linkage);
    setVal('afLinkageDetail', s3.linkage_detail);
    setVal('afRotation', s3.rotation);
  }
  // 四、个股
  if (sd.section4_stocks && sd.section4_stocks.length) {
    document.getElementById('afStockReviews').innerHTML = '';
    sd.section4_stocks.forEach(st => addStockReview(st));
  }
  // 五、计划
  if (sd.section5_plan) {
    const p = sd.section5_plan;
    setVal('afTargetSectors', p.target_sectors);
    setVal('afBuyPlan', p.buy_plan);
    setVal('afSellPlan', p.sell_plan);
    setVal('afRiskWarning', p.risk_warning);
  }
}

/* 添加指数行 */
function addIndexRow(name='', close='', change='', change_pct='', vol='') {
  const grid = document.getElementById('afIndicesGrid');
  const row = document.createElement('div');
  row.className = 'idx-input-row';
  row.innerHTML = `
    <input class="form-input" placeholder="指数名称" value="${escAttr(name)}" data-field="name">
    <input class="form-input" placeholder="收盘价" value="${escAttr(close)}" data-field="close" type="number">
    <input class="form-input" placeholder="涨跌额" value="${escAttr(change)}" data-field="change" type="number">
    <input class="form-input" placeholder="涨跌%"  value="${escAttr(change_pct)}" data-field="change_pct" type="number">
    <input class="form-input" placeholder="成交量" value="${escAttr(vol)}" data-field="vol">
    <button class="btn-icon delete" onclick="this.parentElement.remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
  `;
  grid.appendChild(row);
}

/* 添加领涨板块 */
function addTopSector(data={}) {
  const container = document.getElementById('afTopSectors');
  if (container.children.length >= 3) return;
  const idx = container.children.length + 1;
  const div = document.createElement('div');
  div.className = 'sector-input-block';
  div.innerHTML = `
    <div class="sector-block-header">
      <span>第 ${idx} 大领涨板块</span>
      <button class="btn-icon delete" onclick="this.closest('.sector-input-block').remove();updateSectorNums('af')" title="删除"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="se-row two-col">
      <div class="form-group">
        <label>板块名称</label>
        <input class="form-input" placeholder="如：半导体" value="${escAttr(data.name||'')}" data-field="name">
      </div>
      <div class="form-group">
        <label>驱动因素</label>
        <select class="form-input" data-field="driver">
          <option value="">请选择...</option>
          <option value="政策驱动"  ${data.driver==='政策驱动'?'selected':''}>📋 政策驱动</option>
          <option value="资金推动"  ${data.driver==='资金推动'?'selected':''}>💰 资金推动</option>
          <option value="行业景气"  ${data.driver==='行业景气'?'selected':''}>📈 行业景气</option>
          <option value="消息刺激"  ${data.driver==='消息刺激'?'selected':''}>📰 消息刺激</option>
          <option value="技术突破"  ${data.driver==='技术突破'?'selected':''}>🔬 技术突破</option>
          <option value="超跌反弹"  ${data.driver==='超跌反弹'?'selected':''}>🔄 超跌反弹</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>深度分析（上涨原因、影响、是否可持续）</label>
      <textarea class="form-textarea short" data-field="reason" placeholder="深入分析该板块今日上涨的原因，是否受政策支持，资金是否持续流入，行业景气度如何...">${escHtml(data.reason||'')}</textarea>
    </div>
    <div class="form-group">
      <label>持续性判断</label>
      <select class="form-input" data-field="continuity">
        <option value="">请选择...</option>
        <option value="持续性强，建议重点关注"  ${data.continuity==='持续性强，建议重点关注'?'selected':''}>🔥 持续性强，建议重点关注</option>
        <option value="短期热点，谨慎追高"      ${data.continuity==='短期热点，谨慎追高'?'selected':''}>⚠️ 短期热点，谨慎追高</option>
        <option value="一日游行情，不建议参与"  ${data.continuity==='一日游行情，不建议参与'?'selected':''}>❌ 一日游行情，不建议参与</option>
      </select>
    </div>
  `;
  container.appendChild(div);
  const btn = document.getElementById('addSectorBtn');
  if (btn) btn.style.display = container.children.length >= 3 ? 'none' : '';
}

/* 添加个股分析 */
function addStockReview(data={}) {
  const container = document.getElementById('afStockReviews');
  const div = document.createElement('div');
  div.className = 'stock-review-block';
  div.innerHTML = `
    <div class="sector-block-header">
      <span>个股分析</span>
      <button class="btn-icon delete" onclick="this.closest('.stock-review-block').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="se-row two-col">
      <div class="form-group">
        <label>股票代码</label>
        <input class="form-input" placeholder="如：600519" value="${escAttr(data.code||'')}" data-field="code">
      </div>
      <div class="form-group">
        <label>股票名称</label>
        <input class="form-input" placeholder="如：贵州茅台" value="${escAttr(data.name||'')}" data-field="name">
      </div>
    </div>
    <div class="form-group">
      <label><i class="fa-solid fa-chart-line"></i> 分时图分析（成交量分布 / 主力行为）</label>
      <textarea class="form-textarea short" data-field="minute_analysis" placeholder="分析分时图成交量分布，判断主力是吸筹、出货还是洗盘...">${escHtml(data.minute_analysis||'')}</textarea>
    </div>
    <div class="form-group">
      <label><i class="fa-solid fa-candlestick-chart"></i> K线形态分析</label>
      <textarea class="form-textarea short" data-field="kline_analysis" placeholder="结合前期K线，判断是否形成反转形态（头肩顶底）或持续形态（旗形矩形）...">${escHtml(data.kline_analysis||'')}</textarea>
    </div>
    <div class="form-group">
      <label><i class="fa-solid fa-newspaper"></i> 基本面与消息面分析</label>
      <textarea class="form-textarea short" data-field="news_analysis" placeholder="个股当天重要消息，分析消息对股价的影响...">${escHtml(data.news_analysis||'')}</textarea>
    </div>
  `;
  container.appendChild(div);
}

/* 收集盘后表单数据 */
function collectAfternoonData() {
  // 一、指数
  const indices = [];
  document.querySelectorAll('#afIndicesGrid .idx-input-row').forEach(row => {
    const name       = row.querySelector('[data-field="name"]').value.trim();
    const close      = row.querySelector('[data-field="close"]').value.trim();
    const change     = row.querySelector('[data-field="change"]').value.trim();
    const change_pct = row.querySelector('[data-field="change_pct"]').value.trim();
    const vol        = row.querySelector('[data-field="vol"]').value.trim();
    if (name) indices.push({ name, close, change, change_pct, vol });
  });

  // 二、市场
  const section2 = {
    trend:          val('afTrend'),
    trend_detail:   val('afTrendDetail'),
    fund_north:     val('afNorthFund'),
    fund_main:      val('afMainFund'),
    fund_detail:    val('afFundDetail'),
    sentiment_level:val('afSentimentLevel'),
    volume:         val('afVolume'),
    advance:        val('afAdvance'),
    decline:        val('afDecline'),
    sentiment_detail:val('afSentimentDetail')
  };

  // 三、板块
  const topSectors = [];
  document.querySelectorAll('#afTopSectors .sector-input-block').forEach(blk => {
    const name        = blk.querySelector('[data-field="name"]').value.trim();
    const driver      = blk.querySelector('[data-field="driver"]').value;
    const reason      = blk.querySelector('[data-field="reason"]').value.trim();
    const continuity  = blk.querySelector('[data-field="continuity"]').value;
    if (name) topSectors.push({ name, driver, reason, continuity });
  });
  const section3 = {
    top_sectors:    topSectors,
    linkage:        val('afLinkage'),
    linkage_detail: val('afLinkageDetail'),
    rotation:       val('afRotation')
  };

  // 四、个股
  const section4 = [];
  document.querySelectorAll('#afStockReviews .stock-review-block').forEach(blk => {
    const code            = blk.querySelector('[data-field="code"]').value.trim();
    const name            = blk.querySelector('[data-field="name"]').value.trim();
    const minute_analysis = blk.querySelector('[data-field="minute_analysis"]').value.trim();
    const kline_analysis  = blk.querySelector('[data-field="kline_analysis"]').value.trim();
    const news_analysis   = blk.querySelector('[data-field="news_analysis"]').value.trim();
    if (code || name) section4.push({ code, name, minute_analysis, kline_analysis, news_analysis });
  });

  // 五、计划
  const section5 = {
    target_sectors: val('afTargetSectors'),
    buy_plan:       val('afBuyPlan'),
    sell_plan:      val('afSellPlan'),
    risk_warning:   val('afRiskWarning')
  };

  return {
    section1_indices: indices,
    section2_market:  section2,
    section3_sectors: section3,
    section4_stocks:  section4,
    section5_plan:    section5
  };
}

async function saveAfternoon() {
  const title = val('afTitle');
  const sd    = collectAfternoonData();

  // 生成摘要文字
  const lines = [];
  if (sd.section2_market.trend) lines.push(`趋势：${sd.section2_market.trend}`);
  if (sd.section3_sectors.top_sectors.length) lines.push(`领涨：${sd.section3_sectors.top_sectors.map(s=>s.name).join('/')} `);
  if (sd.section5_plan.target_sectors) lines.push(`次日目标：${sd.section5_plan.target_sectors}`);
  const content = lines.join('；') || '盘后复盘已记录';

  const now  = new Date();
  const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

  try {
    await apiFetch('/stock/api/daily', {
      method: 'POST',
      body: JSON.stringify({
        date: formatDate(state.dailyDate),
        type: 'afternoon',
        title: title || `${formatDate(state.dailyDate)} 盘后复盘`,
        content,
        sentiment: state.afSentiment,
        time,
        structured_data: sd
      })
    });
    closeModal('afternoonModal');
    renderDaily();
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

/* ========================================================
   周报结构化编辑器
   ======================================================== */
function setWkSentiment(v) {
  state.wkSentiment = v;
  document.querySelectorAll('#weeklyModal .sentiment-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.value === v);
  });
}

async function openWeeklyEditor() {
  state.wkSentiment = 'neutral';
  _initWeeklyEditor();

  const wk = getWeekKey(state.weeklyDate);
  try {
    const data = await apiFetch(`/stock/api/weekly?week=${wk}`);
    if (data.summary) {
      setVal('wkTitle', data.summary.title);
      setWkSentiment(data.summary.sentiment || 'neutral');
      const sd = data.summary.structured_data || {};
      _fillWeeklyFields(sd);
    }
    // 回填推荐股票
    if (data.recommend && data.recommend.length) {
      document.getElementById('wkRecommendInputs').innerHTML = '';
      data.recommend.forEach(s => addWkStockInput(s));
      updateWkStockBtn();
    }
  } catch(e) {}

  openModal('weeklyModal');
}

function _initWeeklyEditor() {
  // 指数
  const grid = document.getElementById('wkIndicesGrid');
  grid.innerHTML = '';
  ['上证指数','深证成指','创业板指','北证50','恒生指数'].forEach(name => addWkIndexRow(name));

  // 板块
  document.getElementById('wkTopSectors').innerHTML = '';
  addWkTopSector(); addWkTopSector(); addWkTopSector();
  const btn = document.getElementById('addWkSectorBtn');
  if (btn) btn.style.display = '';

  // 个股
  document.getElementById('wkStockReviews').innerHTML = '';

  // 推荐
  document.getElementById('wkRecommendInputs').innerHTML = '';
  updateWkStockBtn();

  // 清空文本
  ['wkTrend','wkTrendDetail','wkNorthFund','wkMainFund','wkFundDetail',
   'wkSentimentLevel','wkVolume','wkSentimentScore','wkSentimentDetail',
   'wkLinkage','wkRotation',
   'wkTargetSectors','wkBuyPlan','wkSellPlan','wkRiskWarning','wkTitle'].forEach(id => setVal(id, ''));
}

function _fillWeeklyFields(sd) {
  // 一、指数
  if (sd.section1_indices && sd.section1_indices.length) {
    const grid = document.getElementById('wkIndicesGrid');
    grid.innerHTML = '';
    sd.section1_indices.forEach(idx => addWkIndexRow(idx.name, idx.close, idx.change, idx.change_pct, idx.vol));
  }
  // 二
  if (sd.section2_market) {
    const m = sd.section2_market;
    setVal('wkTrend', m.trend);
    setVal('wkTrendDetail', m.trend_detail);
    setVal('wkNorthFund', m.fund_north);
    setVal('wkMainFund', m.fund_main);
    setVal('wkFundDetail', m.fund_detail);
    setVal('wkSentimentLevel', m.sentiment_level);
    setVal('wkVolume', m.volume);
    setVal('wkSentimentScore', m.sentiment_score);
    setVal('wkSentimentDetail', m.sentiment_detail);
  }
  // 三
  if (sd.section3_sectors) {
    const s3 = sd.section3_sectors;
    document.getElementById('wkTopSectors').innerHTML = '';
    if (s3.top_sectors && s3.top_sectors.length) {
      s3.top_sectors.forEach(sec => addWkTopSector(sec));
    } else {
      addWkTopSector(); addWkTopSector(); addWkTopSector();
    }
    setVal('wkLinkage', s3.linkage);
    setVal('wkRotation', s3.rotation);
  }
  // 四
  if (sd.section4_stocks && sd.section4_stocks.length) {
    document.getElementById('wkStockReviews').innerHTML = '';
    sd.section4_stocks.forEach(st => addWkStockReview(st));
  }
  // 五
  if (sd.section5_plan) {
    const p = sd.section5_plan;
    setVal('wkTargetSectors', p.target_sectors);
    setVal('wkBuyPlan', p.buy_plan);
    setVal('wkSellPlan', p.sell_plan);
    setVal('wkRiskWarning', p.risk_warning);
  }
}

function addWkIndexRow(name='', close='', change='', change_pct='', vol='') {
  const grid = document.getElementById('wkIndicesGrid');
  const row = document.createElement('div');
  row.className = 'idx-input-row';
  row.innerHTML = `
    <input class="form-input" placeholder="指数名称" value="${escAttr(name)}" data-field="name">
    <input class="form-input" placeholder="周收盘价" value="${escAttr(close)}" data-field="close" type="number">
    <input class="form-input" placeholder="周涨跌额" value="${escAttr(change)}" data-field="change" type="number">
    <input class="form-input" placeholder="周涨跌%"  value="${escAttr(change_pct)}" data-field="change_pct" type="number">
    <input class="form-input" placeholder="周成交量" value="${escAttr(vol)}" data-field="vol">
    <button class="btn-icon delete" onclick="this.parentElement.remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
  `;
  grid.appendChild(row);
}

function addWkTopSector(data={}) {
  const container = document.getElementById('wkTopSectors');
  if (container.children.length >= 3) return;
  const idx = container.children.length + 1;
  const div = document.createElement('div');
  div.className = 'sector-input-block';
  div.innerHTML = `
    <div class="sector-block-header">
      <span>第 ${idx} 大领涨板块（周）</span>
      <button class="btn-icon delete" onclick="this.closest('.sector-input-block').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="se-row two-col">
      <div class="form-group">
        <label>板块名称</label>
        <input class="form-input" placeholder="如：新能源" value="${escAttr(data.name||'')}" data-field="name">
      </div>
      <div class="form-group">
        <label>驱动因素</label>
        <select class="form-input" data-field="driver">
          <option value="">请选择...</option>
          <option value="政策驱动"  ${data.driver==='政策驱动'?'selected':''}>📋 政策驱动</option>
          <option value="资金推动"  ${data.driver==='资金推动'?'selected':''}>💰 资金推动</option>
          <option value="行业景气"  ${data.driver==='行业景气'?'selected':''}>📈 行业景气</option>
          <option value="消息刺激"  ${data.driver==='消息刺激'?'selected':''}>📰 消息刺激</option>
          <option value="技术突破"  ${data.driver==='技术突破'?'selected':''}>🔬 技术突破</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>周度深度分析</label>
      <textarea class="form-textarea short" data-field="reason" placeholder="本周该板块的核心逻辑，驱动因素是否可持续，下周展望...">${escHtml(data.reason||'')}</textarea>
    </div>
  `;
  container.appendChild(div);
  const btn = document.getElementById('addWkSectorBtn');
  if (btn) btn.style.display = container.children.length >= 3 ? 'none' : '';
}

function addWkStockReview(data={}) {
  const container = document.getElementById('wkStockReviews');
  const div = document.createElement('div');
  div.className = 'stock-review-block';
  div.innerHTML = `
    <div class="sector-block-header">
      <span>个股周度分析</span>
      <button class="btn-icon delete" onclick="this.closest('.stock-review-block').remove()" title="删除"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="se-row two-col">
      <div class="form-group">
        <label>股票代码</label>
        <input class="form-input" placeholder="如：300750" value="${escAttr(data.code||'')}" data-field="code">
      </div>
      <div class="form-group">
        <label>股票名称</label>
        <input class="form-input" placeholder="如：宁德时代" value="${escAttr(data.name||'')}" data-field="name">
      </div>
    </div>
    <div class="form-group">
      <label>周K线形态分析</label>
      <textarea class="form-textarea short" data-field="kline_analysis" placeholder="本周K线形态，支撑压力位，趋势方向...">${escHtml(data.kline_analysis||'')}</textarea>
    </div>
    <div class="form-group">
      <label>基本面 / 消息面</label>
      <textarea class="form-textarea short" data-field="news_analysis" placeholder="本周重要消息，基本面变化...">${escHtml(data.news_analysis||'')}</textarea>
    </div>
  `;
  container.appendChild(div);
}

/* 收集周报数据 */
function collectWeeklyData() {
  // 一
  const indices = [];
  document.querySelectorAll('#wkIndicesGrid .idx-input-row').forEach(row => {
    const name       = row.querySelector('[data-field="name"]').value.trim();
    const close      = row.querySelector('[data-field="close"]').value.trim();
    const change     = row.querySelector('[data-field="change"]').value.trim();
    const change_pct = row.querySelector('[data-field="change_pct"]').value.trim();
    const vol        = row.querySelector('[data-field="vol"]').value.trim();
    if (name) indices.push({ name, close, change, change_pct, vol });
  });

  // 二
  const section2 = {
    trend:          val('wkTrend'),
    trend_detail:   val('wkTrendDetail'),
    fund_north:     val('wkNorthFund'),
    fund_main:      val('wkMainFund'),
    fund_detail:    val('wkFundDetail'),
    sentiment_level:val('wkSentimentLevel'),
    volume:         val('wkVolume'),
    sentiment_score:val('wkSentimentScore'),
    sentiment_detail:val('wkSentimentDetail')
  };

  // 三
  const topSectors = [];
  document.querySelectorAll('#wkTopSectors .sector-input-block').forEach(blk => {
    const name   = blk.querySelector('[data-field="name"]').value.trim();
    const driver = blk.querySelector('[data-field="driver"]').value;
    const reason = blk.querySelector('[data-field="reason"]').value.trim();
    if (name) topSectors.push({ name, driver, reason });
  });
  const section3 = {
    top_sectors: topSectors,
    linkage:     val('wkLinkage'),
    rotation:    val('wkRotation')
  };

  // 四
  const section4 = [];
  document.querySelectorAll('#wkStockReviews .stock-review-block').forEach(blk => {
    const code          = blk.querySelector('[data-field="code"]').value.trim();
    const name          = blk.querySelector('[data-field="name"]').value.trim();
    const kline_analysis = blk.querySelector('[data-field="kline_analysis"]').value.trim();
    const news_analysis  = blk.querySelector('[data-field="news_analysis"]').value.trim();
    if (code || name) section4.push({ code, name, kline_analysis, news_analysis });
  });

  // 五
  const section5 = {
    target_sectors: val('wkTargetSectors'),
    buy_plan:       val('wkBuyPlan'),
    sell_plan:      val('wkSellPlan'),
    risk_warning:   val('wkRiskWarning')
  };

  return {
    section1_indices: indices,
    section2_market:  section2,
    section3_sectors: section3,
    section4_stocks:  section4,
    section5_plan:    section5
  };
}

/* 周报推荐股票 */
function addWkStockInput(s={}) {
  const container = document.getElementById('wkRecommendInputs');
  if (container.children.length >= 5) return;
  const row = document.createElement('div');
  row.className = 'stock-input-row';
  row.innerHTML = `
    <input class="form-input" placeholder="代码" value="${escAttr(s.code||'')}" data-field="code">
    <input class="form-input" placeholder="名称" value="${escAttr(s.name||'')}" data-field="name">
    <select class="form-input" data-field="market">
      <option value="A"  ${s.market==='A' ?'selected':''}>A股</option>
      <option value="HK" ${s.market==='HK'?'selected':''}>港股</option>
      <option value="US" ${s.market==='US'?'selected':''}>美股</option>
    </select>
    <input class="form-input" placeholder="推荐理由（可选）" value="${escAttr(s.reason||'')}" data-field="reason">
    <button class="btn-remove-stock" onclick="this.parentElement.remove();updateWkStockBtn()"><i class="fa-solid fa-xmark"></i></button>
  `;
  container.appendChild(row);
  updateWkStockBtn();
}

function updateWkStockBtn() {
  const count = document.getElementById('wkRecommendInputs').children.length;
  const btn   = document.getElementById('addWkStockBtn');
  if (btn) {
    btn.style.display = count >= 5 ? 'none' : '';
    if (count < 5) btn.textContent = `+ 添加股票（${count}/5）`;
  }
}

async function saveWeekly() {
  const title = val('wkTitle');
  const sd    = collectWeeklyData();
  const wk    = getWeekKey(state.weeklyDate);

  // 摘要文字
  const lines = [];
  if (sd.section2_market.trend) lines.push(`趋势：${sd.section2_market.trend}`);
  if (sd.section3_sectors.top_sectors.length) lines.push(`领涨：${sd.section3_sectors.top_sectors.map(s=>s.name).join('/')}`);
  const content = lines.join('；') || '周报已记录';

  const now  = new Date();
  const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

  // 收集推荐股票
  const stocks = [];
  document.querySelectorAll('#wkRecommendInputs .stock-input-row').forEach(row => {
    const code   = row.querySelector('[data-field="code"]').value.trim();
    const name   = row.querySelector('[data-field="name"]').value.trim();
    const market = row.querySelector('[data-field="market"]').value;
    const reason = row.querySelector('[data-field="reason"]').value.trim();
    if (code || name) stocks.push({ code, name, market, reason });
  });

  try {
    await apiFetch('/stock/api/weekly/summary', {
      method: 'POST',
      body: JSON.stringify({
        week: wk,
        title: title || `${wk} 周报`,
        content,
        sentiment: state.wkSentiment,
        time,
        structured_data: sd
      })
    });
    await apiFetch('/stock/api/weekly/recommend', {
      method: 'POST',
      body: JSON.stringify({ week: wk, stocks })
    });
    closeModal('weeklyModal');
    renderWeekly();
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

/* ========================================================
   推荐股票编辑器（独立弹窗，从关注板块使用）
   ======================================================== */
async function openRecommendEditor() {
  const wk = getWeekKey(state.weeklyDate);
  let existing = [];
  try {
    const data = await apiFetch(`/stock/api/weekly?week=${wk}`);
    existing = data.recommend || [];
  } catch(e) {}

  const container = document.getElementById('recommendStockInputs');
  container.innerHTML = '';
  if (existing.length) {
    existing.forEach(s => addStockInput(s));
  } else {
    addStockInput();
  }
  updateAddStockBtn();
  openModal('recommendModal');
}

function addStockInput(s={}) {
  const container = document.getElementById('recommendStockInputs');
  const count = container.children.length;
  if (count >= 5) return;
  const row = document.createElement('div');
  row.className = 'stock-input-row';
  row.innerHTML = `
    <input class="form-input" placeholder="代码" value="${escAttr(s.code||'')}" data-field="code">
    <input class="form-input" placeholder="名称" value="${escAttr(s.name||'')}" data-field="name">
    <select class="form-input" data-field="market">
      <option value="A"  ${s.market==='A' ?'selected':''}>A股</option>
      <option value="HK" ${s.market==='HK'?'selected':''}>港股</option>
      <option value="US" ${s.market==='US'?'selected':''}>美股</option>
    </select>
    <input class="form-input" placeholder="推荐理由（可选）" value="${escAttr(s.reason||'')}" data-field="reason">
    <button class="btn-remove-stock" onclick="removeStockInput(this)"><i class="fa-solid fa-xmark"></i></button>
  `;
  container.appendChild(row);
  updateAddStockBtn();
}

function removeStockInput(btn) {
  btn.parentElement.remove();
  updateAddStockBtn();
}

function updateAddStockBtn() {
  const count = document.getElementById('recommendStockInputs').children.length;
  const btn   = document.getElementById('addStockBtn');
  if (btn) {
    btn.style.display = count >= 5 ? 'none' : '';
    btn.textContent   = count >= 5 ? '' : `+ 添加股票（${count}/5）`;
  }
}

async function saveRecommendStocks() {
  const rows   = document.querySelectorAll('#recommendStockInputs .stock-input-row');
  const stocks = [];
  rows.forEach(row => {
    const code   = row.querySelector('[data-field="code"]').value.trim();
    const name   = row.querySelector('[data-field="name"]').value.trim();
    const market = row.querySelector('[data-field="market"]').value;
    const reason = row.querySelector('[data-field="reason"]').value.trim();
    if (code || name) stocks.push({ code, name, market, reason });
  });
  try {
    await apiFetch('/stock/api/weekly/recommend', {
      method: 'POST',
      body: JSON.stringify({ week: getWeekKey(state.weeklyDate), stocks })
    });
    closeModal('recommendModal');
    renderWeekly();
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

/* ========================================================
   持仓 CRUD
   ======================================================== */
async function openHoldingEditor(id) {
  state.editingHoldingId = id !== undefined ? id : null;
  document.getElementById('holdingModalTitle').textContent = id !== undefined ? '编辑持仓' : '添加持仓';
  if (id !== undefined) {
    const h = state.holdings.find(x => x.id === id);
    if (h) {
      setVal('holdingCode', h.code);
      setVal('holdingName', h.name);
      document.getElementById('holdingCost').value         = h.cost          || '';
      document.getElementById('holdingShares').value       = h.shares        || '';
      document.getElementById('holdingCurrentPrice').value = h.current_price || '';
      setVal('holdingMarket', h.market || 'A');
      setVal('holdingNote', h.note);
    }
  } else {
    ['holdingCode','holdingName','holdingCost','holdingShares','holdingCurrentPrice','holdingNote']
      .forEach(i => document.getElementById(i).value = '');
    document.getElementById('holdingMarket').value = 'A';
  }
  openModal('holdingModal');
}

async function saveHolding() {
  const body = {
    code:          document.getElementById('holdingCode').value.trim(),
    name:          document.getElementById('holdingName').value.trim(),
    cost:          document.getElementById('holdingCost').value,
    shares:        document.getElementById('holdingShares').value,
    current_price: document.getElementById('holdingCurrentPrice').value,
    market:        document.getElementById('holdingMarket').value,
    note:          document.getElementById('holdingNote').value.trim()
  };
  if (!body.name && !body.code) { alert('请填写股票名称或代码'); return; }
  try {
    if (state.editingHoldingId !== null) {
      await apiFetch(`/stock/api/holdings/${state.editingHoldingId}`, { method:'PUT', body:JSON.stringify(body) });
    } else {
      await apiFetch('/stock/api/holdings', { method:'POST', body:JSON.stringify(body) });
    }
    closeModal('holdingModal');
    await renderHoldings();
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

async function editHolding(id) { await openHoldingEditor(id); }

async function deleteHolding(id) {
  if (!confirm('确认删除该持仓？')) return;
  try {
    await apiFetch(`/stock/api/holdings/${id}`, { method: 'DELETE' });
    await renderHoldings();
  } catch(e) {
    alert('删除失败：' + e.message);
  }
}

/* ========================================================
   持仓实时报价
   ======================================================== */
async function fetchHoldingQuotes() {
  const holdings = state.holdings || [];
  if (!holdings.length) return;
  const btn = document.getElementById('btnRefreshHoldings');
  if (btn) { btn.disabled = true; btn.querySelector('i').className = 'fa-solid fa-rotate fa-spin'; }

  const codeMap = {};
  holdings.forEach((h, idx) => {
    const tc = toTencentCode(h.code, h.market);
    if (tc) codeMap[tc] = idx;
  });
  const tCodes = Object.keys(codeMap).join(',');
  if (!tCodes) { if (btn) resetBtn(btn); return; }

  try {
    const data = await apiFetch(`/stock/api/quote/stock?codes=${encodeURIComponent(tCodes)}`);
    Object.entries(codeMap).forEach(([tc, idx]) => {
      const h        = holdings[idx];
      const pureCode = tc.replace(/^(sh|sz|hk|us)/i,'');
      const quote    = data[pureCode] || data[h.code];
      if (!quote || !quote.price) return;
      const cur    = quote.price;
      const cost   = parseFloat(h.cost) || 0;
      const shares = parseInt(h.shares) || 0;
      const pnl    = (cur - cost) * shares;
      const pnlPct = cost > 0 ? ((cur - cost) / cost * 100) : 0;
      const cls    = pnl > 0 ? 'pnl-positive' : pnl < 0 ? 'pnl-negative' : 'pnl-zero';
      const sign   = pnl > 0 ? '+' : '';
      const chgCls  = quote.change_pct > 0 ? 'pnl-positive' : quote.change_pct < 0 ? 'pnl-negative' : 'pnl-zero';
      const chgSign = quote.change_pct > 0 ? '+' : '';
      const priceEl = document.getElementById(`h-price-${idx}`);
      const pnlEl   = document.getElementById(`h-pnl-${idx}`);
      const pnlpEl  = document.getElementById(`h-pnlp-${idx}`);
      if (priceEl) priceEl.innerHTML = `${cur.toFixed(2)}<span style="font-size:11px;margin-left:4px" class="${chgCls}">${chgSign}${quote.change_pct.toFixed(2)}%</span>`;
      if (pnlEl)   { pnlEl.textContent  = `${sign}${pnl.toFixed(0)}`;      pnlEl.className  = cls; }
      if (pnlpEl)  { pnlpEl.textContent = `${sign}${pnlPct.toFixed(2)}%`;  pnlpEl.className = cls; }
      state.holdings[idx]._livePrice = cur;
    });
    updateHoldingsSummary();
    const now = new Date();
    const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    const timeEl = document.getElementById('holdingUpdateTime');
    if (timeEl) timeEl.textContent = `更新于 ${t}`;
  } catch(e) {
    const timeEl = document.getElementById('holdingUpdateTime');
    if (timeEl) timeEl.textContent = '报价获取失败';
  } finally {
    if (btn) resetBtn(btn);
  }
}

function resetBtn(btn) {
  btn.disabled = false;
  btn.querySelector('i').className = 'fa-solid fa-rotate';
}

/* ========================================================
   新建按钮
   ======================================================== */
document.getElementById('btnNew').addEventListener('click', () => {
  if (state.currentPage === 'daily')     openMorningEditor();
  else if (state.currentPage === 'weekly')    openWeeklyEditor();
  else if (state.currentPage === 'watchlist') openHoldingEditor();
});

/* ========================================================
   模态框
   ======================================================== */
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('active');
  });
});

/* ========================================================
   实时行情
   ======================================================== */
function toTencentCode(code, market) {
  if (!code) return null;
  const c = code.trim().toUpperCase();
  if (/^(SH|SZ|HK)\d/.test(c)) return c.toLowerCase();
  if (/^(000001|399001|399006)$/.test(c)) return c === '000001' ? 'sh000001' : `sz${c}`;
  if (/^\d{6}$/.test(c)) return (c.startsWith('6') ? 'sh' : 'sz') + c;
  if (market === 'HK') return `hk0${c.padStart(4,'0')}`;
  if (market === 'US') return `us${c.toLowerCase()}`;
  return null;
}

async function fetchIndex() {
  const btn = document.querySelector('.idx-refresh');
  if (btn) btn.classList.add('spinning');
  try {
    const data = await apiFetch('/stock/api/quote/index');
    renderIndex(data);
    const now = new Date();
    const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    document.getElementById('idxUpdateTime').textContent = `更新于 ${t}`;
  } catch(e) {
    document.getElementById('idxUpdateTime').textContent = '行情获取失败，请确认服务已启动';
  } finally {
    if (btn) btn.classList.remove('spinning');
  }
}

function renderIndex(data) {
  const map = { '000001':'idx-000001', '399001':'idx-399001', '399006':'idx-399006' };
  Object.entries(map).forEach(([code, elId]) => {
    const el = document.getElementById(elId);
    if (!el || !data[code]) return;
    const d = data[code];
    const isUp   = d.change_pct > 0;
    const isDown = d.change_pct < 0;
    const cls    = isUp ? 'up' : isDown ? 'down' : 'flat';
    const sign   = isUp ? '+' : '';
    el.querySelector('.idx-price').textContent = d.price.toFixed(2);
    const chgEl = el.querySelector('.idx-change');
    chgEl.textContent = `${sign}${d.change.toFixed(2)} (${sign}${d.change_pct.toFixed(2)}%)`;
    chgEl.className   = `idx-change ${cls}`;
  });
}

async function fetchSector() {
  const body = document.getElementById('sectorBody');
  if (!body) return;
  body.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载中...</div>';
  try {
    const data = await apiFetch('/stock/api/quote/sector');
    if (data.error && !data.sectors?.length) throw new Error(data.error);
    renderSector(data.sectors || []);
  } catch(e) {
    body.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation empty-icon"></i><p>板块数据加载失败</p><small style="color:var(--text-muted)">${e.message}</small></div>`;
  }
}

function renderSector(sectors) {
  const body = document.getElementById('sectorBody');
  if (!body) return;
  if (!sectors.length) { body.innerHTML = '<div class="empty-state"><p>暂无板块数据</p></div>'; return; }
  const maxAbs = Math.max(...sectors.map(s => Math.abs(s.inflow)), 1);
  body.innerHTML = `<div class="sector-list">${sectors.map(s => {
    const isUp    = s.change > 0;
    const isDown  = s.change < 0;
    const chgCls  = isUp ? 'up' : isDown ? 'down' : 'flat';
    const inflowCls = s.inflow >= 0 ? 'positive' : 'negative';
    const barW  = Math.round(Math.abs(s.inflow) / maxAbs * 100);
    const sign  = s.change > 0 ? '+' : '';
    const isign = s.inflow > 0 ? '+' : '';
    return `
      <div class="sector-row">
        <span class="sector-name">${escHtml(s.name)}</span>
        <span class="sector-chg ${chgCls}">${sign}${s.change.toFixed(2)}%</span>
        <span class="sector-inflow ${inflowCls}">${isign}${s.inflow.toFixed(1)}亿</span>
        <div class="sector-bar-wrap">
          <div class="sector-bar ${inflowCls}" style="width:${barW}%"></div>
        </div>
      </div>
    `;
  }).join('')}</div>`;
}

async function fetchNews() {
  const body = document.getElementById('newsBody');
  if (!body) return;
  body.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载中...</div>';
  try {
    const data = await apiFetch('/stock/api/quote/news');
    if (data.error && !data.news?.length) throw new Error(data.error);
    renderNews(data.news || []);
  } catch(e) {
    body.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation empty-icon"></i><p>快讯加载失败</p><small style="color:var(--text-muted)">${e.message}</small></div>`;
  }
}

function renderNews(news) {
  const body = document.getElementById('newsBody');
  if (!body) return;
  if (!news.length) { body.innerHTML = '<div class="empty-state"><p>暂无快讯</p></div>'; return; }
  body.innerHTML = `<div class="news-list">${news.map(n => {
    const time = n.time ? n.time.slice(0,10) : '';
    return `
      <div class="news-item">
        <div class="news-dot"></div>
        <div class="news-content">
          <div class="news-title">${escHtml(n.title)}</div>
          <div class="news-meta">
            ${n.stock ? `<span class="news-stock">${escHtml(n.stock)}</span>` : ''}
            <span class="news-time">${escHtml(time)}</span>
          </div>
        </div>
      </div>
    `;
  }).join('')}</div>`;
}

async function fetchWatchlistQuotes(stocks) {
  // 无参时从关注推荐接口获取
  if (!stocks || !stocks.length) {
    try {
      stocks = await apiFetch('/stock/api/watch/recommend');
    } catch(e) { return; }
  }
  if (!stocks.length) return;
  const codeMap = {};
  stocks.forEach(s => {
    const tc = toTencentCode(s.code, s.market);
    if (tc) codeMap[tc] = s.code;
  });
  const tCodes = Object.keys(codeMap).join(',');
  if (!tCodes) return;
  try {
    const data = await apiFetch(`/stock/api/quote/stock?codes=${encodeURIComponent(tCodes)}`);
    Object.entries(codeMap).forEach(([tc, origCode]) => {
      const pureCode = tc.replace(/^(sh|sz|hk|us)/i,'');
      const quote    = data[pureCode] || data[origCode];
      const quoteEl  = document.getElementById(`ws-quote-${origCode}`);
      if (!quoteEl) return;
      if (!quote) { quoteEl.innerHTML = '<span style="color:var(--text-muted)">暂无报价</span>'; return; }
      const isUp   = quote.change_pct > 0;
      const isDown = quote.change_pct < 0;
      const cls    = isUp ? 'up' : isDown ? 'down' : 'flat';
      const sign   = isUp ? '+' : '';
      quoteEl.innerHTML = `
        <span class="ws-price ${cls}">${quote.price.toFixed(2)}</span>
        <span class="ws-change-badge ${cls}">${sign}${quote.change_pct.toFixed(2)}%</span>
        <div class="ws-quote-detail">
          <span>开 ${quote.open.toFixed(2)}</span>
          <span>高 ${quote.high.toFixed(2)}</span>
          <span>低 ${quote.low.toFixed(2)}</span>
        </div>
      `;
    });
  } catch(e) {
    document.querySelectorAll('.ws-quote').forEach(el => {
      el.innerHTML = '<span style="color:var(--red)">报价获取失败</span>';
    });
  }
}

/* ========================================================
   刷新按钮（查DB → 无则网络抓取 → 存DB → 展示）
   ======================================================== */
async function refreshMorning() {
  const date = formatDate(state.dailyDate);
  const btn  = document.querySelector('.card-morning .btn-refresh-data');
  if (btn) { btn.disabled = true; btn.querySelector('i').className = 'fa-solid fa-rotate fa-spin'; }
  showReportLoading('morning');
  try {
    const res = await apiFetch(`/stock/api/auto/morning?date=${date}`);
    if (res.source === 'future') {
      renderMorningCard(null);  // 未来日期，显示空状态
    } else if (res.data) {
      renderMorningCard(res.data);
    } else {
      renderMorningCard(null);
    }
  } catch(e) {
    renderMorningCard(null);
  } finally {
    if (btn) { btn.disabled = false; btn.querySelector('i').className = 'fa-solid fa-rotate'; }
  }
}

async function refreshAfternoon() {
  const date = formatDate(state.dailyDate);
  const btn  = document.querySelector('.card-afternoon .btn-refresh-data');
  if (btn) { btn.disabled = true; btn.querySelector('i').className = 'fa-solid fa-rotate fa-spin'; }
  showReportLoading('afternoon');
  try {
    const res = await apiFetch(`/stock/api/auto/afternoon?date=${date}`);
    if (res.source === 'future') {
      renderAfternoonCard(null);  // 未来日期，显示空状态
    } else if (res.data) {
      renderAfternoonCard(res.data);
    } else {
      renderAfternoonCard(null);
    }
  } catch(e) {
    renderAfternoonCard(null);
  } finally {
    if (btn) { btn.disabled = false; btn.querySelector('i').className = 'fa-solid fa-rotate'; }
  }
}

async function refreshWeekly() {
  const wk  = getWeekKey(state.weeklyDate);
  const btn = document.querySelector('.card-summary .btn-refresh-data');
  if (btn) { btn.disabled = true; btn.querySelector('i').className = 'fa-solid fa-rotate fa-spin'; }
  const sumEmpty  = document.getElementById('weeklySummaryEmpty');
  const sumReport = document.getElementById('weeklySummaryReport');
  sumEmpty.classList.add('hidden');
  sumReport.classList.remove('hidden');
  sumReport.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> 自动获取中...</div>';
  try {
    const res = await apiFetch(`/stock/api/auto/weekly?week=${wk}`);
    if (res.source === 'future') {
      sumEmpty.classList.remove('hidden');
      sumReport.classList.add('hidden');
      sumReport.innerHTML = '';
      sumEmpty.querySelector('p') && (sumEmpty.querySelector('p').textContent = '未来周暂无数据');
    } else if (res.source === 'past') {
      sumEmpty.classList.remove('hidden');
      sumReport.classList.add('hidden');
      sumReport.innerHTML = '';
      sumEmpty.querySelector('p') && (sumEmpty.querySelector('p').textContent = '历史周数据已过期，无法重新采集');
    } else if (res.data) {
      renderWeeklySummaryCard(res.data);
      // 注意：周总结推荐股只更新 weekly 侧边卡片，不影响关注板块的 watch_recommend
      renderRecommendList(res.data.structured_data?.section6_recommend || []);
    } else {
      sumEmpty.classList.remove('hidden');
      sumReport.classList.add('hidden');
    }
  } catch(e) {
    sumEmpty.classList.remove('hidden');
    sumReport.classList.add('hidden');
  } finally {
    if (btn) { btn.disabled = false; btn.querySelector('i').className = 'fa-solid fa-rotate'; }
  }
}

/* ========================================================
   删除当前周总结
   ======================================================== */
async function deleteWeeklySummary() {
  const wk = getWeekKey(state.weeklyDate);
  const isCurrentWeek = (wk === getWeekKey(new Date()));
  if (!isCurrentWeek) {
    alert('只能删除当前周数据');
    return;
  }
  if (!confirm(`确认删除本周（${wk}）的周总结数据？\n删除后无法恢复，可重新采集。`)) return;

  try {
    const res = await fetch(`/stock/api/weekly/summary?week=${wk}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      // 重置显示
      const sumEmpty  = document.getElementById('weeklySummaryEmpty');
      const sumReport = document.getElementById('weeklySummaryReport');
      sumEmpty.classList.remove('hidden');
      sumReport.classList.add('hidden');
      sumReport.innerHTML = '';
      const p = sumEmpty.querySelector('p');
      if (p) p.textContent = '本周总结尚未记录';
      renderRecommendList([]);
    } else {
      alert(data.error || '删除失败');
    }
  } catch(e) {
    alert('删除请求失败：' + e.message);
  }
}

/* ========================================================
   删除盘后总结（当天及以前均可，方便调试重采）
   ======================================================== */
async function deleteAfternoonReport() {
  const dateStr = formatDate(state.dailyDate);
  const today   = formatDate(new Date());
  if (dateStr > today) {
    alert('未来日期无数据可删');
    return;
  }
  if (!confirm(`确认删除 ${dateStr} 的盘后总结数据？\n删除后可点击刷新按钮重新采集。`)) return;

  try {
    const res = await fetch(`/stock/api/daily/afternoon?date=${dateStr}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      renderAfternoonCard(null);
    } else {
      alert(data.error || '删除失败');
    }
  } catch(e) {
    alert('删除请求失败：' + e.message);
  }
}

/* ========================================================
   删除周总结单只推荐股
   ======================================================== */
async function deleteWeeklyRecommend(code, week) {
  const savedScrollY = window.scrollY;
  try {
    const res  = await fetch(`/stock/api/weekly/recommend/${encodeURIComponent(code)}?week=${week}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      renderRecommendList(data.remaining || []);
      // 双层 rAF：等 reflow 完成后再恢复滚动位置，防止页面跳动
      requestAnimationFrame(() => requestAnimationFrame(() => window.scrollTo(0, savedScrollY)));
    } else {
      alert(data.error || '删除失败');
    }
  } catch(e) {
    alert('删除失败：' + e.message);
  }
}

/* ========================================================
   周总结推荐股：编辑/保存/取消操盘建议
   ======================================================== */
function editWrecAdvice(id) {
  document.getElementById(`wrec-advice-${id}`).style.display = 'none';
  document.getElementById(`wrec-advice-edit-${id}`).style.display = 'block';
}
function cancelWrecAdvice(id) {
  document.getElementById(`wrec-advice-edit-${id}`).style.display = 'none';
  document.getElementById(`wrec-advice-${id}`).style.display = '';
}
async function saveWrecAdvice(id, week) {
  const editBox = document.getElementById(`wrec-advice-edit-${id}`);
  const input   = editBox.querySelector('.wrec-advice-input');
  const advice  = input ? input.value.trim() : '';
  try {
    const res = await fetch(`/stock/api/weekly/recommend/${id}/advice`, {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ advice })
    });
    const data = await res.json();
    if (data.success) {
      const display = document.getElementById(`wrec-advice-${id}`);
      if (advice) {
        display.innerHTML = `<i class="fa-solid fa-lightbulb"></i> ${escHtml(advice)}`;
        display.className = 'ws-advice wrec-advice-display';
        display.style.display = '';
      } else {
        display.style.display = 'none';
      }
      editBox.style.display = 'none';
      showToast('操盘建议已保存');
    } else {
      alert('保存失败');
    }
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

/* ========================================================
   周总结推荐股：加入关注
   ======================================================== */
async function addWrecToWatch(btn) {
  const code   = btn.dataset.code;
  const name   = btn.dataset.name;
  const market = btn.dataset.market;
  const reason = btn.dataset.reason;
  // 取当前卡片里的 advice（如果有编辑中的就取编辑框，否则取 display 文本）
  const id     = btn.dataset.id;
  const editBox = id ? document.getElementById(`wrec-advice-edit-${id}`) : null;
  const input   = editBox ? editBox.querySelector('.wrec-advice-input') : null;
  const displayEl = id ? document.getElementById(`wrec-advice-${id}`) : null;
  // 先从编辑框取，没有则从 display 取纯文本
  let advice = '';
  if (input && editBox && editBox.style.display !== 'none') {
    advice = input.value.trim();
  } else if (displayEl && displayEl.style.display !== 'none') {
    advice = displayEl.textContent.replace(/^\s*\uf0eb\s*/, '').trim(); // 去灯泡 icon 文字
  }
  try {
    const res = await fetch('/stock/api/watch/add', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ code, name, market, reason, advice })
    });
    const data = await res.json();
    if (data.duplicate) {
      showToast(`⚠️ ${name} 已在关注列表中`);
    } else if (data.success) {
      btn.innerHTML = '<i class="fa-solid fa-star" style="color:#f0c040"></i>';
      btn.disabled = true;
      btn.title = '已加入关注';
      showToast(`${name} 已加入关注列表`);
    } else {
      alert(data.error || '操作失败');
    }
  } catch(e) {
    alert('操作失败：' + e.message);
  }
}

/* ========================================================
   刷新下周推荐股票列表：先查DB，空则触发选股策略
   ======================================================== */
async function refreshRecommendList() {
  const btn = document.getElementById('btnRefreshRecommend');
  if (btn) { btn.disabled = true; btn.querySelector('i').classList.add('fa-spin'); }
  try {
    const wk = getWeekKey(state.weeklyDate);
    const data = await apiFetch(`/stock/api/weekly/recommend/pick?week=${wk}`);
    renderRecommendList(data.stocks || []);
    if (data.source === 'pick') {
      // 选股成功，轻提示
      showToast('已用选股策略筛选 ' + (data.stocks||[]).length + ' 只潜力股');
    } else if (data.source === 'empty') {
      showToast('当前暂无符合条件的推荐股票');
    }
  } catch(e) {
    alert('刷新失败：' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.querySelector('i').classList.remove('fa-spin'); }
  }
}

/* ========================================================
   删除关注板块单只推荐股
   ======================================================== */
async function deleteWatchRecommend(id) {
  if (id === null || id === undefined || id === '') return;
  try {
    const res  = await fetch(`/stock/api/watch/recommend/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      // 重新渲染整个关注推荐列表
      const container = document.getElementById('watchlistRecommended');
      const remaining = data.remaining || [];
      document.getElementById('recommendCount').textContent = remaining.length;
      if (!remaining.length) {
        container.innerHTML = `<div class="empty-state">
          <i class="fa-solid fa-rocket empty-icon"></i>
          <p>暂无关注股票，点击右上角"添加"按钮手动添加</p>
        </div>`;
        return;
      }
      container.innerHTML = remaining.map((s, i) => `
        <div class="watchlist-stock-card" id="ws-card-${s.id||i}">
          <div class="ws-header">
            <div>
              <div class="ws-name">${escHtml(s.name)}</div>
              <div class="ws-code">${escHtml(s.code)} · ${escHtml(s.market||'A')}股</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="ws-from">关注 #${i+1}</span>
              <button class="btn-edit-advice" onclick="editWatchAdvice(${s.id||0})" title="编辑操盘建议">
                <i class="fa-solid fa-pen-to-square"></i>
              </button>
              <button class="btn-del-rec" onclick="deleteWatchRecommend(${s.id||0})" title="删除此关注股">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>
          <div class="ws-quote" id="ws-quote-${escHtml(s.code)}">
            <span class="ws-quote-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> 加载报价中...</span>
          </div>
          ${s.reason ? `<div class="ws-reason">${escHtml(s.reason)}</div>` : ''}
          ${s.advice
            ? `<div class="ws-advice watch-advice-display" id="watch-advice-${s.id||i}"><i class="fa-solid fa-lightbulb"></i> ${escHtml(s.advice)}</div>`
            : `<div class="watch-advice-display" id="watch-advice-${s.id||i}" style="display:none"></div>`}
          <div class="wrec-advice-edit" id="watch-advice-edit-${s.id||i}" style="display:none">
            <input type="text" class="form-input wrec-advice-input" placeholder="输入操盘建议…" value="${escHtml(s.advice||'')}">
            <div style="display:flex;gap:6px;margin-top:6px">
              <button class="btn btn-primary" style="padding:4px 12px;font-size:12px" onclick="saveWatchAdvice(${s.id||0})">保存</button>
              <button class="btn btn-outline" style="padding:4px 10px;font-size:12px" onclick="cancelWatchAdvice(${s.id||0})">取消</button>
            </div>
          </div>
        </div>
      `).join('');
      fetchWatchlistQuotes(remaining);
    } else {
      alert(data.error || '删除失败');
    }
  } catch(e) {
    alert('删除失败：' + e.message);
  }
}

/* ========================================================
   关注推荐股：编辑/保存/取消操盘建议
   ======================================================== */
function editWatchAdvice(id) {
  document.getElementById(`watch-advice-${id}`).style.display = 'none';
  document.getElementById(`watch-advice-edit-${id}`).style.display = 'block';
  const input = document.querySelector(`#watch-advice-edit-${id} .wrec-advice-input`);
  if (input) input.focus();
}
function cancelWatchAdvice(id) {
  document.getElementById(`watch-advice-edit-${id}`).style.display = 'none';
  document.getElementById(`watch-advice-${id}`).style.display = '';
}
async function saveWatchAdvice(id) {
  const editBox = document.getElementById(`watch-advice-edit-${id}`);
  const input   = editBox ? editBox.querySelector('.wrec-advice-input') : null;
  const advice  = input ? input.value.trim() : '';
  try {
    const res = await fetch(`/stock/api/watch/recommend/${id}/advice`, {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ advice })
    });
    const data = await res.json();
    if (data.success) {
      const display = document.getElementById(`watch-advice-${id}`);
      if (advice) {
        display.innerHTML = `<i class="fa-solid fa-lightbulb"></i> ${escHtml(advice)}`;
        display.className = 'ws-advice watch-advice-display';
        display.style.display = '';
      } else {
        display.style.display = 'none';
      }
      if (editBox) editBox.style.display = 'none';
      showToast('操盘建议已保存');
    } else {
      alert('保存失败');
    }
  } catch(e) {
    alert('保存失败：' + e.message);
  }
}

/* ========================================================
   股票搜索（输入框自动补全，通用）
   onStockSearch(inputEl, dropdownId, codeFieldId, nameFieldId, marketFieldId)
   ======================================================== */
let _searchTimer = null;

function onStockSearch(inputEl, dropdownId, codeFieldId, nameFieldId, marketFieldId) {
  const q = inputEl.value.trim();
  const dropdown = document.getElementById(dropdownId);
  if (!dropdown) return;

  // 关闭下拉
  if (!q || q.length < 1) {
    dropdown.classList.add('hidden');
    return;
  }

  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(async () => {
    try {
      const results = await apiFetch(`/stock/api/search/stock?q=${encodeURIComponent(q)}`);
      if (!results || !results.length) {
        dropdown.classList.add('hidden');
        return;
      }
      // 找到 list 容器（内层 div）
      const listEl = dropdown.querySelector('div') || dropdown;
      listEl.innerHTML = results.map(r => `
        <div class="stock-search-item"
             data-code="${escAttr(r.code)}"
             data-name="${escAttr(r.name)}"
             data-market="${escAttr(r.market||'A')}"
             onclick="_selectStock(this,'${escAttr(dropdownId)}','${escAttr(codeFieldId)}','${escAttr(nameFieldId)}','${escAttr(marketFieldId)}')">
          <span class="ssi-code">${escHtml(r.code)}</span>
          <span class="ssi-name">${escHtml(r.name)}</span>
          <span class="ssi-market tag tag-blue">${escHtml(r.market||'A')}</span>
        </div>
      `).join('');
      dropdown.classList.remove('hidden');

      // 点击页面其他地方关闭下拉
      const closeHandler = (e) => {
        if (!dropdown.contains(e.target) && e.target !== inputEl) {
          dropdown.classList.add('hidden');
          document.removeEventListener('click', closeHandler);
        }
      };
      document.addEventListener('click', closeHandler);
    } catch(e) {
      dropdown.classList.add('hidden');
    }
  }, 300);
}

function _selectStock(itemEl, dropdownId, codeFieldId, nameFieldId, marketFieldId) {
  const code   = itemEl.dataset.code   || '';
  const name   = itemEl.dataset.name   || '';
  const market = itemEl.dataset.market || 'A';

  const codeEl   = document.getElementById(codeFieldId);
  const nameEl   = document.getElementById(nameFieldId);
  const marketEl = document.getElementById(marketFieldId);

  if (codeEl)   codeEl.value   = code;
  if (nameEl)   nameEl.value   = name;
  if (marketEl) marketEl.value = market;

  const dropdown = document.getElementById(dropdownId);
  if (dropdown) dropdown.classList.add('hidden');
}

/* ========================================================
   手动添加关注股票（关注板块页面）
   ======================================================== */
function openAddWatchStock() {
  // 清空表单
  ['watchCode','watchName','watchReason','watchAdvice'].forEach(id => setVal(id, ''));
  setVal('watchMarket', 'A');
  setVal('watchStockInput', '');
  const dropdown = document.getElementById('watchStockResult');
  if (dropdown) dropdown.classList.add('hidden');
  openModal('addWatchStockModal');
}

async function saveWatchStock() {
  const code   = val('watchCode');
  const name   = val('watchName');
  const market = val('watchMarket') || 'A';
  const reason = val('watchReason');
  const advice = val('watchAdvice');

  if (!code && !name) {
    alert('请输入股票代码或名称');
    return;
  }

  // 添加到关注推荐列表（独立于周报，写入 watch_recommend）
  try {
    // 先取现有的关注列表
    const existing = await apiFetch('/stock/api/watch/recommend');
    const stocks = Array.isArray(existing) ? existing : [];
    // 检查是否已存在
    if (stocks.find(s => s.code === code || s.name === name)) {
      alert('该股票已在关注列表中');
      return;
    }
    stocks.push({ code, name, market, reason, advice });
    await apiFetch('/stock/api/watch/recommend', {
      method: 'POST',
      body: JSON.stringify({ stocks })
    });
    closeModal('addWatchStockModal');
    await renderWatchlistRecommended();
  } catch(e) {
    alert('添加失败：' + e.message);
  }
}

/* ========================================================
   初始化
   ======================================================== */
function init() {
  updateMarketStatus();
  setInterval(updateMarketStatus, 60000);
  document.getElementById('pageDate').textContent = formatDate(new Date());
  renderDaily();
  fetchIndex();
  fetchSector();
  fetchNews();
  setInterval(fetchIndex,  10000);
  setInterval(fetchSector, 60000);
  setInterval(fetchNews,   120000);
}

init();
