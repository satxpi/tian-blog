"""
股票日记 - 本地行情代理服务器
端口: 3389
功能: 转发腾讯财经行情接口，解决浏览器跨域限制
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs, urlencode
import json, re, time, threading

CACHE = {}          # { cache_key: (timestamp, data) }
CACHE_TTL = 5       # 行情缓存5秒

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        # --- 路由 ---
        if parsed.path == "/quote":
            self.handle_quote(qs)
        elif parsed.path == "/index":
            self.handle_index()
        elif parsed.path == "/sector":
            self.handle_sector()
        elif parsed.path == "/news":
            self.handle_news()
        else:
            self.send_json({"error": "unknown path"}, 404)

    # ========== 个股/指数行情 ==========
    def handle_quote(self, qs):
        codes = qs.get("codes", [""])[0]
        if not codes:
            self.send_json({"error": "no codes"}, 400)
            return

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
            raw = urlopen(req, timeout=6).read().decode("gbk", errors="replace")
            result = parse_tencent(raw)
            CACHE[cache_key] = (time.time(), result)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ========== 大盘三大指数 ==========
    def handle_index(self):
        self.handle_quote({"codes": ["sh000001,sz399001,sz399006"]})

    # ========== 板块资金流向（东方财富） ==========
    def handle_sector(self):
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
            raw = urlopen(req, timeout=8).read().decode("utf-8", errors="replace")
            # 去掉可能的 JSONP 包装
            raw = re.sub(r'^\w+\(', '', raw).rstrip(');')
            data = json.loads(raw)
            items = data.get("data", {}).get("diff", [])
            sectors = []
            for it in items[:10]:
                inflow = it.get("f62", 0) or 0
                chg = it.get("f3", 0) or 0
                sectors.append({
                    "name": it.get("f14", ""),
                    "code": it.get("f12", ""),
                    "change": round(chg, 2),
                    "inflow": round(inflow / 1e8, 2),   # 亿元
                    "main_inflow": round((it.get("f66", 0) or 0) / 1e8, 2),
                })
            result = {"sectors": sectors}
            CACHE[cache_key] = (time.time(), result)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e), "sectors": []}, 200)

    # ========== 财经快讯（东方财富） ==========
    def handle_news(self):
        cache_key = "news"
        cached = CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 60:
            self.send_json(cached[1])
            return
        try:
            url = ("https://np-anotice-stock.eastmoney.com/api/security/ann"
                   "?sr=-1&page_size=10&page_index=1&ann_type=ALL&client_source=web")
            req = Request(url, headers={
                "Referer": "https://www.eastmoney.com/",
                "User-Agent": "Mozilla/5.0"
            })
            raw = urlopen(req, timeout=8).read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            items = data.get("data", {}).get("list", [])
            news = [{"title": it.get("title", ""), "time": it.get("notice_date", ""),
                     "stock": it.get("codes", [{}])[0].get("short_name", "") if it.get("codes") else ""}
                    for it in items[:8]]
            result = {"news": news}
            CACHE[cache_key] = (time.time(), result)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e), "news": []}, 200)

    # ========== 发送JSON ==========
    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)


# ========== 解析腾讯行情格式 ==========
def parse_tencent(raw):
    """
    格式: v_sh000001="1~上证指数~000001~现价~昨收~今开~..."
    字段索引（1-based）:
      3=现价 4=昨收 5=今开 6=成交量(手) 33=时间 34=涨跌额 35=涨跌幅
      33=最高 34=最低 ...
    完整字段表:
    idx 0=type 1=name 2=code 3=price 4=close_prev 5=open
        6=vol 31=bid1 32=ask1 33=datetime 34=change 35=change_pct
        36=high 37=low 38=price/vol/amount 44=pe 45=pb ...
    """
    result = {}
    for line in raw.strip().split("\n"):
        line = line.strip().rstrip(";")
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip('"')
        parts = val.split("~")
        if len(parts) < 36:
            continue
        code = parts[2]
        try:
            price = float(parts[3]) if parts[3] else 0
            close_prev = float(parts[4]) if parts[4] else 0
            open_p = float(parts[5]) if parts[5] else 0
            vol = int(parts[6]) if parts[6] else 0
            high = float(parts[33]) if len(parts) > 33 and parts[33] else 0
            low = float(parts[34]) if len(parts) > 34 and parts[34] else 0
            change = float(parts[31]) if len(parts) > 31 and parts[31] else 0
            change_pct = float(parts[32]) if len(parts) > 32 and parts[32] else 0
            dt = parts[30] if len(parts) > 30 else ""
        except Exception:
            price = close_prev = 0
            vol = 0; high = low = 0; change = change_pct = 0; dt = ""
            open_p = 0

        result[code] = {
            "name": parts[1],
            "code": code,
            "price": price,
            "close_prev": close_prev,
            "open": open_p,
            "high": high,
            "low": low,
            "vol": vol,
            "change": change,
            "change_pct": change_pct,
            "datetime": dt,
        }
    return result


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 3389), ProxyHandler)
    print("✅ 行情代理服务已启动: http://127.0.0.1:3389")
    print("   /index  → 三大指数")
    print("   /quote?codes=sh600519,sz300750  → 个股行情")
    print("   /sector → 板块资金流向")
    print("   /news   → 财经快讯")
    server.serve_forever()
