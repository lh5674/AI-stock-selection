import requests
import time
import random
from datetime import datetime
from threading import Lock

# ── 关键：trust_env=True，走系统代理 ─────────────────────────
_session = requests.Session()
_session.trust_env = True   # 必须是 True！

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept": "application/json",
}

NAME_CN = {
    "NVDA":"英伟达","MSFT":"微软","GOOGL":"谷歌","META":"Meta",
    "AMD":"超微半导体","TSLA":"特斯拉","AAPL":"苹果","AMZN":"亚马逊",
    "BABA":"阿里巴巴","BIDU":"百度","JD":"京东","PDD":"拼多多",
    "NTES":"网易","BILI":"哔哩哔哩","NIO":"蔚来","XPEV":"小鹏",
    "LI":"理想汽车","TCOM":"携程",
}

# ── TTL 缓存 60秒 ─────────────────────────────────────────────
_cache = {}
_cache_lock = Lock()

def _cache_get(key):
    with _cache_lock:
        v = _cache.get(key)
        if v and v["expire"] > time.time():
            print(f"[cache] hit: {key}")
            return v["data"]
    return None

def _cache_set(key, data, ttl=60):
    with _cache_lock:
        _cache[key] = {"data": data, "expire": time.time() + ttl}


# ══════════════════════════════════════════════════════════════
# 核心: Yahoo v8/finance/chart — 已确认新加坡可用
# ══════════════════════════════════════════════════════════════
def _yf_quote_single(symbol: str) -> dict | None:
    """用 chart meta 字段拿实时价格"""
    for base in ["query1", "query2"]:   # query1 失败自动试 query2
        try:
            url = f"https://{base}.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
            r = _session.get(url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            meta  = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice") or meta.get("previousClose")
            prev  = meta.get("previousClose") or meta.get("chartPreviousClose")
            if not price:
                continue
            change = round((price - prev) / prev * 100, 2) if prev else 0.0
            return {
                "symbol":     symbol.upper(),
                "name":       NAME_CN.get(symbol.upper(), symbol),
                "price":      round(float(price), 2),
                "change_pct": change,
            }
        except Exception as e:
            print(f"[yf_quote] {symbol} {base} failed: {type(e).__name__}")
    return None


def _yf_kline(symbol: str) -> list:
    """用 chart 接口拿近30日K线"""
    for base in ["query1", "query2"]:
        try:
            url = f"https://{base}.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
            r = _session.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            chart   = r.json().get("chart", {}).get("result", [{}])[0]
            ts      = chart.get("timestamp", [])
            closes  = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            volumes = chart.get("indicators", {}).get("quote", [{}])[0].get("volume", [])
            history = [
                {
                    "date":   datetime.fromtimestamp(t).strftime("%Y-%m-%d"),
                    "close":  round(float(c), 2) if c else 0,
                    "volume": int(v) if v else 0,
                }
                for t, c, v in zip(ts, closes, volumes) if c
            ]
            if history:
                return history
        except Exception as e:
            print(f"[yf_kline] {symbol} {base} failed: {e}")
    return []


def _batch_quotes(symbols: list) -> list:
    """逐个拉取，加小延迟避免限流"""
    results = []
    order = symbols[:]
    random.shuffle(order)
    for sym in order:
        q = _yf_quote_single(sym)
        if q:
            results.append(q)
        time.sleep(0.15)
    return results


# ══════════════════════════════════════════════════════════════
# 对外接口
# ══════════════════════════════════════════════════════════════
def get_us_movers() -> list:
    cached = _cache_get("us_movers")
    if cached:
        return cached
    symbols = ["NVDA","MSFT","GOOGL","META","AMD","TSLA","AAPL","AMZN"]
    results = _batch_quotes(symbols)
    results.sort(key=lambda x: x["change_pct"], reverse=True)
    if results:
        _cache_set("us_movers", results, ttl=60)
    print(f"[us_movers] OK — {len(results)}/{len(symbols)}")
    return results


def get_hot_sectors_a() -> list:
    cached = _cache_get("sectors_a")
    if cached:
        return cached
    symbols = ["BABA","BIDU","JD","PDD","NTES","BILI","NIO","XPEV","LI","TCOM"]
    results = _batch_quotes(symbols)
    data = sorted(
        [
            {
                "板块名称": q["name"],
                "涨跌幅":   q["change_pct"],
                "最新价":   q["price"],
                "symbol":   q["symbol"],
            }
            for q in results
        ],
        key=lambda x: x["涨跌幅"], reverse=True
    )
    if data:
        _cache_set("sectors_a", data, ttl=60)
    print(f"[sectors_a] OK — {len(data)}/{len(symbols)}")
    return data


def get_stock_detail_us(symbol: str) -> dict:
    cache_key = f"kline:{symbol}"
    cached = _cache_get(cache_key)
    if cached:
        return {"symbol": symbol, "history": cached}
    history = _yf_kline(symbol)
    if history:
        _cache_set(cache_key, history, ttl=300)
    print(f"[kline] {symbol} OK — {len(history)} days")
    return {"symbol": symbol, "history": history}


def get_sector_stocks(sector_name: str):
    return []

def get_stock_detail_a(code: str):
    return {"history": []}


# ── 自测 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n===== 美股实时 =====")
    for s in get_us_movers():
        print(f"  {s['symbol']:6} {s['name']:10} ${s['price']:>9.2f}  {s['change_pct']:+.2f}%")

    print("\n===== 中概股实时 =====")
    for s in get_hot_sectors_a():
        print(f"  {s['symbol']:6} {s['板块名称']:10} ${s['最新价']:>9.2f}  {s['涨跌幅']:+.2f}%")

    print("\n===== NVDA K线 =====")
    for d in get_stock_detail_us("NVDA")["history"][-3:]:
        print(f"  {d['date']}  ${d['close']}")