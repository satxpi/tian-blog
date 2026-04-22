"""
股票日记 - 后端服务器
端口: 3389
功能:
  1. SQLite 数据库存储 (日报 / 周报 / 持仓)
  2. REST API 供前端读写数据
  3. 行情代理 (腾讯财经 / 东方财富)，解决 CORS 跨域
  4. 静态文件服务 (直接访问 http://127.0.0.1:3389 即可)

日报早盘报道结构化字段（JSON 存储在 structured_data 列，type=morning）:
  section1_overseas  - 一、外围市场 {us_markets:[{name,close,change,change_pct}], other_markets:[...], summary}
  section2_events    - 二、昨日财经大事 {items:[{event,impact,affected_sectors}], summary}
  section3_focus     - 三、今日关注方向 {watch_sectors:[{name,reason}], warn_sectors:[{name,reason}], summary}
  section4_advice    - 四、操作建议 {buy_strength,buy_advice,sell_strength,sell_advice,risk_note}
  section5_plan      - 五、今日计划 {items:[{type,content,done}], pre_open_check}

日报盘后总结结构化字段（JSON 存储在 structured_data 列，type=afternoon）:
  section1_indices   - 一、各大指数数据 (JSON 数组，每项: {name, close, change, change_pct, vol})
  section2_market    - 二、市场整体分析 {trend, fund_flow, sentiment, volume_note, advance_decline}
  section3_sectors   - 三、板块深度剖析 {top_sectors:[{name,reason,driver,continuity}], linkage, rotation}
  section4_stocks    - 四、关注个股回顾 [{code,name,minute_analysis,kline_analysis,news_analysis}]
  section5_plan      - 五、次日计划 {target_sectors,buy_plan,sell_plan,risk_warning}
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs, quote
import json, re, time, os, sqlite3, threading
from datetime import datetime, date as date_cls, timedelta

# ─────────────────────────────────────────────
#  路径配置
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "stock_diary.db")

# ─────────────────────────────────────────────
#  行情缓存
# ─────────────────────────────────────────────
CACHE     = {}
CACHE_TTL = 5   # 行情缓存 5 秒

# ─────────────────────────────────────────────
#  数据库初始化
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 日报表（含结构化字段）
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            date           TEXT NOT NULL,          -- YYYY-MM-DD
            type           TEXT NOT NULL,          -- morning / afternoon
            title          TEXT DEFAULT '',
            content        TEXT DEFAULT '',
            sentiment      TEXT DEFAULT 'neutral',
            time           TEXT DEFAULT '',
            structured_data TEXT DEFAULT '{}',     -- JSON: 结构化五大板块内容
            updated_at     TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(date, type)
        )
    """)

    # 尝试 ALTER TABLE 添加 structured_data 列（若旧库已存在则忽略）
    try:
        c.execute("ALTER TABLE daily_reports ADD COLUMN structured_data TEXT DEFAULT '{}'")
        conn.commit()
    except Exception:
        pass

    # 周报总结表
    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_summary (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            week           TEXT NOT NULL UNIQUE,   -- 周一 YYYY-MM-DD
            title          TEXT DEFAULT '',
            content        TEXT DEFAULT '',
            sentiment      TEXT DEFAULT 'neutral',
            time           TEXT DEFAULT '',
            structured_data TEXT DEFAULT '{}',     -- JSON: 结构化周报内容
            updated_at     TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    try:
        c.execute("ALTER TABLE weekly_summary ADD COLUMN structured_data TEXT DEFAULT '{}'")
        conn.commit()
    except Exception:
        pass

    # 周报推荐股票表
    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_recommend (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            week      TEXT NOT NULL,          -- 周一 YYYY-MM-DD
            rank      INTEGER DEFAULT 0,
            code      TEXT DEFAULT '',
            name      TEXT DEFAULT '',
            market    TEXT DEFAULT 'A',
            reason    TEXT DEFAULT '',
            advice    TEXT DEFAULT ''
        )
    """)
    # 兼容旧数据库：若 advice 列不存在则追加
    try:
        c.execute("ALTER TABLE weekly_recommend ADD COLUMN advice TEXT DEFAULT ''")
    except Exception:
        pass  # 列已存在，忽略

    # 关注板块推荐股（独立于周报，手动维护）
    c.execute("""
        CREATE TABLE IF NOT EXISTS watch_recommend (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            rank       INTEGER DEFAULT 0,
            code       TEXT DEFAULT '',
            name       TEXT DEFAULT '',
            market     TEXT DEFAULT 'A',
            reason     TEXT DEFAULT '',
            advice     TEXT DEFAULT '',
            added_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # 兼容旧数据库：若 advice 列不存在则追加
    try:
        c.execute("ALTER TABLE watch_recommend ADD COLUMN advice TEXT DEFAULT ''")
    except Exception:
        pass  # 列已存在，忽略

    # 持仓表
    c.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            code         TEXT DEFAULT '',
            name         TEXT DEFAULT '',
            market       TEXT DEFAULT 'A',
            cost         REAL DEFAULT 0,
            shares       INTEGER DEFAULT 0,
            current_price REAL DEFAULT 0,
            note         TEXT DEFAULT '',
            created_at   TEXT DEFAULT (datetime('now','localtime')),
            updated_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库已就绪: {DB_PATH}")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
#  HTTP 处理器
# ─────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # 静默日志

    # ---------- CORS ----------
    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    # ---------- 路由分发 ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        qs     = parse_qs(parsed.query)

        # 静态文件：/stock/ 提供页面，根路径不再重定向
        if path in ('/stock', '/stock/'):
            self.serve_file('index.html')
        elif path in ('/stock/app.js',):
            self.serve_file('app.js')
        elif path in ('/stock/style.css',):
            self.serve_file('style.css')
        # API（仅响应 /stock/api/ 前缀）
        elif path == '/stock/api/daily':
            self.api_get_daily(qs)
        elif path == '/stock/api/daily/list':
            self.api_daily_list(qs)
        elif path == '/stock/api/weekly':
            self.api_get_weekly(qs)
        elif path == '/stock/api/weekly/list':
            self.api_weekly_list(qs)
        elif path == '/stock/api/weekly/recommend/pick':
            self.api_pick_weekly_recommend(qs)
        elif path == '/stock/api/watch/recommend':
            self.api_get_watch_recommend()
        elif path == '/stock/api/holdings':
            self.api_get_holdings()
        # 股票搜索
        elif path == '/stock/api/search/stock':
            self.api_search_stock(qs)
        # 自动采集（查DB→抓网络→存DB→返回）
        elif path == '/stock/api/auto/morning':
            self.api_auto_morning(qs)
        elif path == '/stock/api/auto/afternoon':
            self.api_auto_afternoon(qs)
        elif path == '/stock/api/auto/weekly':
            self.api_auto_weekly(qs)
        elif path == '/stock/api/auto/status':
            self.api_auto_status()
        # 行情代理
        elif path == '/stock/api/quote/index':
            self.proxy_index()
        elif path == '/stock/api/quote/stock':
            self.proxy_quote(qs)
        elif path == '/stock/api/quote/sector':
            self.proxy_sector()
        elif path == '/stock/api/quote/news':
            self.proxy_news()
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        body   = self.read_body()

        if path == '/stock/api/daily':
            self.api_save_daily(body)
        elif path == '/stock/api/weekly/summary':
            self.api_save_weekly_summary(body)
        elif path == '/stock/api/weekly/recommend':
            self.api_save_weekly_recommend(body)
        elif path == '/stock/api/watch/recommend':
            self.api_save_watch_recommend(body)
        elif path == '/stock/api/watch/add':
            self.api_watch_add_from_weekly(body)
        elif path == '/stock/api/holdings':
            self.api_add_holding(body)
        else:
            self.send_json({"error": "not found"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        body   = self.read_body()

        m_holding  = re.match(r'^(?:/stock)?/api/holdings/(\d+)$', path)
        m_wrec_adv = re.match(r'^/stock/api/weekly/recommend/(\d+)/advice$', path)
        m_watch_adv = re.match(r'^/stock/api/watch/recommend/(\d+)/advice$', path)
        if m_holding:
            self.api_update_holding(int(m_holding.group(1)), body)
        elif m_wrec_adv:
            self.api_update_weekly_recommend_advice(int(m_wrec_adv.group(1)), body)
        elif m_watch_adv:
            self.api_update_watch_recommend_advice(int(m_watch_adv.group(1)), body)
        else:
            self.send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)
        m_holding = re.match(r'^/stock/api/holdings/(\d+)$', path)
        m_wrec    = re.match(r'^/stock/api/weekly/recommend/(.+)$', path)
        m_watch   = re.match(r'^/stock/api/watch/recommend/(\d+)$', path)
        if m_holding:
            self.api_delete_holding(int(m_holding.group(1)))
        elif m_wrec:
            self.api_delete_weekly_recommend(qs, m_wrec.group(1))
        elif m_watch:
            self.api_delete_watch_recommend(int(m_watch.group(1)))
        elif path == '/stock/api/weekly/summary':
            self.api_delete_weekly_summary(qs)
        elif path == '/stock/api/daily/afternoon':
            self.api_delete_afternoon(qs)
        else:
            self.send_json({"error": "not found"}, 404)

    # ─────────────────────────────────────────
    #  静态文件服务
    # ─────────────────────────────────────────
    def serve_file(self, filename):
        fpath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(fpath):
            self.send_json({"error": "file not found"}, 404)
            return
        ext = filename.rsplit('.', 1)[-1].lower()
        mime_map = {
            'html': 'text/html; charset=utf-8',
            'js':   'application/javascript; charset=utf-8',
            'css':  'text/css; charset=utf-8',
        }
        mime = mime_map.get(ext, 'application/octet-stream')
        with open(fpath, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.send_cors()
        self.end_headers()
        self.wfile.write(data)

    # ─────────────────────────────────────────
    #  日报 API
    # ─────────────────────────────────────────
    def api_get_daily(self, qs):
        date = qs.get('date', [''])[0]
        if not date:
            self.send_json({"error": "date required"}, 400)
            return
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM daily_reports WHERE date=?", (date,)
        ).fetchall()
        conn.close()
        result = {}
        for r in rows:
            sd = {}
            try:
                sd = json.loads(r['structured_data'] or '{}')
            except Exception:
                sd = {}
            result[r['type']] = {
                "title": r['title'], "content": r['content'],
                "sentiment": r['sentiment'], "time": r['time'],
                "structured_data": sd
            }
        self.send_json(result)

    def api_daily_list(self, qs):
        limit = int(qs.get('limit', ['10'])[0])
        conn = get_conn()
        rows = conn.execute("""
            SELECT date, GROUP_CONCAT(type) as types,
                   MAX(content) as preview
            FROM daily_reports
            GROUP BY date
            ORDER BY date DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        result = []
        for r in rows:
            result.append({
                "date": r['date'],
                "types": r['types'].split(',') if r['types'] else [],
                "preview": (r['preview'] or '')[:60]
            })
        self.send_json(result)

    def api_save_daily(self, body):
        date      = body.get('date', '')
        rtype     = body.get('type', '')
        title     = body.get('title', '')
        content   = body.get('content', '')
        sentiment = body.get('sentiment', 'neutral')
        rtime     = body.get('time', '')
        sd        = body.get('structured_data', {})
        sd_json   = json.dumps(sd, ensure_ascii=False)

        if not date or rtype not in ('morning', 'afternoon'):
            self.send_json({"error": "invalid params"}, 400)
            return
        conn = get_conn()
        conn.execute("""
            INSERT INTO daily_reports (date, type, title, content, sentiment, time, structured_data, updated_at)
            VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))
            ON CONFLICT(date, type) DO UPDATE SET
                title=excluded.title, content=excluded.content,
                sentiment=excluded.sentiment, time=excluded.time,
                structured_data=excluded.structured_data,
                updated_at=excluded.updated_at
        """, (date, rtype, title, content, sentiment, rtime, sd_json))
        conn.commit()
        conn.close()
        self.send_json({"ok": True})

    # ─────────────────────────────────────────
    #  周报 API
    # ─────────────────────────────────────────
    def api_get_weekly(self, qs):
        week = qs.get('week', [''])[0]
        if not week:
            self.send_json({"error": "week required"}, 400)
            return
        conn = get_conn()
        sumrow = conn.execute(
            "SELECT * FROM weekly_summary WHERE week=?", (week,)
        ).fetchone()
        recrows = conn.execute(
            "SELECT * FROM weekly_recommend WHERE week=? ORDER BY rank", (week,)
        ).fetchall()
        conn.close()
        result = {}
        if sumrow:
            sd = {}
            try:
                sd = json.loads(sumrow['structured_data'] or '{}')
            except Exception:
                sd = {}
            result['summary'] = {
                "title": sumrow['title'], "content": sumrow['content'],
                "sentiment": sumrow['sentiment'], "time": sumrow['time'],
                "structured_data": sd
            }
        result['recommend'] = [
            {"id": r['id'], "code": r['code'], "name": r['name'],
             "market": r['market'], "reason": r['reason'], "advice": r['advice'] or ''}
            for r in recrows
        ]
        self.send_json(result)

    # ─────────────────────────────────────────
    #  下周推荐股票：查DB→空则选股写DB→返回
    #  GET /api/weekly/recommend/pick?week=YYYY-MM-DD
    # ─────────────────────────────────────────
    def api_pick_weekly_recommend(self, qs):
        week = qs.get('week', [''])[0]
        if not week:
            self.send_json({"source": "error", "error": "week required"}, 400)
            return
        conn = get_conn()
        rows = conn.execute(
            "SELECT id,code,name,market,reason,advice FROM weekly_recommend WHERE week=? ORDER BY rank", (week,)
        ).fetchall()
        conn.close()
        if rows:
            self.send_json({"source": "db", "stocks": [dict(r) for r in rows]})
            return
        # DB 无数据，触发选股策略
        try:
            picked = _pick_weekly_stocks()
        except Exception as e:
            self.send_json({"source": "error", "error": str(e)}, 500)
            return
        if not picked:
            self.send_json({"source": "empty", "stocks": []})
            return
        # 写入 weekly_recommend 表（不再自动同步到 watch_recommend，由用户点关注按钮手动同步）
        conn = get_conn()
        conn.execute("DELETE FROM weekly_recommend WHERE week=?", (week,))
        for i, s in enumerate(picked):
            conn.execute(
                "INSERT INTO weekly_recommend (week, rank, code, name, market, reason, advice) VALUES (?,?,?,?,?,?,?)",
                (week, i+1, s['code'], s['name'], s.get('market','A'), s.get('reason',''), s.get('advice',''))
            )
        conn.commit()
        # 取回带 id 的完整记录
        rows = conn.execute(
            "SELECT id,code,name,market,reason,advice FROM weekly_recommend WHERE week=? ORDER BY rank", (week,)
        ).fetchall()
        conn.close()
        self.send_json({"source": "pick", "stocks": [dict(r) for r in rows]})

    def api_weekly_list(self, qs):
        limit = int(qs.get('limit', ['8'])[0])

        conn = get_conn()
        rows = conn.execute("""
            SELECT ws.week, ws.content as summary_content,
                   COUNT(wr.id) as rec_count
            FROM weekly_summary ws
            LEFT JOIN weekly_recommend wr ON wr.week = ws.week
            GROUP BY ws.week
            ORDER BY ws.week DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        result = []
        for r in rows:
            result.append({
                "week": r['week'],
                "summary_preview": (r['summary_content'] or '')[:50],
                "rec_count": r['rec_count']
            })
        self.send_json(result)

    def api_save_weekly_summary(self, body):
        week = body.get('week', '')
        if not week:
            self.send_json({"error": "week required"}, 400)
            return
        sd      = body.get('structured_data', {})
        sd_json = json.dumps(sd, ensure_ascii=False)
        conn = get_conn()
        conn.execute("""
            INSERT INTO weekly_summary (week, title, content, sentiment, time, structured_data, updated_at)
            VALUES (?,?,?,?,?,?,datetime('now','localtime'))
            ON CONFLICT(week) DO UPDATE SET
                title=excluded.title, content=excluded.content,
                sentiment=excluded.sentiment, time=excluded.time,
                structured_data=excluded.structured_data,
                updated_at=excluded.updated_at
        """, (week, body.get('title',''), body.get('content',''),
              body.get('sentiment','neutral'), body.get('time',''), sd_json))
        conn.commit()
        conn.close()
        self.send_json({"ok": True})

    def api_save_weekly_recommend(self, body):
        week   = body.get('week', '')
        stocks = body.get('stocks', [])
        if not week:
            self.send_json({"error": "week required"}, 400)
            return
        conn = get_conn()
        conn.execute("DELETE FROM weekly_recommend WHERE week=?", (week,))
        for i, s in enumerate(stocks[:5]):
            conn.execute("""
                INSERT INTO weekly_recommend (week, rank, code, name, market, reason, advice)
                VALUES (?,?,?,?,?,?,?)
            """, (week, i, s.get('code',''), s.get('name',''),
                  s.get('market','A'), s.get('reason',''), s.get('advice','')))
        conn.commit()
        conn.close()
        self.send_json({"ok": True})

    # ─────────────────────────────────────────
    #  关注板块推荐股 API（独立于周报，不共用）
    #  GET  /api/watch/recommend
    #  POST /api/watch/recommend  body: {stocks:[{code,name,market,reason}]}
    # ─────────────────────────────────────────
    def api_get_watch_recommend(self):
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM watch_recommend ORDER BY rank, added_at"
        ).fetchall()
        conn.close()
        self.send_json([
            {"id": r['id'], "code": r['code'], "name": r['name'],
             "market": r['market'], "reason": r['reason'],
             "advice": r['advice'] if 'advice' in r.keys() else ''}
            for r in rows
        ])

    def api_save_watch_recommend(self, body):
        stocks = body.get('stocks', [])
        conn = get_conn()
        conn.execute("DELETE FROM watch_recommend")
        for i, s in enumerate(stocks):
            conn.execute("""
                INSERT INTO watch_recommend (rank, code, name, market, reason, advice, added_at)
                VALUES (?,?,?,?,?,?,datetime('now','localtime'))
            """, (i, s.get('code',''), s.get('name',''),
                  s.get('market','A'), s.get('reason',''), s.get('advice','')))
        conn.commit()
        conn.close()
        self.send_json({"ok": True})

    # ─────────────────────────────────────────
    #  持仓 API
    # ─────────────────────────────────────────
    def api_get_holdings(self):
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM holdings ORDER BY created_at"
        ).fetchall()
        conn.close()
        self.send_json([dict(r) for r in rows])

    def api_add_holding(self, body):
        conn = get_conn()
        cur = conn.execute("""
            INSERT INTO holdings (code, name, market, cost, shares, current_price, note, updated_at)
            VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))
        """, (body.get('code',''), body.get('name',''), body.get('market','A'),
              float(body.get('cost',0) or 0), int(body.get('shares',0) or 0),
              float(body.get('current_price',0) or 0), body.get('note','')))
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM holdings WHERE id=?", (new_id,)).fetchone()
        conn.close()
        self.send_json(dict(row))

    def api_update_holding(self, hid, body):
        conn = get_conn()
        conn.execute("""
            UPDATE holdings SET
                code=?, name=?, market=?, cost=?, shares=?,
                current_price=?, note=?, updated_at=datetime('now','localtime')
            WHERE id=?
        """, (body.get('code',''), body.get('name',''), body.get('market','A'),
              float(body.get('cost',0) or 0), int(body.get('shares',0) or 0),
              float(body.get('current_price',0) or 0), body.get('note',''), hid))
        conn.commit()
        row = conn.execute("SELECT * FROM holdings WHERE id=?", (hid,)).fetchone()
        conn.close()
        if row:
            self.send_json(dict(row))
        else:
            self.send_json({"error": "not found"}, 404)

    def api_delete_holding(self, hid):
        conn = get_conn()
        conn.execute("DELETE FROM holdings WHERE id=?", (hid,))
        conn.commit()
        conn.close()
        self.send_json({"ok": True})

    # ─────────────────────────────────────────
    #  股票搜索 API  GET /api/search/stock?q=关键词
    #  返回 [{code, name, market, pinyin}]
    # ─────────────────────────────────────────
    def api_search_stock(self, qs):
        q = qs.get('q', [''])[0].strip()
        if not q:
            self.send_json([])
            return
        cache_key = f"search_{q}"
        cached = CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 60:
            self.send_json(cached[1])
            return
        try:
            # 东方财富股票搜索接口
            url = (f"https://searchapi.eastmoney.com/api/suggest/get"
                   f"?input={quote(q)}&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&count=8")
            req = Request(url, headers={"User-Agent": "Mozilla/5.0",
                                        "Referer": "https://www.eastmoney.com/"})
            raw  = urlopen(req, timeout=6).read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            items = data.get("QuotationCodeTable", {}).get("Data", []) or []
            result = []
            for it in items[:8]:
                code  = it.get("Code", "")
                name  = it.get("Name", "")
                mtype = it.get("MktNum", "")
                # 判断市场
                if mtype in ("1", "2"):
                    market = "A"
                elif mtype in ("31","33"):
                    market = "HK"
                elif mtype in ("105","106","107"):
                    market = "US"
                else:
                    market = "A"
                result.append({"code": code, "name": name, "market": market})
            CACHE[cache_key] = (time.time(), result)
            self.send_json(result)
        except Exception as e:
            # fallback：腾讯搜索
            try:
                url2 = f"https://smartbox.gtimg.cn/s3/?v=2&q={quote(q)}&type=S"
                req2 = Request(url2, headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.qq.com/"})
                raw2 = urlopen(req2, timeout=5).read().decode("utf-8", errors="replace")
                # 格式: v_hint="..."
                m = re.search(r'"([^"]+)"', raw2)
                result = []
                if m:
                    for part in m.group(1).split("^"):
                        fields = part.split("~")
                        if len(fields) >= 2:
                            result.append({"code": fields[1], "name": fields[2] if len(fields)>2 else fields[1], "market": "A"})
                self.send_json(result[:8])
            except Exception:
                self.send_json([])

    # ─────────────────────────────────────────
    #  自动采集状态  GET /api/auto/status
    # ─────────────────────────────────────────
    def api_auto_status(self):
        self.send_json(AUTO_STATUS)

    # ─────────────────────────────────────────
    #  自动采集：早报  GET /api/auto/morning?date=YYYY-MM-DD
    #  逻辑：查DB → 有数据直接返回 → 无则网络抓取 → 存DB → 返回
    # ─────────────────────────────────────────
    def api_auto_morning(self, qs):
        today = qs.get('date', [str(date_cls.today())])[0]
        # ── 未来日期拦截：不允许获取未来日期数据 ──
        try:
            req_date = date_cls.fromisoformat(today)
        except Exception:
            self.send_json({"source": "error", "error": "日期格式无效", "data": None}, 400)
            return
        if req_date > date_cls.today():
            self.send_json({"source": "future", "error": "未来日期暂无数据", "data": None})
            return
        # 1. 查 DB
        conn = get_conn()
        row  = conn.execute(
            "SELECT * FROM daily_reports WHERE date=? AND type='morning'", (today,)
        ).fetchone()
        conn.close()
        if row:
            sd = {}
            try: sd = json.loads(row['structured_data'] or '{}')
            except: pass
            self.send_json({"source": "db", "data": {
                "title": row['title'], "content": row['content'],
                "sentiment": row['sentiment'], "time": row['time'],
                "structured_data": sd
            }})
            return
        # 2. 网络抓取
        try:
            result = fetch_morning_data(today)
            if result:
                save_daily_auto(today, 'morning', result)
                AUTO_STATUS['morning_last'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                AUTO_STATUS['morning_date'] = today
                self.send_json({"source": "fetch", "data": result})
            else:
                self.send_json({"source": "empty", "data": None})
        except Exception as e:
            self.send_json({"source": "error", "error": str(e), "data": None})

    # ─────────────────────────────────────────
    #  自动采集：盘后总结  GET /api/auto/afternoon?date=YYYY-MM-DD
    # ─────────────────────────────────────────
    def api_auto_afternoon(self, qs):
        today = qs.get('date', [str(date_cls.today())])[0]
        # ── 未来日期拦截 ──
        try:
            req_date = date_cls.fromisoformat(today)
        except Exception:
            self.send_json({"source": "error", "error": "日期格式无效", "data": None}, 400)
            return
        if req_date > date_cls.today():
            self.send_json({"source": "future", "error": "未来日期暂无数据", "data": None})
            return
        conn = get_conn()
        row  = conn.execute(
            "SELECT * FROM daily_reports WHERE date=? AND type='afternoon'", (today,)
        ).fetchone()
        conn.close()
        if row:
            sd = {}
            try: sd = json.loads(row['structured_data'] or '{}')
            except: pass
            self.send_json({"source": "db", "data": {
                "title": row['title'], "content": row['content'],
                "sentiment": row['sentiment'], "time": row['time'],
                "structured_data": sd
            }})
            return
        try:
            result = fetch_afternoon_data(today)
            if result:
                save_daily_auto(today, 'afternoon', result)
                AUTO_STATUS['afternoon_last'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                AUTO_STATUS['afternoon_date'] = today
                self.send_json({"source": "fetch", "data": result})
            else:
                self.send_json({"source": "empty", "data": None})
        except Exception as e:
            self.send_json({"source": "error", "error": str(e), "data": None})

    # ─────────────────────────────────────────
    #  自动采集：周总结  GET /api/auto/weekly?week=YYYY-MM-DD
    #  规则：仅当前周可触发网络采集；未来周返回 future；
    #        过期周只查 DB，无数据返回 past（不再抓网络）
    # ─────────────────────────────────────────
    def api_auto_weekly(self, qs):
        week = qs.get('week', [''])[0]
        if not week:
            self.send_json({"source": "error", "error": "week required", "data": None})
            return
        try:
            req_week = date_cls.fromisoformat(week)
        except Exception:
            self.send_json({"source": "error", "error": "日期格式无效", "data": None}, 400)
            return
        this_monday = date_cls.fromisoformat(get_week_monday(date_cls.today()))
        # 未来周拦截
        if req_week > this_monday:
            self.send_json({"source": "future", "error": "未来周暂无数据", "data": None})
            return
        # 查询 DB（无论当前/过期都先查 DB）
        conn = get_conn()
        row  = conn.execute(
            "SELECT * FROM weekly_summary WHERE week=?", (week,)
        ).fetchone()
        conn.close()
        if row:
            sd = {}
            try: sd = json.loads(row['structured_data'] or '{}')
            except: pass
            self.send_json({"source": "db", "data": {
                "title": row['title'], "content": row['content'],
                "sentiment": row['sentiment'], "time": row['time'],
                "structured_data": sd
            }})
            return
        # 过期周：DB 无数据，不再抓网络
        if req_week < this_monday:
            self.send_json({"source": "past", "error": "该周数据已过期，无法重新采集", "data": None})
            return
        # 当前周：DB 无数据，触发网络采集
        try:
            result = fetch_weekly_data(week)
            if result:
                save_weekly_auto(week, result)
                AUTO_STATUS['weekly_last'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                AUTO_STATUS['weekly_week'] = week
                self.send_json({"source": "fetch", "data": result})
            else:
                self.send_json({"source": "empty", "data": None})
        except Exception as e:
            self.send_json({"source": "error", "error": str(e), "data": None})

    # ─────────────────────────────────────────
    #  删除周总结  DELETE /api/weekly/summary?week=YYYY-MM-DD
    #  只允许删除当前周数据
    # ─────────────────────────────────────────
    def api_delete_weekly_summary(self, qs):
        week = qs.get('week', [''])[0]
        if not week:
            self.send_json({"success": False, "error": "week required"}, 400)
            return
        try:
            req_week = date_cls.fromisoformat(week)
        except Exception:
            self.send_json({"success": False, "error": "日期格式无效"}, 400)
            return
        this_monday = date_cls.fromisoformat(get_week_monday(date_cls.today()))
        if req_week != this_monday:
            self.send_json({"success": False, "error": "只能删除当前周数据"}, 403)
            return
        conn = get_conn()
        conn.execute("DELETE FROM weekly_summary WHERE week=?", (week,))
        conn.execute("DELETE FROM weekly_recommend WHERE week=?", (week,))
        conn.commit()
        conn.close()
        self.send_json({"success": True, "message": f"已删除 {week} 周总结数据"})

    # ─────────────────────────────────────────
    #  删除盘后总结  DELETE /api/daily/afternoon?date=YYYY-MM-DD
    #  允许删除今日及以前的数据（方便调试重采）
    # ─────────────────────────────────────────
    def api_delete_afternoon(self, qs):
        date_str = qs.get('date', [''])[0]
        if not date_str:
            self.send_json({"success": False, "error": "date required"}, 400)
            return
        try:
            req_date = date_cls.fromisoformat(date_str)
        except Exception:
            self.send_json({"success": False, "error": "日期格式无效"}, 400)
            return
        if req_date > date_cls.today():
            self.send_json({"success": False, "error": "未来日期无数据可删"}, 403)
            return
        conn = get_conn()
        conn.execute("DELETE FROM daily_reports WHERE date=? AND type='afternoon'", (date_str,))
        conn.commit()
        conn.close()
        self.send_json({"success": True, "message": f"已删除 {date_str} 盘后总结数据"})

    # ─────────────────────────────────────────
    #  删除周总结单只推荐股  DELETE /api/weekly/recommend/<code>?week=YYYY-MM-DD
    # ─────────────────────────────────────────
    def api_delete_weekly_recommend(self, qs, code):
        week = qs.get('week', [''])[0]
        if not week or not code:
            self.send_json({"success": False, "error": "week and code required"}, 400)
            return
        conn = get_conn()
        conn.execute("DELETE FROM weekly_recommend WHERE week=? AND code=?", (week, code))
        conn.commit()
        # 返回剩余推荐股列表
        rows = conn.execute(
            "SELECT id,rank,code,name,market,reason,advice FROM weekly_recommend WHERE week=? ORDER BY rank", (week,)
        ).fetchall()
        conn.close()
        self.send_json({"success": True, "remaining": [dict(r) for r in rows]})

    # ─────────────────────────────────────────
    #  更新周推荐单只股的操盘建议  PUT /api/weekly/recommend/<id>/advice
    # ─────────────────────────────────────────
    def api_update_weekly_recommend_advice(self, rid, body):
        advice = body.get('advice', '')
        conn = get_conn()
        conn.execute("UPDATE weekly_recommend SET advice=? WHERE id=?", (advice, rid))
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    # ─────────────────────────────────────────
    #  把周总结推荐股加入关注  POST /api/watch/add
    #  body: {id, code, name, market, reason, advice}
    # ─────────────────────────────────────────
    def api_watch_add_from_weekly(self, body):
        code   = body.get('code', '').strip()
        name   = body.get('name', '').strip()
        market = body.get('market', 'A')
        reason = body.get('reason', '')
        advice = body.get('advice', '')
        if not code:
            self.send_json({"success": False, "error": "code required"}, 400)
            return
        conn = get_conn()
        existing = conn.execute(
            "SELECT id FROM watch_recommend WHERE code=?", (code,)
        ).fetchone()
        if existing:
            conn.close()
            self.send_json({"success": False, "duplicate": True, "msg": f"{name or code} 已在关注列表中"})
            return
        # 取当前最大 rank
        max_rank = conn.execute("SELECT COALESCE(MAX(rank),0) FROM watch_recommend").fetchone()[0]
        conn.execute(
            "INSERT INTO watch_recommend (rank, code, name, market, reason, advice, added_at) "
            "VALUES (?,?,?,?,?,?,datetime('now','localtime'))",
            (max_rank + 1, code, name, market, reason, advice)
        )
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    # ─────────────────────────────────────────
    #  更新关注推荐单只股的操盘建议  PUT /api/watch/recommend/<id>/advice
    # ─────────────────────────────────────────
    def api_update_watch_recommend_advice(self, rid, body):
        advice = body.get('advice', '')
        conn = get_conn()
        conn.execute("UPDATE watch_recommend SET advice=? WHERE id=?", (advice, rid))
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    # ─────────────────────────────────────────
    #  删除关注推荐单只股  DELETE /api/watch/recommend/<id>
    # ─────────────────────────────────────────
    def api_delete_watch_recommend(self, rid):
        conn = get_conn()
        conn.execute("DELETE FROM watch_recommend WHERE id=?", (rid,))
        conn.commit()
        rows = conn.execute(
            "SELECT id,rank,code,name,market,reason,advice,added_at FROM watch_recommend ORDER BY rank, added_at"
        ).fetchall()
        conn.close()
        self.send_json({"success": True, "remaining": [dict(r) for r in rows]})

    # ─────────────────────────────────────────
    #  行情代理
    # ─────────────────────────────────────────
    def proxy_index(self):
        self.proxy_tencent_quote("sh000001,sz399001,sz399006")

    def proxy_quote(self, qs):
        codes = qs.get('codes', [''])[0]
        if not codes:
            self.send_json({"error": "no codes"}, 400)
            return
        self.proxy_tencent_quote(codes)

    def proxy_tencent_quote(self, codes):
        cache_key = f"quote_{codes}"
        cached = CACHE.get(cache_key)
        if cached and time.time() - cached[0] < CACHE_TTL:
            self.send_json(cached[1])
            return
        try:
            url = f"https://qt.gtimg.cn/q={codes}"
            req = Request(url, headers={
                "Referer": "https://finance.qq.com/",
                "User-Agent": "Mozilla/5.0"
            })
            raw    = urlopen(req, timeout=6).read().decode("gbk", errors="replace")
            result = parse_tencent(raw)
            CACHE[cache_key] = (time.time(), result)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def proxy_sector(self):
        cache_key = "sector"
        cached = CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 30:
            self.send_json(cached[1])
            return
        try:
            url = ("https://push2.eastmoney.com/api/qt/clist/get"
                   "?cb=&pn=1&pz=15&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                   "&fltt=2&invt=2&fid=f62&fs=m:90+t:2"
                   "&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87"
                   "&_=1")
            req = Request(url, headers={
                "Referer": "https://data.eastmoney.com/",
                "User-Agent": "Mozilla/5.0"
            })
            raw  = urlopen(req, timeout=8).read().decode("utf-8", errors="replace")
            raw  = re.sub(r'^\w+\(', '', raw).rstrip(');')
            data = json.loads(raw)
            items   = data.get("data", {}).get("diff", [])
            sectors = []
            for it in items[:10]:
                inflow = it.get("f62", 0) or 0
                chg    = it.get("f3", 0) or 0
                sectors.append({
                    "name":        it.get("f14", ""),
                    "code":        it.get("f12", ""),
                    "change":      round(chg, 2),
                    "inflow":      round(inflow / 1e8, 2),
                    "main_inflow": round((it.get("f66", 0) or 0) / 1e8, 2),
                })
            result = {"sectors": sectors}
            CACHE[cache_key] = (time.time(), result)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e), "sectors": []}, 200)

    def proxy_news(self):
        cache_key = "news"
        cached = CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 60:
            self.send_json(cached[1])
            return

        news = []
        _seen_titles = set()

        # ── 接口一：东方财富7x24快讯，多页合并去重（每页2条，取5页） ──
        try:
            for _page in range(1, 6):
                _url = f"https://newsapi.eastmoney.com/kuaixun/v1/getlist_100_ajaxResult_2_{_page}_.html"
                _req = Request(_url, headers={
                    "Referer": "https://kuaixun.eastmoney.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                })
                _raw  = urlopen(_req, timeout=6).read().decode("utf-8", errors="replace")
                _raw  = re.sub(r'^var\s+ajaxResult\s*=\s*', '', _raw.strip()).rstrip(';')
                _data = json.loads(_raw)
                _items = _data.get("LivesList", []) or []
                for it in _items:
                    t = it.get("showtime", "")
                    if len(t) >= 16:
                        t = t[11:16]   # 只留 HH:MM
                    title = (it.get("title", "") or it.get("digest", "")).strip()
                    if title and title not in _seen_titles:
                        _seen_titles.add(title)
                        news.append({"title": title, "time": t, "stock": ""})
                if len(news) >= 10:
                    break
        except Exception:
            pass

        # ── 接口二：备用 — 东方财富电报快讯（wap） ──
        if not news:
            try:
                url2 = ("https://np-listapi.eastmoney.com/comm/web/getListInfo"
                        "?appid=1715678888&client=web&type=1&mTypeAndCode="
                        "&pageSize=12&pageIndex=1&fields=articleId,title,publishTime,mediaName")
                req2 = Request(url2, headers={
                    "Referer": "https://www.eastmoney.com/",
                    "User-Agent": "Mozilla/5.0"
                })
                raw2  = urlopen(req2, timeout=8).read().decode("utf-8", errors="replace")
                data2 = json.loads(raw2)
                # 可能是 data.list 或 data.LivesList 等
                d2 = data2.get("data") or {}
                if isinstance(d2, dict):
                    items2 = d2.get("list", []) or d2.get("LivesList", []) or []
                elif isinstance(d2, list):
                    items2 = d2
                else:
                    items2 = []
                for it in items2[:12]:
                    t = it.get("publishTime", "") or it.get("showtime", "")
                    if len(t) >= 16:
                        t = t[11:16]
                    title = it.get("title", "") or it.get("digest", "")
                    if title:
                        news.append({"title": title.strip(), "time": t, "stock": it.get("mediaName","")})
            except Exception:
                pass

        # ── 接口三：再备用 — 腾讯财经快讯 ──
        if not news:
            try:
                url3 = "https://finance.qq.com/ifa/index/getRoll?channel=&cate=qqfinance&limit=10&page=1"
                req3 = Request(url3, headers={
                    "Referer": "https://finance.qq.com/",
                    "User-Agent": "Mozilla/5.0"
                })
                raw3  = urlopen(req3, timeout=6).read().decode("utf-8", errors="replace")
                data3 = json.loads(raw3)
                items3 = (data3.get("data", {}) or {}).get("list", []) or []
                for it in items3[:10]:
                    t = it.get("ctime", "")
                    if t and len(str(t)) == 10:
                        t = datetime.fromtimestamp(int(t)).strftime('%H:%M')
                    news.append({
                        "title": (it.get("vt") or it.get("title") or "").strip(),
                        "time":  str(t),
                        "stock": ""
                    })
            except Exception:
                pass

        result = {"news": news}
        CACHE[cache_key] = (time.time(), result)
        self.send_json(result)

    # ─────────────────────────────────────────
    #  工具方法
    # ─────────────────────────────────────────
    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8') if length else '{}'
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)


# ─────────────────────────────────────────────
#  自动采集状态
# ─────────────────────────────────────────────
AUTO_STATUS = {
    "morning_last":   None,   # 上次采集早报时间
    "morning_date":   None,
    "afternoon_last": None,   # 上次采集盘后时间
    "afternoon_date": None,
    "weekly_last":    None,   # 上次采集周总结时间
    "weekly_week":    None,
}

# ─────────────────────────────────────────────
#  工具：判断工作日
# ─────────────────────────────────────────────
def is_weekday(d=None):
    d = d or date_cls.today()
    return d.weekday() < 5   # 0=周一…4=周五

def get_week_monday(d=None):
    """返回 d 所在周的周一日期字符串"""
    d = d or date_cls.today()
    mon = d - timedelta(days=d.weekday())
    return mon.strftime('%Y-%m-%d')

# ─────────────────────────────────────────────
#  自动抓取：早报数据
#  来源：东方财富财经新闻 + 腾讯行情外盘指数
# ─────────────────────────────────────────────
def fetch_morning_data(today_str):
    """
    抓取早报结构化数据：
    - 外围市场：道指/纳指/标普/恒生/日经/黄金（东方财富单只行情接口 secid=100.XXX/118.AUTD）
    - 昨日财经大事：东方财富7x24快讯
    接口来源已验证（2026-03）：
      美股三大指数 secid=100.DJIA / 100.SPX / 100.NDX
      恒生/日经    secid=100.HSI / 100.N225
      黄金T+D     secid=118.AUTD
    """
    now_time = datetime.now().strftime('%H:%M')

    # ── 一、外围市场（东方财富单只行情接口，稳定可用） ──
    # 格式: secid -> 展示名称
    ABROAD_SECIDS = [
        ("100.DJIA",  "道琼斯"),
        ("100.SPX",   "标普500"),
        ("100.NDX",   "纳斯达克"),
        ("100.HSI",   "恒生指数"),
        ("100.N225",  "日经225"),
        ("118.AUTD",  "黄金T+D"),
    ]
    us_markets    = []
    other_markets = []

    def _fetch_em_single(secid):
        """东方财富单只行情接口，返回 (price, change_pct) 或 ('','')"""
        url = (f"https://push2.eastmoney.com/api/qt/stock/get"
               f"?secid={secid}&ut=bd1d9ddb04089700cf9c27f6f7426281"
               f"&fltt=2&invt=2&fields=f43,f57,f58,f169,f170,f171&_=1")
        req = Request(url, headers={
            "Referer": "https://data.eastmoney.com/",
            "User-Agent": "Mozilla/5.0"
        })
        raw = urlopen(req, timeout=6).read().decode("utf-8", errors="replace")
        raw = re.sub(r'^\w+\(', '', raw).rstrip(');')
        d   = json.loads(raw).get("data") or {}
        price = str(d.get("f43", "") or "")
        pct   = str(d.get("f170", "") or "")
        chg   = str(d.get("f169", "") or "")
        return price, chg, pct

    for secid, display_name in ABROAD_SECIDS:
        try:
            price, chg, pct = _fetch_em_single(secid)
            if price and price not in ("-", ""):
                entry = {"name": display_name, "close": price, "change": chg, "change_pct": pct}
                # 道指/标普/纳指归 us_markets，其余归 other_markets
                if secid.startswith("100.D") or secid in ("100.SPX", "100.NDX"):
                    us_markets.append(entry)
                else:
                    other_markets.append(entry)
        except Exception:
            pass

    # ── 二、昨日财经大事（东方财富7x24快讯，多页合并去重） ──
    events = []
    try:
        _ev_seen = set()
        for _page in range(1, 6):
            _url = f"https://newsapi.eastmoney.com/kuaixun/v1/getlist_100_ajaxResult_2_{_page}_.html"
            _req = Request(_url, headers={
                "Referer": "https://kuaixun.eastmoney.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            _raw  = urlopen(_req, timeout=6).read().decode("utf-8", errors="replace")
            _raw  = re.sub(r'^var\s+ajaxResult\s*=\s*', '', _raw.strip()).rstrip(';')
            _data = json.loads(_raw)
            _items = _data.get("LivesList", []) or []
            for it in _items:
                title = (it.get("title", "") or it.get("digest", "") or "").strip()
                if title and title not in _ev_seen:
                    _ev_seen.add(title)
                    events.append({"event": title, "impact": "", "affected_sectors": ""})
            if len(events) >= 8:
                break
    except Exception:
        pass

    # ── 备用快讯：东方财富np-listapi ──
    if not events:
        try:
            url2 = ("https://np-listapi.eastmoney.com/comm/web/getListInfo"
                    "?appid=1715678888&client=web&type=1&mTypeAndCode="
                    "&pageSize=12&pageIndex=1&fields=articleId,title,publishTime,mediaName")
            req2 = Request(url2, headers={"Referer":"https://www.eastmoney.com/","User-Agent":"Mozilla/5.0"})
            raw2  = urlopen(req2, timeout=8).read().decode("utf-8", errors="replace")
            data2 = json.loads(raw2)
            d2 = data2.get("data") or {}
            items2 = (d2.get("list", []) if isinstance(d2, dict) else d2) or []
            for it in items2[:8]:
                title = it.get("title", "") or ""
                if title:
                    events.append({"event": title.strip(), "impact": "", "affected_sectors": ""})
        except Exception:
            pass

    # 若两项都没抓到，返回 None
    if not us_markets and not other_markets and not events:
        return None

    # ── 三、今日关注：从前一天盘后总结中提取热门板块 ──
    watch_sectors = []
    warn_sectors  = []
    focus_summary = ""
    try:
        from datetime import datetime as _dt, timedelta
        _today = _dt.strptime(today_str, "%Y-%m-%d")
        # 往前找最近一个工作日（跳过周末，最多查7天）
        for _delta in range(1, 8):
            _prev = (_today - timedelta(days=_delta)).strftime("%Y-%m-%d")
            _conn = get_conn()
            _row = _conn.execute(
                "SELECT structured_data FROM daily_reports WHERE date=? AND type='afternoon'",
                (_prev,)
            ).fetchone()
            _conn.close()
            if _row and _row["structured_data"]:
                _prev_sd = json.loads(_row["structured_data"])
                _s3 = _prev_sd.get("section3_sectors", {})
                _top = _s3.get("top_sectors", []) or []
                _bot = _s3.get("bottom_sectors", []) or []
                # 涨幅前三 → 今日关注（可能延续）
                for _s in _top[:3]:
                    _sname = _s.get("name", "")
                    _sreason = _s.get("reason", "")
                    if _sname:
                        watch_sectors.append({
                            "name":   _sname,
                            "reason": f"昨日领涨，{_sreason}" if _sreason else "昨日领涨板块，关注是否持续"
                        })
                # 跌幅前三 → 注意板块（可能超跌反弹或继续杀跌）
                for _s in _bot[:2]:
                    _sname = _s.get("name", "")
                    _sreason = _s.get("reason", "")
                    if _sname:
                        warn_sectors.append({
                            "name":   _sname,
                            "reason": f"昨日领跌，{_sreason}，警惕继续下探" if _sreason else "昨日领跌，注意补跌风险"
                        })
                # 次日计划里的 target_sectors 也纳入关注
                _s5 = _prev_sd.get("section5_plan", {})
                _targets = _s5.get("target_sectors", []) if isinstance(_s5.get("target_sectors"), list) else []
                for _t in _targets:
                    _tname = _t if isinstance(_t, str) else _t.get("name", "")
                    if _tname and not any(w["name"] == _tname for w in watch_sectors):
                        watch_sectors.append({"name": _tname, "reason": "昨日盘后次日计划重点关注"})
                # 生成摘要
                _w_names = "、".join(w["name"] for w in watch_sectors) or "—"
                _b_names = "、".join(w["name"] for w in warn_sectors)  or "—"
                focus_summary = f"参考 {_prev} 盘后数据：关注 {_w_names}；注意 {_b_names}"
                break
    except Exception:
        pass

    # ── 四、操盘建议：对持仓股做技术面+成本分析，给出操作建议 ──
    advice_lines   = []
    buy_strength   = ""
    sell_strength  = ""
    risk_note      = ""
    try:
        _conn2 = get_conn()
        _holdings = _conn2.execute(
            "SELECT code, name, market, cost, shares, current_price FROM holdings"
        ).fetchall()
        _conn2.close()

        if _holdings:
            def _market_prefix(h):
                m = (h["market"] or "").upper()
                c = (h["code"] or "")
                if m in ("SH", "1"): return "sh"
                if m in ("SZ", "0"): return "sz"
                if m == "BJ":        return "bj"
                # market='A' 按代码首位判断
                return "sh" if c.startswith("6") else "sz"

            _codes_str = ",".join([_market_prefix(h) + h["code"] for h in _holdings])
            _url_q = f"https://qt.gtimg.cn/q={_codes_str}"
            _req_q = Request(_url_q, headers={"Referer":"https://finance.qq.com/","User-Agent":"Mozilla/5.0"})
            _raw_q = urlopen(_req_q, timeout=6).read().decode("gbk", errors="replace")

            _qmap = {}
            for _line in _raw_q.strip().split("\n"):
                _line = _line.strip().rstrip(";")
                if not _line or "=" not in _line: continue
                _, _, _val = _line.partition("=")
                _val = _val.strip('"')
                _parts = _val.split("~")
                if len(_parts) < 35: continue
                _code = _parts[2]
                try:
                    _qmap[_code] = {
                        "price":   float(_parts[3]  or 0),
                        "open":    float(_parts[5]  or 0),
                        "high":    float(_parts[33] or 0),
                        "low":     float(_parts[34] or 0),
                        "pre_close": float(_parts[4] or 0),
                        "change_pct": float(_parts[32] or 0) if len(_parts)>32 else 0,
                        "vol":     int(_parts[6] or 0)   if len(_parts)>6  else 0,
                        "amount":  float(_parts[37] or 0) if len(_parts)>37 else 0,
                        "turnover": float(_parts[38] or 0) if len(_parts)>38 else 0,
                    }
                except: pass

            # ── 拉取每只持仓股的日K线（最近20日），用于计算均线和技术位 ──
            def _fetch_kline(code, market_prefix):
                """返回 (closes, highs, lows) 列表，最新在末尾；失败返回 ([], [], [])"""
                try:
                    # 东方财富 secid: 0=深圳, 1=上海
                    _em_mkt = "1" if market_prefix == "sh" else "0"
                    _kurl = (
                        f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
                        f"?secid={_em_mkt}.{code}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55"
                        f"&klt=101&fqt=1&end=20500101&lmt=22"
                    )
                    _kreq = Request(_kurl, headers={"Referer":"https://finance.eastmoney.com/","User-Agent":"Mozilla/5.0"})
                    _kraw = urlopen(_kreq, timeout=6).read().decode("utf-8", errors="replace")
                    _kdata = json.loads(_kraw)
                    _klines = _kdata.get("data", {}).get("klines", [])
                    _closes, _highs, _lows = [], [], []
                    for _kl in _klines:
                        _ps = _kl.split(",")
                        if len(_ps) < 5: continue
                        try:
                            _closes.append(float(_ps[2]))  # 收盘
                            _highs.append(float(_ps[3]))   # 最高
                            _lows.append(float(_ps[4]))    # 最低
                        except: pass
                    return _closes, _highs, _lows
                except:
                    return [], [], []

            def _calc_ma(closes, n):
                """计算最近n日均线，数据不足返回None"""
                if len(closes) < n: return None
                return round(sum(closes[-n:]) / n, 2)

            def _calc_tech_levels(code, market_prefix, price, cost):
                """
                计算技术支撑/压力位：
                - 支撑1（S1）：MA5 或近5日最低点（二者取较低者）
                - 支撑2（S2）：MA20 或近20日最低点
                - 压力1（R1）：MA10 或近10日最高点（二者取较高者）
                - 压力2（R2）：近20日最高点
                - 止损位：max(成本×92%, S2) — 不能低于技术支撑太多
                返回 dict: {s1, s2, r1, r2, stop, ma5, ma10, ma20, has_tech}
                """
                _closes, _highs, _lows = _fetch_kline(code, market_prefix)
                if not _closes or len(_closes) < 5:
                    # K线不足，回退到成本价估算
                    return {
                        "s1": round(cost * 0.95, 2) if cost else round(price * 0.95, 2),
                        "s2": round(cost * 0.92, 2) if cost else round(price * 0.92, 2),
                        "r1": round(cost * 1.08, 2) if cost else round(price * 1.08, 2),
                        "r2": round(cost * 1.15, 2) if cost else round(price * 1.15, 2),
                        "stop": round(cost * 0.92, 2) if cost else round(price * 0.92, 2),
                        "ma5": None, "ma10": None, "ma20": None, "has_tech": False,
                    }

                ma5  = _calc_ma(_closes, 5)
                ma10 = _calc_ma(_closes, 10)
                ma20 = _calc_ma(_closes, 20)

                _low5   = round(min(_lows[-5:]),  2)
                _high5  = round(max(_highs[-5:]), 2)
                _low20  = round(min(_lows[-min(20,len(_lows)):]),  2)
                _high20 = round(max(_highs[-min(20,len(_highs)):]), 2)

                # S1：MA5 和近5日低点取较低者（更贴近当前价格的支撑）
                _s1_candidates = [x for x in [ma5, _low5] if x]
                s1 = round(min(_s1_candidates), 2) if _s1_candidates else round(price * 0.95, 2)

                # S2：MA20 和近20日低点取较低者（更远的强支撑）
                _s2_candidates = [x for x in [ma20, _low20] if x]
                s2 = round(min(_s2_candidates), 2) if _s2_candidates else round(price * 0.92, 2)

                # R1：MA10 和近5日高点取较高者
                _r1_candidates = [x for x in [ma10, _high5] if x]
                r1 = round(max(_r1_candidates), 2) if _r1_candidates else round(price * 1.08, 2)

                # R2：近20日最高点
                r2 = _high20

                # 止损：成本×92% 和 S2 取较高者（避免止损位过深）
                _stop_cost = round(cost * 0.92, 2) if cost > 0 else 0
                stop = round(max(_stop_cost, s2 * 0.98), 2)  # S2略下方

                return {
                    "s1": s1, "s2": s2, "r1": r1, "r2": r2, "stop": stop,
                    "ma5": ma5, "ma10": ma10, "ma20": ma20, "has_tech": True,
                }

            buy_candidates  = []
            sell_candidates = []
            hold_candidates = []
            risk_candidates = []

            for _h in _holdings:
                _code  = _h["code"]
                _name  = _h["name"]
                _cost  = float(_h["cost"]  or 0)
                _shares = int(_h["shares"] or 0)
                _q     = _qmap.get(_code, {})
                _price = _q.get("price", 0)
                _pct   = _q.get("change_pct", 0)
                _high  = _q.get("high",  0)
                _low   = _q.get("low",   0)
                _open  = _q.get("open",  0)
                _pre   = _q.get("pre_close", 0)
                _vol   = _q.get("vol",    0)
                _turn  = _q.get("turnover", 0)
                _mprefix = _market_prefix(_h)

                # 行情无法获取则跳过
                if _price <= 0: continue

                # 涨跌情绪
                _sent = "强势" if _pct > 3 else ("弱势" if _pct < -3 else "震荡")

                # ── 未填写成本：只展示行情+技术位，提示填写 ──
                if _cost <= 0:
                    _pct_str = (f"+{_pct:.2f}%" if _pct >= 0 else f"{_pct:.2f}%")
                    _tl = _calc_tech_levels(_code, _mprefix, _price, 0)
                    _tech_str = ""
                    if _tl["has_tech"]:
                        _tech_str = (f"MA5={_tl['ma5']} MA10={_tl['ma10']} MA20={_tl['ma20']}，"
                                     f"支撑{_tl['s1']}~{_tl['s2']}元/压力{_tl['r1']}~{_tl['r2']}元。")
                    advice_lines.append(
                        f"【📋待完善】{_name}({_code})：现价{_price}元，今日{_pct_str}，{_sent}。"
                        + (_tech_str if _tech_str else "")
                        + "成本价未录入，请在持仓管理中填写成本后查看完整分析"
                    )
                    hold_candidates.append(f"{_name}({_code})待录入成本")
                    continue

                # ── 成本分析 ──
                _profit_pct = (_price - _cost) / _cost * 100  # 持仓盈亏%

                # ── 技术位计算 ──
                _tl = _calc_tech_levels(_code, _mprefix, _price, _cost)
                _support   = _tl["s1"]    # 近期支撑
                _support2  = _tl["s2"]    # 强支撑
                _pressure  = _tl["r1"]    # 近期压力
                _pressure2 = _tl["r2"]    # 强压力
                _stop_loss = _tl["stop"]  # 止损位
                _ma5, _ma10, _ma20 = _tl["ma5"], _tl["ma10"], _tl["ma20"]
                _has_tech  = _tl["has_tech"]

                # 均线趋势判断（多头/空头/震荡）
                _ma_trend = ""
                if _ma5 and _ma10 and _ma20:
                    if _ma5 > _ma10 > _ma20:
                        _ma_trend = "均线多头排列"
                    elif _ma5 < _ma10 < _ma20:
                        _ma_trend = "均线空头排列"
                    elif _price > _ma5 > _ma10:
                        _ma_trend = "短期走强"
                    elif _price < _ma5 < _ma10:
                        _ma_trend = "短期走弱"
                    else:
                        _ma_trend = "均线纠缠"

                # 价格与均线的位置关系
                _vs_ma = ""
                if _ma5 and _ma10:
                    if _price > _ma5 and _price > _ma10:
                        _vs_ma = f"现价站上MA5({_ma5})和MA10({_ma10})"
                    elif _price > _ma5 and _price < _ma10:
                        _vs_ma = f"现价{_price}在MA5({_ma5})上方、MA10({_ma10})下方"
                    elif _price < _ma5:
                        _vs_ma = f"现价{_price}跌破MA5({_ma5})"

                # 技术位描述文本
                _tech_desc = ""
                if _has_tech:
                    _ma_line = ""
                    if _ma5:  _ma_line += f"MA5={_ma5} "
                    if _ma10: _ma_line += f"MA10={_ma10} "
                    if _ma20: _ma_line += f"MA20={_ma20}"
                    _tech_desc = (
                        f"【技术位】{_ma_line.strip()}；"
                        f"支撑{_support}~{_support2}元，压力{_pressure}~{_pressure2}元，止损{_stop_loss}元"
                        + (f"；{_ma_trend}" if _ma_trend else "")
                    )
                else:
                    _tech_desc = (
                        f"【参考位】支撑{_support}元，压力{_pressure}元，止损{_stop_loss}元（基于成本估算）"
                    )

                _pct_str   = (f"+{_pct:.2f}%" if _pct >= 0 else f"{_pct:.2f}%")

                # ── 操作建议逻辑 ──
                _op = "观察"
                _reason = ""

                if _profit_pct <= -8:
                    # 浮亏超8%，硬止损
                    _op = "⚠️止损"
                    _reason = (f"浮亏 {_profit_pct:.1f}%，现价{_price}元，成本{_cost}元，今日{_pct_str}/{_sent}。"
                               f"已触及止损位({_stop_loss}元)，建议清仓止损控制风险。{_tech_desc}")
                    risk_candidates.append(f"{_name}({_code})止损{_stop_loss}元")
                elif _profit_pct <= -5:
                    # 浮亏5-8%，视盘面决定
                    _op = "⚠️减仓/止损"
                    _reason = (f"浮亏 {_profit_pct:.1f}%，现价{_price}元，成本{_cost}元，今日{_pct_str}/{_sent}。"
                               f"若继续{_sent}放量建议减仓50%；跌破{_stop_loss}元直接止损。{_tech_desc}")
                    risk_candidates.append(f"{_name}({_code})减仓观察")
                elif _profit_pct >= 15:
                    # 盈利超15%，止盈
                    _op = "💰止盈"
                    _reason = (f"浮盈 {_profit_pct:.1f}%，现价{_price}元，今日{_pct_str}/{_sent}。"
                               f"建议分批止盈（先减30-50%），剩余设移动止损。{_tech_desc}")
                    sell_candidates.append(f"{_name}({_code})+{_profit_pct:.1f}%止盈")
                elif _profit_pct >= 8:
                    # 盈利8-15%，锁利
                    _op = "📌锁利"
                    _reason = (f"浮盈 {_profit_pct:.1f}%，现价{_price}元，今日{_pct_str}/{_sent}。"
                               f"建议上移止损至成本{_cost}元保本，持有等待压力{_pressure}~{_pressure2}元。{_tech_desc}")
                    hold_candidates.append(f"{_name}({_code})+{_profit_pct:.1f}%锁利")
                elif _profit_pct >= 3:
                    # 盈利3-8%，持有
                    _op = "✅持有"
                    _reason = (f"浮盈 {_profit_pct:.1f}%，现价{_price}元，今日{_pct_str}/{_sent}。"
                               f"趋势良好可持有，跌破支撑{_support}元则止损，目标看压力{_pressure}元。{_tech_desc}")
                    hold_candidates.append(f"{_name}({_code})持有观察")
                elif _profit_pct >= -3:
                    # 微盈/平
                    if _pct > 2:
                        _op = "✅持有"
                        _reason = (f"今日{_pct_str}/{_sent}，成本{_cost}元，现价{_price}元盈亏接近平衡。"
                                   f"量价配合可持有，跌破支撑{_support}元考虑止损。{_tech_desc}")
                        hold_candidates.append(f"{_name}({_code})盘整持有")
                    elif _pct < -2:
                        _op = "⚠️注意"
                        _reason = (f"今日{_pct_str}/{_sent}，成本{_cost}元，现价{_price}元。"
                                   f"跌破止损位{_stop_loss}元须止损，支撑位参考{_support}元。{_tech_desc}")
                        risk_candidates.append(f"{_name}({_code})注意止损线")
                    else:
                        _op = "👀观察"
                        _reason = (f"现价{_price}元接近成本{_cost}元，今日{_pct_str}/{_sent}。"
                                   f"等待方向明确，支撑{_support}元/压力{_pressure}元。{_tech_desc}")
                        hold_candidates.append(f"{_name}({_code})待突破")
                elif _profit_pct >= -5:
                    # 浮亏3-5%，可考虑补仓
                    if _pct < -2:
                        _op = "⚠️观察/补仓"
                        _reason = (f"浮亏{abs(_profit_pct):.1f}%，今日{_pct_str}/{_sent}，现价{_price}元，成本{_cost}元。"
                                   f"若止跌企稳在支撑{_support}元附近可小仓补仓摊薄；继续破低则止损{_stop_loss}元。{_tech_desc}")
                        buy_candidates.append(f"{_name}({_code})低吸补仓支撑{_support}元")
                    else:
                        _op = "👀观察"
                        _reason = (f"浮亏{abs(_profit_pct):.1f}%，今日{_pct_str}/{_sent}，暂时持有，"
                                   f"关注是否在支撑{_support}元附近企稳，止损位{_stop_loss}元。{_tech_desc}")
                        hold_candidates.append(f"{_name}({_code})观察企稳")

                advice_lines.append(f"【{_op}】{_name}({_code})：{_reason}")

            # 汇总买卖风险
            if buy_candidates:
                buy_strength = "可关注补仓：" + "；".join(buy_candidates)
            if sell_candidates:
                sell_strength = "建议止盈：" + "；".join(sell_candidates)
            if risk_candidates:
                risk_note = "风险提示：" + "；".join(risk_candidates)
    except Exception:
        pass

    buy_advice  = "\n".join(advice_lines) if advice_lines else ""

    sd = {
        "section1_overseas": {
            "us_markets":    us_markets    or [{"name":"道琼斯","close":"","change":"","change_pct":""},
                                               {"name":"纳斯达克","close":"","change":"","change_pct":""},
                                               {"name":"标普500","close":"","change":"","change_pct":""}],
            "other_markets": other_markets or [{"name":"恒生指数","close":"","change":"","change_pct":""},
                                               {"name":"黄金","close":"","change":"","change_pct":""},
                                               {"name":"原油","close":"","change":"","change_pct":""}],
            "summary": "（自动采集，请补充外盘影响判断）"
        },
        "section2_events": {
            "items":   events,
            "summary": "（自动采集，请补充综合分析）"
        },
        "section3_focus": {
            "watch_sectors": watch_sectors,
            "warn_sectors":  warn_sectors,
            "summary":       focus_summary or "（基于昨日盘后数据自动生成，可手动调整）"
        },
        "section4_advice": {
            "buy_strength":  buy_strength,
            "buy_advice":    buy_advice,
            "sell_strength": sell_strength,
            "sell_advice":   "",
            "risk_note":     risk_note
        },
        "section5_plan":   {"items": [], "pre_open_check": ""},
    }

    us_str = "  ".join([f"{m['name']} {m['change_pct']}%" for m in us_markets if m.get('change_pct')])
    watch_str = "、".join(w["name"] for w in watch_sectors) if watch_sectors else ""
    content = f"外围：{us_str}\n"
    if watch_str: content += f"关注：{watch_str}\n"
    if buy_advice: content += f"操作：见持仓分析\n"
    content += f"自动采集于 {now_time}"

    return {
        "title":    f"{today_str} 早盘报道（自动）",
        "content":  content,
        "sentiment": "neutral",
        "time":      now_time,
        "structured_data": sd
    }


# ─────────────────────────────────────────────
#  自动抓取：盘后总结数据
#  来源：腾讯行情A股指数 + 东方财富板块资金流向
# ─────────────────────────────────────────────
def fetch_afternoon_data(today_str):
    now_time = datetime.now().strftime('%H:%M')

    # ── 一、A股指数 ──
    indices = []
    try:
        codes = "sh000001,sz399001,sz399006,bj899050"
        names = {"000001":"上证指数","399001":"深证成指","399006":"创业板指","899050":"北证50"}
        url = f"https://qt.gtimg.cn/q={codes}"
        req = Request(url, headers={"Referer":"https://finance.qq.com/","User-Agent":"Mozilla/5.0"})
        raw = urlopen(req, timeout=6).read().decode("gbk", errors="replace")
        for line in raw.strip().split("\n"):
            line = line.strip().rstrip(";")
            if not line or "=" not in line: continue
            _, _, val = line.partition("=")
            val   = val.strip('"')
            parts = val.split("~")
            if len(parts) < 33: continue
            try:
                code = parts[2]
                name = names.get(code, parts[1])
                indices.append({
                    "name":       name,
                    "close":      parts[3],
                    "change":     parts[31] if len(parts)>31 else '',
                    "change_pct": parts[32] if len(parts)>32 else '',
                    "vol":        parts[6]  if len(parts)>6  else '',
                })
            except: pass
    except Exception:
        pass

    # ── 二、大盘成交量 & 涨跌家数（沪深市场合计） ──
    volume_str = ""
    advance_str = ""
    decline_str = ""
    trend_str = ""
    try:
        # 沪深两市成交合计：东方财富大盘资金流向接口
        url_mkt = ("https://push2.eastmoney.com/api/qt/stock/get"
                   "?ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2"
                   "&fields=f43,f57,f58,f169,f170,f171,f86,f84,f85"
                   "&secid=1.000001&_=1")
        req_mkt = Request(url_mkt, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_mkt = urlopen(req_mkt, timeout=6).read().decode("utf-8", errors="replace")
        raw_mkt = re.sub(r'^\w+\(', '', raw_mkt).rstrip(');')
        d_mkt = json.loads(raw_mkt).get("data", {}) or {}
    except Exception:
        d_mkt = {}

    # 用指数成交量估算
    if indices:
        # 上证成交量 parts[6] 单位手，1手=100股，粗估
        sh_vol = next((i.get('vol','') for i in indices if '上证' in i.get('name','')), '')
        if sh_vol:
            try:
                v = float(sh_vol) / 10000  # 转为亿手估算
                volume_str = f"约 {v:.0f} 亿"
            except Exception:
                volume_str = sh_vol

    # 涨跌家数：东方财富行情统计
    try:
        url_updown = ("https://push2.eastmoney.com/api/qt/stock/get"
                      "?secid=1.000001&ut=bd1d9ddb04089700cf9c27f6f7426281"
                      "&fltt=2&invt=2&fields=f3,f170,f171,f186,f187,f188,f189&_=1")
        req_ud = Request(url_updown, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_ud = urlopen(req_ud, timeout=5).read().decode("utf-8", errors="replace")
        raw_ud = re.sub(r'^\w+\(', '', raw_ud).rstrip(');')
        d_ud = json.loads(raw_ud).get("data", {}) or {}
        # f186=上涨家数,f187=下跌家数 (不一定存在，视接口而定)
        advance_str = str(d_ud.get("f186","")) if d_ud.get("f186") else ""
        decline_str = str(d_ud.get("f187","")) if d_ud.get("f187") else ""
    except Exception:
        pass

    # 综合指数涨跌判断趋势
    sh_idx = next((i for i in indices if '上证' in i.get('name','')), None)
    if sh_idx:
        try:
            pct = float(sh_idx.get('change_pct', 0) or 0)
            if pct > 1:      trend_str = "强势上涨"
            elif pct > 0:    trend_str = "小幅上涨"
            elif pct > -1:   trend_str = "小幅下跌"
            else:            trend_str = "明显下跌"
        except Exception:
            trend_str = ""

    # ── 三、板块涨幅前三 & 跌幅前三（东方财富行业板块，带更多分析字段） ──
    top_sectors    = []   # 涨幅前三
    bottom_sectors = []   # 跌幅前三
    try:
        # 涨幅前三（po=1 降序排）—— 多取字段：f3涨跌幅, f62主力净流入, f115市盈率, f9换手率, f104涨停数, f3000涨幅描述
        url_up = ("https://push2.eastmoney.com/api/qt/clist/get"
                  "?cb=&pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                  "&fltt=2&invt=2&fid=f3&fs=m:90+t:2"
                  "&fields=f12,f14,f3,f62,f9,f104,f105&_=1")
        req_up = Request(url_up, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_up = urlopen(req_up, timeout=8).read().decode("utf-8", errors="replace")
        raw_up = re.sub(r'^\w+\(', '', raw_up).rstrip(');')
        items_up = json.loads(raw_up).get("data", {}).get("diff", []) or []
        for it in items_up[:3]:
            chg      = it.get("f3", 0) or 0
            inflow   = it.get("f62", 0) or 0
            turnover = it.get("f9", 0) or 0
            up_cnt   = it.get("f104", 0) or 0
            dn_cnt   = it.get("f105", 0) or 0
            # 生成自然语言分析原因
            reason_parts = [f"涨幅 +{chg:.2f}%"]
            if inflow > 0:
                reason_parts.append(f"主力净流入 {inflow/1e8:.2f}亿，资金持续买入")
            elif inflow < 0:
                reason_parts.append(f"主力净流出 {abs(inflow)/1e8:.2f}亿，靠散户推动")
            if turnover:
                reason_parts.append(f"换手 {turnover:.1f}%")
            if up_cnt:
                reason_parts.append(f"板块内{up_cnt}只上涨/{dn_cnt}只下跌")
            top_sectors.append({
                "name":   it.get("f14", ""),
                "reason": "，".join(reason_parts),
                "driver":      "",
                "continuity":  ""
            })
    except Exception:
        pass

    try:
        # 跌幅前三（po=0 升序排，即跌幅最大在前）
        url_dn = ("https://push2.eastmoney.com/api/qt/clist/get"
                  "?cb=&pn=1&pz=5&po=0&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                  "&fltt=2&invt=2&fid=f3&fs=m:90+t:2"
                  "&fields=f12,f14,f3,f62,f9,f104,f105&_=1")
        req_dn = Request(url_dn, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_dn = urlopen(req_dn, timeout=8).read().decode("utf-8", errors="replace")
        raw_dn = re.sub(r'^\w+\(', '', raw_dn).rstrip(');')
        items_dn = json.loads(raw_dn).get("data", {}).get("diff", []) or []
        for it in items_dn[:3]:
            chg      = it.get("f3", 0) or 0
            outflow  = it.get("f62", 0) or 0
            turnover = it.get("f9", 0) or 0
            up_cnt   = it.get("f104", 0) or 0
            dn_cnt   = it.get("f105", 0) or 0
            reason_parts = [f"跌幅 {chg:.2f}%"]
            if outflow < 0:
                reason_parts.append(f"主力净流出 {abs(outflow)/1e8:.2f}亿，资金持续撤离")
            elif outflow > 0:
                reason_parts.append(f"主力逆势流入 {outflow/1e8:.2f}亿，或有抄底迹象")
            if turnover:
                reason_parts.append(f"换手 {turnover:.1f}%")
            if dn_cnt:
                reason_parts.append(f"板块内{up_cnt}只上涨/{dn_cnt}只下跌")
            bottom_sectors.append({
                "name":   it.get("f14", ""),
                "reason": "，".join(reason_parts),
                "driver":      "",
                "continuity":  ""
            })
    except Exception:
        pass

    # ── 四、关注个股回顾（从持仓表读取，拉取当日实时行情，构建分析框架） ──
    section4_stocks = []
    try:
        conn4 = get_conn()
        holdings = conn4.execute("SELECT code, name, market FROM holdings").fetchall()
        conn4.close()
        if holdings:
            codes_str = ",".join([
                ("sh" if h["market"] in ("SH","sh","1") else "sz") + h["code"]
                for h in holdings
            ])
            url_q = f"https://qt.gtimg.cn/q={codes_str}"
            req_q = Request(url_q, headers={"Referer":"https://finance.qq.com/","User-Agent":"Mozilla/5.0"})
            raw_q = urlopen(req_q, timeout=6).read().decode("gbk", errors="replace")
            quote_map = {}
            for line in raw_q.strip().split("\n"):
                line = line.strip().rstrip(";")
                if not line or "=" not in line: continue
                _, _, val = line.partition("=")
                val = val.strip('"')
                parts = val.split("~")
                if len(parts) < 33: continue
                code = parts[2]
                try:
                    quote_map[code] = {
                        "price":      parts[3],
                        "change_pct": parts[32] if len(parts)>32 else '',
                        "vol":        parts[6]  if len(parts)>6  else '',
                        "open":       parts[5]  if len(parts)>5  else '',
                        "high":       parts[33] if len(parts)>33 else '',
                        "low":        parts[34] if len(parts)>34 else '',
                    }
                except: pass

            for h in holdings:
                code = h["code"]
                q    = quote_map.get(code, {})
                pct  = float(q.get("change_pct", 0) or 0)
                pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
                price   = q.get("price","—")
                # 自动生成分析框架（用户可在编辑器里补充）
                minute_ana = f"今日涨跌幅 {pct_str}，现价 {price}元；请结合分时图分析成交量分布，判断主力行为（吸筹/出货/洗盘）"
                kline_ana  = f"开 {q.get('open','—')} 高 {q.get('high','—')} 低 {q.get('low','—')} 收 {price}；请结合前期K线判断形态（反转/持续）"
                news_ana   = f"请补充今日{h['name']}相关消息面（公告/新闻），分析对股价的影响"
                section4_stocks.append({
                    "code":            code,
                    "name":            h["name"],
                    "minute_analysis": minute_ana,
                    "kline_analysis":  kline_ana,
                    "news_analysis":   news_ana,
                })
    except Exception:
        pass

    if not indices and not top_sectors:
        return None

    # 生成简要摘要
    idx_str = "  ".join([f"{i['name']} {i['change_pct']}%" for i in indices if i.get('change_pct')])
    top_str = "、".join([s['name'] for s in top_sectors]) or "—"
    bot_str = "、".join([s['name'] for s in bottom_sectors]) or "—"
    content = f"指数：{idx_str}\n领涨：{top_str}  领跌：{bot_str}\n自动采集于 {now_time}，请在编辑器中补充详细分析。"

    sd = {
        "section1_indices": indices,
        "section2_market": {
            "trend":          trend_str,
            "trend_detail":   f"自动采集于 {now_time}",
            "fund_north":     "",
            "fund_main":      "",
            "fund_detail":    "",
            "sentiment_level": "",
            "volume":         volume_str,
            "advance":        advance_str,
            "decline":        decline_str,
            "sentiment_detail": ""
        },
        "section3_sectors": {
            "top_sectors":    top_sectors,
            "bottom_sectors": bottom_sectors,
            "linkage": "", "linkage_detail": "", "rotation": ""
        },
        "section4_stocks": section4_stocks,
        "section5_plan": {
            "target_sectors": "", "buy_plan": "", "sell_plan": "", "risk_warning": ""
        },
    }

    return {
        "title":    f"{today_str} 盘后总结（自动）",
        "content":  content,
        "sentiment": "neutral",
        "time":      now_time,
        "structured_data": sd
    }


# ─────────────────────────────────────────────
#  自动抓取：周总结数据
#  来源：A股指数 + 东方财富板块周涨跌 + 潜力股筛选
# ─────────────────────────────────────────────
def fetch_weekly_data(week_str):
    now_time = datetime.now().strftime('%H:%M')

    # ── 一、A 股指数（当前行情代表本周末数据） ──
    indices = []
    try:
        codes = "sh000001,sz399001,sz399006,bj899050"
        names = {"000001":"上证指数","399001":"深证成指","399006":"创业板指","899050":"北证50"}
        url = f"https://qt.gtimg.cn/q={codes}"
        req = Request(url, headers={"Referer":"https://finance.qq.com/","User-Agent":"Mozilla/5.0"})
        raw = urlopen(req, timeout=6).read().decode("gbk", errors="replace")
        for line in raw.strip().split("\n"):
            line = line.strip().rstrip(";")
            if not line or "=" not in line: continue
            _, _, val = line.partition("=")
            val   = val.strip('"')
            parts = val.split("~")
            if len(parts) < 33: continue
            try:
                code = parts[2]
                indices.append({
                    "name":       names.get(code, parts[1]),
                    "close":      parts[3],
                    "change":     parts[31] if len(parts)>31 else '',
                    "change_pct": parts[32] if len(parts)>32 else '',
                    "vol":        parts[6]  if len(parts)>6  else '',
                })
            except: pass
    except Exception:
        pass

    # ── 二、本周大盘趋势 & 成交量估算 ──
    week_trend = ""
    week_volume = ""
    sh_idx = next((i for i in indices if '上证' in i.get('name','')), None)
    if sh_idx:
        try:
            pct = float(sh_idx.get('change_pct', 0) or 0)
            if pct > 2:      week_trend = "本周强势上涨"
            elif pct > 0.5:  week_trend = "本周小幅上涨"
            elif pct > -0.5: week_trend = "本周基本持平"
            elif pct > -2:   week_trend = "本周小幅下跌"
            else:             week_trend = "本周明显下跌"
            vol = sh_idx.get('vol','')
            if vol:
                try:
                    v = float(vol) / 10000
                    week_volume = f"约 {v:.0f} 亿"
                except: pass
        except: pass

    # ── 三、本周板块涨幅前三 & 跌幅前三 ──
    top_sectors    = []   # 涨幅前三
    bottom_sectors = []   # 跌幅前三
    try:
        url_up = ("https://push2.eastmoney.com/api/qt/clist/get"
                  "?cb=&pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                  "&fltt=2&invt=2&fid=f3&fs=m:90+t:2"
                  "&fields=f12,f14,f3,f62,f9,f104,f105&_=1")
        req_up = Request(url_up, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_up = urlopen(req_up, timeout=8).read().decode("utf-8", errors="replace")
        raw_up = re.sub(r'^\w+\(', '', raw_up).rstrip(');')
        items_up = json.loads(raw_up).get("data", {}).get("diff", []) or []
        for it in items_up[:3]:
            chg      = it.get("f3", 0) or 0
            inflow   = it.get("f62", 0) or 0
            turnover = it.get("f9", 0) or 0
            up_cnt   = it.get("f104", 0) or 0
            dn_cnt   = it.get("f105", 0) or 0
            reason_parts = [f"本周涨幅 +{chg:.2f}%"]
            if inflow > 0:
                reason_parts.append(f"主力净流入 {inflow/1e8:.2f}亿，资金持续关注")
            elif inflow < 0:
                reason_parts.append(f"主力净流出 {abs(inflow)/1e8:.2f}亿，靠情绪驱动")
            if up_cnt:
                reason_parts.append(f"板块内{up_cnt}只上涨/{dn_cnt}只下跌")
            top_sectors.append({
                "name":       it.get("f14", ""),
                "reason":     "，".join(reason_parts),
                "driver":     "",
                "continuity": ""
            })
    except Exception:
        pass

    try:
        url_dn = ("https://push2.eastmoney.com/api/qt/clist/get"
                  "?cb=&pn=1&pz=5&po=0&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                  "&fltt=2&invt=2&fid=f3&fs=m:90+t:2"
                  "&fields=f12,f14,f3,f62,f9,f104,f105&_=1")
        req_dn = Request(url_dn, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_dn = urlopen(req_dn, timeout=8).read().decode("utf-8", errors="replace")
        raw_dn = re.sub(r'^\w+\(', '', raw_dn).rstrip(');')
        items_dn = json.loads(raw_dn).get("data", {}).get("diff", []) or []
        for it in items_dn[:3]:
            chg      = it.get("f3", 0) or 0
            outflow  = it.get("f62", 0) or 0
            turnover = it.get("f9", 0) or 0
            up_cnt   = it.get("f104", 0) or 0
            dn_cnt   = it.get("f105", 0) or 0
            reason_parts = [f"本周跌幅 {chg:.2f}%"]
            if outflow < 0:
                reason_parts.append(f"主力净流出 {abs(outflow)/1e8:.2f}亿，资金持续撤离")
            elif outflow > 0:
                reason_parts.append(f"主力逆势流入 {outflow/1e8:.2f}亿")
            if dn_cnt:
                reason_parts.append(f"板块内{up_cnt}只上涨/{dn_cnt}只下跌")
            bottom_sectors.append({
                "name":       it.get("f14", ""),
                "reason":     "，".join(reason_parts),
                "driver":     "",
                "continuity": ""
            })
    except Exception:
        pass

    # ── 四、本周北向资金（东方财富北向数据） ──
    fund_north = ""
    try:
        url_north = ("https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
                     "?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55,f56"
                     "&ut=bd1d9ddb04089700cf9c27f6f7426281&cb=&_=1")
        req_north = Request(url_north, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_north = urlopen(req_north, timeout=6).read().decode("utf-8", errors="replace")
        raw_north = re.sub(r'^\w+\(', '', raw_north).rstrip(');')
        d_north = json.loads(raw_north).get("data", {}) or {}
        # s2n = 南向，n2s = 北向
        north_val = d_north.get("s2nZF", None)
        if north_val is not None:
            sign = "+" if float(north_val) >= 0 else ""
            fund_north = f"{sign}{float(north_val)/1e8:.2f}亿"
    except Exception:
        pass

    # ── 五、主力资金净流入（沪深两市合计，周度估算） ──
    fund_main = ""
    try:
        url_main = ("https://push2.eastmoney.com/api/qt/stock/get"
                    "?secid=1.000001&ut=bd1d9ddb04089700cf9c27f6f7426281"
                    "&fltt=2&invt=2&fields=f43,f62,f64,f65,f66,f69&_=1")
        req_main = Request(url_main, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw_main = urlopen(req_main, timeout=5).read().decode("utf-8", errors="replace")
        raw_main = re.sub(r'^\w+\(', '', raw_main).rstrip(');')
        d_main = json.loads(raw_main).get("data", {}) or {}
        mf = d_main.get("f62", None)
        if mf is not None and mf != "-":
            try:
                mf_val = float(mf)
                sign = "+" if mf_val >= 0 else ""
                fund_main = f"{sign}{mf_val/1e8:.2f}亿"
            except: pass
    except Exception:
        pass

    # ── 六、潜力股筛选：价格≤20元、主力未出逃、有上涨动能 ──
    recommend_stocks = _pick_weekly_stocks()

    # ── 七、关注个股本周回顾（从持仓表读取，拉取当前行情，构建分析框架） ──
    section4_stocks = []
    try:
        conn4 = get_conn()
        holdings4 = conn4.execute("SELECT code, name, market FROM holdings").fetchall()
        conn4.close()
        if holdings4:
            codes_str = ",".join([
                ("sh" if h["market"] in ("SH","sh","1") else "sz") + h["code"]
                for h in holdings4
            ])
            url_q = f"https://qt.gtimg.cn/q={codes_str}"
            req_q = Request(url_q, headers={"Referer":"https://finance.qq.com/","User-Agent":"Mozilla/5.0"})
            raw_q = urlopen(req_q, timeout=6).read().decode("gbk", errors="replace")
            quote_map = {}
            for line in raw_q.strip().split("\n"):
                line = line.strip().rstrip(";")
                if not line or "=" not in line: continue
                _, _, val = line.partition("=")
                val = val.strip('"')
                parts = val.split("~")
                if len(parts) < 33: continue
                code = parts[2]
                try:
                    quote_map[code] = {
                        "price":      parts[3],
                        "change_pct": parts[32] if len(parts)>32 else '',
                    }
                except: pass
            for h in holdings4:
                code = h["code"]
                q    = quote_map.get(code, {})
                pct  = float(q.get("change_pct", 0) or 0)
                pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
                price   = q.get("price","—")
                section4_stocks.append({
                    "code":            code,
                    "name":            h["name"],
                    "minute_analysis": f"本周收盘 {price}元，周涨跌幅约 {pct_str}；请结合分时图分析本周成交量分布，判断主力行为",
                    "kline_analysis":  f"请结合本周K线判断是否形成关键形态（反转/持续），前期支撑压力位评估",
                    "news_analysis":   f"请补充本周{h['name']}相关重要消息/公告，分析对后续走势的影响",
                })
    except Exception:
        pass

    if not indices and not top_sectors:
        return None

    idx_str = "  ".join([f"{i['name']} {i['change_pct']}%" for i in indices if i.get('change_pct')])
    top_str = "、".join([s['name'] for s in top_sectors]) or "—"
    bot_str = "、".join([s['name'] for s in bottom_sectors]) or "—"
    rec_str = "、".join([s['name'] for s in recommend_stocks]) if recommend_stocks else "待筛选"
    content = (f"本周指数：{idx_str}\n"
               f"领涨：{top_str}  领跌：{bot_str}\n"
               f"下周潜力股：{rec_str}\n"
               f"自动采集于 {now_time}，请在编辑器中补充详细分析。")

    sd = {
        "section1_indices": indices,
        "section2_market": {
            "trend":           week_trend,
            "trend_detail":    f"自动采集于 {now_time}",
            "fund_north":      fund_north,
            "fund_main":       fund_main,
            "fund_detail":     "",
            "sentiment_level": "",
            "volume":          week_volume,
            "sentiment_score": "",
            "sentiment_detail": ""
        },
        "section3_sectors": {
            "top_sectors":    top_sectors,
            "bottom_sectors": bottom_sectors,
            "linkage": "", "rotation": ""
        },
        "section4_stocks": section4_stocks,
        "section5_plan": {
            "target_sectors": top_str if top_str != "—" else "",
            "buy_plan": "", "sell_plan": "", "risk_warning": ""
        },
        "section6_recommend": recommend_stocks,
    }

    return {
        "title":    f"{week_str} 周总结（自动）",
        "content":  content,
        "sentiment": "bullish" if week_trend.endswith("上涨") else "bearish" if week_trend.endswith("下跌") else "neutral",
        "time":      now_time,
        "structured_data": sd
    }


# ─────────────────────────────────────────────
#  潜力股筛选
#  策略：价格 < 20元 + 主力净流入 > 0 + 非ST + 热门板块加权
#  热门板块：东方财富行业板块，涨幅和资金双优前5板块成分股加分
# ─────────────────────────────────────────────
def _pick_weekly_stocks():
    """
    筛选下周潜力股（≤5只）
    核心条件：价格 < 20元 + 主力净流入 > 0 + 非ST
    加分项：属于当日涨幅/资金双优热门板块的股票评分 ×1.5
    reason 中展示：技术面 / 资金面 / 热门板块（如有）
    """

    # 安全转浮点（字段可能是 '-' 字符串或 None）
    def _f(v):
        try: return float(v)
        except: return 0.0

    # ── Step 1: 拉取热门板块（涨幅+主力净流入综合排序前5），获取板块代码集合 ──
    hot_sector_codes = set()   # 板块代码集合，如 BK0451
    hot_sector_names = {}      # code -> name，用于填写推荐理由
    try:
        # 东方财富行业板块，按主力净流入降序取前20，再按涨幅二次排序取前5热门
        sec_url = ("https://push2.eastmoney.com/api/qt/clist/get"
                   "?cb=&pn=1&pz=30&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                   "&fltt=2&invt=2&fid=f62&fs=m:90+t:2"
                   "&fields=f12,f14,f3,f62&_=1")
        sec_req = Request(sec_url, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        sec_raw = urlopen(sec_req, timeout=8).read().decode("utf-8", errors="replace")
        sec_raw = re.sub(r'^\w+\(', '', sec_raw).rstrip(');')
        sec_items = json.loads(sec_raw).get("data", {}).get("diff", []) or []

        # 双因子排序：涨幅分（chg>0 ? 1:0）+ 净流入分（>0 ? 1:0），优先取两者均正的板块
        def _sec_score(s):
            chg    = _f(s.get("f3",  0))
            inflow = _f(s.get("f62", 0))
            return (1 if inflow > 0 else 0) * 2 + (1 if chg > 0 else 0)

        sec_items_sorted = sorted(sec_items, key=_sec_score, reverse=True)
        for s in sec_items_sorted[:5]:
            sc = s.get("f12", "")
            sn = s.get("f14", "")
            if sc and sn:
                hot_sector_codes.add(sc)
                hot_sector_names[sc] = sn
    except Exception:
        pass  # 板块拉取失败不影响主流程

    # ── Step 2: 拉取热门板块成分股代码集合（每个板块取前50成分） ──
    hot_stock_codes = {}   # stock_code -> sector_name
    if hot_sector_codes:
        for sc in hot_sector_codes:
            try:
                mem_url = (f"https://push2.eastmoney.com/api/qt/clist/get"
                           f"?cb=&pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                           f"&fltt=2&invt=2&fid=f3&fs=b:{sc}+f:!50"
                           f"&fields=f12,f14,f3&_=1")
                mem_req = Request(mem_url, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
                mem_raw = urlopen(mem_req, timeout=6).read().decode("utf-8", errors="replace")
                mem_raw = re.sub(r'^\w+\(', '', mem_raw).rstrip(');')
                mem_items = json.loads(mem_raw).get("data", {}).get("diff", []) or []
                for m in mem_items:
                    stk_code = m.get("f12", "")
                    if stk_code and stk_code not in hot_stock_codes:
                        hot_stock_codes[stk_code] = hot_sector_names.get(sc, "")
            except Exception:
                continue

    # ── Step 3: 拉取沪深全市场，按主力净流入降序，三条件过滤 ──
    candidates = []
    try:
        url = ("https://push2.eastmoney.com/api/qt/clist/get"
               "?cb=&pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
               "&fltt=2&invt=2&fid=f62&fs=m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23"
               "&fields=f2,f3,f12,f14,f62,f184,f116&_=1")
        req = Request(url, headers={"Referer":"https://data.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        raw = urlopen(req, timeout=10).read().decode("utf-8", errors="replace")
        raw = re.sub(r'^\w+\(', '', raw).rstrip(');')
        items = json.loads(raw).get("data", {}).get("diff", []) or []

        for it in items:
            price    = _f(it.get("f2",  0))   # 现价
            chg      = _f(it.get("f3",  0))   # 涨跌幅%
            inflow   = _f(it.get("f62", 0))   # 主力净流入（元）
            turnover = _f(it.get("f184",0))   # 换手率%
            mktcap   = _f(it.get("f116",0))   # 总市值（元）
            name     = it.get("f14", "")
            code     = it.get("f12", "")

            # 三项核心过滤：价格、资金、ST
            if not code or not name:               continue
            if price <= 0 or price >= 20:          continue   # 价格 0~20 元（不含20）
            if inflow <= 0:                        continue   # 主力净流入 > 0
            if "ST" in name:                       continue   # 排除ST

            # 基础评分：净流入/市值
            base_score = inflow / max(mktcap, 1e8)
            # 热门板块加权：属于热门板块则评分 ×1.5
            in_hot = code in hot_stock_codes
            score  = base_score * 1.5 if in_hot else base_score

            candidates.append({
                "code":       code,
                "name":       name,
                "price":      round(price, 2),
                "chg":        round(chg, 2),
                "inflow":     round(inflow / 1e8, 2),
                "turnover":   round(turnover, 2),
                "score":      score,
                "sector":     hot_stock_codes.get(code, ""),  # 所属热门板块名
            })
            if len(candidates) >= 80: break

        # ── Step 4: 按评分降序排，取前5 ──
        candidates.sort(key=lambda x: x['score'], reverse=True)
        result = []
        for c in candidates[:5]:
            chg_str  = f"+{c['chg']:.2f}%" if c['chg'] >= 0 else f"{c['chg']:.2f}%"
            # 技术面描述
            tech_ma  = "价格低位，具有弹性空间" if c['price'] < 10 else "中低价位，风险可控"
            tech_vol  = f"换手 {c['turnover']:.1f}%，" + ("活跃放量" if c['turnover'] > 3 else "温和成交")
            tech_str  = f"现价 {c['price']:.2f}元，今日 {chg_str}，{tech_vol}，{tech_ma}"
            # 资金面描述
            cap_str   = f"主力净流入 {c['inflow']:.2f}亿元，资金持续关注"
            # 热门板块描述（如有）
            sector_str = f"【热门板块】{c['sector']}板块今日强势，属于热点赛道 | " if c['sector'] else ""
            # 操盘建议：根据价格区间、换手、资金强度生成差异化建议
            if c['price'] < 6:
                entry_hint = f"低价位（{c['price']:.2f}元），可小仓试探性建仓"
            elif c['price'] < 12:
                entry_hint = f"现价 {c['price']:.2f}元附近可分批介入"
            else:
                entry_hint = f"现价 {c['price']:.2f}元，逢回调至支撑位可考虑入场"

            if c['inflow'] >= 2:
                fund_hint = f"主力今日净流入 {c['inflow']:.2f}亿，资金明显关注，可适当跟进"
            elif c['inflow'] >= 0.5:
                fund_hint = f"主力净流入 {c['inflow']:.2f}亿，关注量价配合情况"
            else:
                fund_hint = f"资金小幅流入，轻仓观察为主"

            if c['sector']:
                sector_hint = f"；{c['sector']}板块处于热点，若板块持续则可加仓"
            else:
                sector_hint = ""

            advice = f"{entry_hint}，{fund_hint}{sector_hint}。止损参考近期低点。"

            reason = (f"{sector_str}"
                      f"【技术面】{tech_str} | "
                      f"【资金面】{cap_str}")
            result.append({
                "code":   c['code'],
                "name":   c['name'],
                "market": "A",
                "price":  c['price'],
                "chg":    c['chg'],
                "inflow": c['inflow'],
                "sector": c['sector'],
                "reason": reason,
                "advice": advice
            })
        return result
    except Exception:
        return []


# ─────────────────────────────────────────────
#  DB 写入辅助（供自动采集用，不覆盖已有手动内容的核心字段）
# ─────────────────────────────────────────────
def save_daily_auto(date_str, rtype, data):
    conn = get_conn()
    sd_json = json.dumps(data.get('structured_data', {}), ensure_ascii=False)
    conn.execute("""
        INSERT INTO daily_reports (date, type, title, content, sentiment, time, structured_data, updated_at)
        VALUES (?,?,?,?,?,?,?,datetime('now','localtime'))
        ON CONFLICT(date, type) DO UPDATE SET
            title = CASE WHEN title='' THEN excluded.title ELSE title END,
            content = CASE WHEN content='' THEN excluded.content ELSE content END,
            structured_data = CASE WHEN structured_data='{}' OR structured_data='' THEN excluded.structured_data ELSE structured_data END,
            updated_at = excluded.updated_at
    """, (date_str, rtype, data.get('title',''), data.get('content',''),
          data.get('sentiment','neutral'), data.get('time',''), sd_json))
    conn.commit()
    conn.close()

def save_weekly_auto(week_str, data):
    conn = get_conn()
    sd     = data.get('structured_data', {})
    sd_json = json.dumps(sd, ensure_ascii=False)
    conn.execute("""
        INSERT INTO weekly_summary (week, title, content, sentiment, time, structured_data, updated_at)
        VALUES (?,?,?,?,?,?,datetime('now','localtime'))
        ON CONFLICT(week) DO UPDATE SET
            title = CASE WHEN title='' THEN excluded.title ELSE title END,
            content = CASE WHEN content='' THEN excluded.content ELSE content END,
            structured_data = CASE WHEN structured_data='{}' OR structured_data='' THEN excluded.structured_data ELSE structured_data END,
            updated_at = excluded.updated_at
    """, (week_str, data.get('title',''), data.get('content',''),
          data.get('sentiment','neutral'), data.get('time',''), sd_json))

    # 如果有自动筛选的潜力股，且本周 recommend 表为空，则写入
    recs = sd.get('section6_recommend', [])
    if recs:
        existing = conn.execute(
            "SELECT COUNT(*) FROM weekly_recommend WHERE week=?", (week_str,)
        ).fetchone()[0]
        if existing == 0:
            for i, s in enumerate(recs[:5]):
                conn.execute("""
                    INSERT INTO weekly_recommend (week, rank, code, name, market, reason, advice)
                    VALUES (?,?,?,?,?,?,?)
                """, (week_str, i, s.get('code',''), s.get('name',''),
                      s.get('market','A'), s.get('reason',''), s.get('advice','')))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  腾讯行情解析
# ─────────────────────────────────────────────
def parse_tencent(raw):
    result = {}
    for line in raw.strip().split("\n"):
        line = line.strip().rstrip(";")
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val   = val.strip('"')
        parts = val.split("~")
        if len(parts) < 36:
            continue
        code = parts[2]
        try:
            price       = float(parts[3])  if parts[3]  else 0
            close_prev  = float(parts[4])  if parts[4]  else 0
            open_p      = float(parts[5])  if parts[5]  else 0
            vol         = int(parts[6])    if parts[6]  else 0
            change      = float(parts[31]) if len(parts) > 31 and parts[31] else 0
            change_pct  = float(parts[32]) if len(parts) > 32 and parts[32] else 0
            high        = float(parts[33]) if len(parts) > 33 and parts[33] else 0
            low         = float(parts[34]) if len(parts) > 34 and parts[34] else 0
            dt          = parts[30]        if len(parts) > 30 else ""
        except Exception:
            price = close_prev = open_p = high = low = change = change_pct = 0
            vol = 0; dt = ""
        result[code] = {
            "name": parts[1], "code": code,
            "price": price, "close_prev": close_prev, "open": open_p,
            "high": high, "low": low, "vol": vol,
            "change": change, "change_pct": change_pct, "datetime": dt,
        }
    return result


# ─────────────────────────────────────────────
#  定时自动采集调度器
# ─────────────────────────────────────────────
def _in_window(h, m, target_h, target_m, window=10):
    """判断当前时间是否在目标时间点的前后 window 分钟窗口内"""
    now_total    = h * 60 + m
    target_total = target_h * 60 + target_m
    return abs(now_total - target_total) <= window

def _scheduler():
    """后台线程：每10分钟检查一次，在目标时间点前后10分钟窗口内触发自动采集
    触发条件：当前时间在窗口内 + DB 无当日数据 + 本日未采集过
    """
    checked_morning   = None   # 已执行早报采集的日期
    checked_afternoon = None   # 已执行盘后采集的日期
    checked_weekly    = None   # 已执行周总结采集的周

    while True:
        try:
            now  = datetime.now()
            d    = now.date()
            h, m = now.hour, now.minute

            if is_weekday(d):
                date_str = d.strftime('%Y-%m-%d')
                week_str = get_week_monday(d)

                # 工作日 08:30 ± 10分钟 采集早报
                if _in_window(h, m, 8, 30) and checked_morning != date_str:
                    conn = get_conn()
                    row  = conn.execute(
                        "SELECT id FROM daily_reports WHERE date=? AND type='morning'", (date_str,)
                    ).fetchone()
                    conn.close()
                    if not row:
                        data = fetch_morning_data(date_str)
                        if data:
                            save_daily_auto(date_str, 'morning', data)
                            AUTO_STATUS['morning_last'] = now.strftime('%Y-%m-%d %H:%M')
                            AUTO_STATUS['morning_date'] = date_str
                            print(f"[自动采集] 早报 {date_str} ✅")
                    checked_morning = date_str

                # 工作日 15:30 ± 10分钟 采集盘后
                if _in_window(h, m, 15, 30) and checked_afternoon != date_str:
                    conn = get_conn()
                    row  = conn.execute(
                        "SELECT id FROM daily_reports WHERE date=? AND type='afternoon'", (date_str,)
                    ).fetchone()
                    conn.close()
                    if not row:
                        data = fetch_afternoon_data(date_str)
                        if data:
                            save_daily_auto(date_str, 'afternoon', data)
                            AUTO_STATUS['afternoon_last'] = now.strftime('%Y-%m-%d %H:%M')
                            AUTO_STATUS['afternoon_date'] = date_str
                            print(f"[自动采集] 盘后 {date_str} ✅")
                    checked_afternoon = date_str

                # 周五 16:00 ± 10分钟 采集周总结
                if d.weekday() == 4 and _in_window(h, m, 16, 0) and checked_weekly != week_str:
                    conn = get_conn()
                    row  = conn.execute(
                        "SELECT id FROM weekly_summary WHERE week=?", (week_str,)
                    ).fetchone()
                    conn.close()
                    if not row:
                        data = fetch_weekly_data(week_str)
                        if data:
                            save_weekly_auto(week_str, data)
                            AUTO_STATUS['weekly_last'] = now.strftime('%Y-%m-%d %H:%M')
                            AUTO_STATUS['weekly_week'] = week_str
                            print(f"[自动采集] 周总结 {week_str} ✅")
                    checked_weekly = week_str

        except Exception as ex:
            print(f"[调度器异常] {ex}")

        time.sleep(600)   # 每10分钟检查一次


# ─────────────────────────────────────────────
#  启动
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    # 启动定时采集线程
    t = threading.Thread(target=_scheduler, daemon=True)
    t.start()
    print("✅ 定时采集线程已启动（工作日 08:30 早报 / 15:30 盘后 / 周五 16:00 周总结）")

    # ThreadingHTTPServer：多线程处理请求，避免自动采集阻塞整个服务
    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(("0.0.0.0", 80), Handler)
    print("=" * 50)
    print("  股票日记服务已启动")
    print("  访问地址: http://127.0.0.1/stock/")
    print("  旧地址仍可用: http://127.0.0.1/")
    print("=" * 50)
    print("  数据库  : stock_diary.db")
    print("  API 文档 (支持 /stock/api/ 和 /api/ 双前缀):")
    print("    GET  /stock/api/daily?date=YYYY-MM-DD")
    print("    POST /stock/api/daily  {date,type,title,content,sentiment,time,structured_data}")
    print("    GET  /stock/api/weekly?week=YYYY-MM-DD")
    print("    POST /stock/api/weekly/summary  {week,...}")
    print("    GET  /stock/api/auto/morning?date=YYYY-MM-DD")
    print("    GET  /stock/api/auto/afternoon?date=YYYY-MM-DD")
    print("    GET  /stock/api/auto/weekly?week=YYYY-MM-DD")
    print("    GET  /stock/api/auto/status")
    print("    GET  /stock/api/search/stock?q=关键词")
    print("    GET  /stock/api/holdings")
    print("    GET  /stock/api/quote/index")
    print("    GET  /stock/api/quote/stock?codes=sh600519")
    print("=" * 50)
    server.serve_forever()
