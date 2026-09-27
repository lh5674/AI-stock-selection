import math
import random
import re
import time
from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import quote

import requests


class MarketDataError(RuntimeError):
    """Raised when an upstream market-data provider is unavailable."""


_session = requests.Session()
_session.trust_env = True

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0"
    ),
    "Accept": "application/json",
}

NAME_CN = {
    "NVDA": "英伟达",
    "MSFT": "微软",
    "GOOGL": "谷歌",
    "META": "Meta",
    "AMD": "超微半导体",
    "TSLA": "特斯拉",
    "AAPL": "苹果",
    "AMZN": "亚马逊",
}

_cache = {}
_cache_lock = Lock()


def _cache_get(key):
    with _cache_lock:
        value = _cache.get(key)
        if value and value["expire"] > time.time():
            return value["data"]
    return None


def _cache_set(key, data, ttl=60):
    with _cache_lock:
        _cache[key] = {"data": data, "expire": time.time() + ttl}


def _get_akshare():
    # Lazy import keeps app startup quick and makes provider failures isolated.
    import akshare as ak

    return ak


def _number(value, default=0.0):
    try:
        result = float(value)
        return default if math.isnan(result) or math.isinf(result) else result
    except (TypeError, ValueError):
        return default


def _integer(value, default=0):
    return int(_number(value, default))


def _validate_a_code(code: str) -> str:
    normalized = code.strip()
    if not re.fullmatch(r"\d{6}", normalized):
        raise ValueError("A股代码必须是 6 位数字。")
    return normalized


def _validate_us_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", normalized):
        raise ValueError("美股代码格式不正确。")
    return normalized


def _yf_chart(symbol: str, range_value: str) -> dict:
    safe_symbol = quote(_validate_us_symbol(symbol), safe="")
    last_error = None
    for host in ("query1", "query2"):
        try:
            response = _session.get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{safe_symbol}",
                params={"interval": "1d", "range": range_value},
                headers=HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            chart = response.json().get("chart", {})
            if chart.get("error"):
                raise MarketDataError("行情代码不存在或暂时不可用。")
            results = chart.get("result") or []
            if results:
                return results[0]
        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = exc
    raise MarketDataError("美股行情服务暂时不可用，请稍后重试。") from last_error


def _yf_quote_single(symbol: str) -> dict:
    normalized = _validate_us_symbol(symbol)
    chart = _yf_chart(normalized, "5d")
    meta = chart.get("meta", {})
    price = meta.get("regularMarketPrice") or meta.get("previousClose")
    previous = meta.get("previousClose") or meta.get("chartPreviousClose")
    if price is None:
        raise MarketDataError("美股行情缺少价格数据。")
    change = ((price - previous) / previous * 100) if previous else 0.0
    return {
        "symbol": normalized,
        "name": NAME_CN.get(normalized, normalized),
        "price": round(float(price), 2),
        "change_pct": round(change, 2),
    }


def _yf_kline(symbol: str) -> list:
    chart = _yf_chart(symbol, "1mo")
    timestamps = chart.get("timestamp", [])
    quote_data = (chart.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote_data.get("close", [])
    volumes = quote_data.get("volume", [])
    return [
        {
            "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
            "close": round(float(close), 2),
            "volume": _integer(volume),
        }
        for timestamp, close, volume in zip(timestamps, closes, volumes)
        if close is not None
    ]


def _batch_quotes(symbols: list) -> list:
    results = []
    order = symbols[:]
    random.shuffle(order)
    for symbol in order:
        try:
            results.append(_yf_quote_single(symbol))
        except (MarketDataError, ValueError):
            continue
        time.sleep(0.1)
    return results


def get_us_movers() -> list:
    cached = _cache_get("us_movers")
    if cached is not None:
        return cached
    symbols = ["NVDA", "MSFT", "GOOGL", "META", "AMD", "TSLA", "AAPL", "AMZN"]
    results = _batch_quotes(symbols)
    if not results:
        raise MarketDataError("美股行情服务暂时不可用，请稍后重试。")
    results.sort(key=lambda item: item["change_pct"], reverse=True)
    _cache_set("us_movers", results, ttl=60)
    return results


def get_hot_sectors_a() -> list:
    cached = _cache_get("sectors_a")
    if cached is not None:
        return cached
    akshare = _get_akshare()
    try:
        frame = akshare.stock_board_industry_name_em()
        records = frame.to_dict("records")
        data = [
            {
                "板块名称": str(row.get("板块名称", "")).strip(),
                "涨跌幅": round(_number(row.get("涨跌幅")), 2),
                "最新价": round(_number(row.get("最新价")), 2),
                "name": str(row.get("板块名称", "")).strip(),
                "change_pct": round(_number(row.get("涨跌幅")), 2),
                "price": round(_number(row.get("最新价")), 2),
                "kind": "industry",
            }
            for row in records
            if str(row.get("板块名称", "")).strip()
        ]
        data.sort(key=lambda item: item["涨跌幅"], reverse=True)
    except Exception:
        # Eastmoney can be unavailable on some regional proxies. Sina's full
        # A-share snapshot is slower but provides a genuine, independent
        # fallback. Rank it by turnover to represent market attention.
        try:
            frame = akshare.stock_zh_a_spot()
            records = frame.to_dict("records")
            active = sorted(
                records,
                key=lambda row: _number(row.get("成交额")),
                reverse=True,
            )[:30]
            data = [
                {
                    "板块名称": str(row.get("名称", "")).strip(),
                    "涨跌幅": round(_number(row.get("涨跌幅")), 2),
                    "最新价": round(_number(row.get("最新价")), 2),
                    "name": str(row.get("名称", "")).strip(),
                    "change_pct": round(_number(row.get("涨跌幅")), 2),
                    "price": round(_number(row.get("最新价")), 2),
                    "symbol": re.sub(r"^[a-zA-Z]+", "", str(row.get("代码", ""))),
                    "kind": "stock",
                }
                for row in active
                if row.get("代码") and row.get("名称")
            ]
        except Exception as exc:
            raise MarketDataError("A股市场热度数据暂时不可用，请稍后重试。") from exc
    result = data[:12]
    if not result:
        raise MarketDataError("A股行业板块数据暂时为空。")
    _cache_set("sectors_a", result, ttl=120)
    return result


def get_sector_stocks(sector_name: str) -> list:
    normalized = sector_name.strip()
    if not normalized or len(normalized) > 40:
        raise ValueError("板块名称格式不正确。")
    cache_key = f"sector:{normalized}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        frame = _get_akshare().stock_board_industry_cons_em(symbol=normalized)
        records = frame.to_dict("records")
        data = [
            {
                "code": str(row.get("代码", "")).zfill(6),
                "name": str(row.get("名称", "")).strip(),
                "price": round(_number(row.get("最新价")), 2),
                "change_pct": round(_number(row.get("涨跌幅")), 2),
                "volume": _integer(row.get("成交量")),
            }
            for row in records
            if row.get("代码") and row.get("名称")
        ]
    except Exception as exc:
        raise MarketDataError("板块成分股数据暂时不可用，请稍后重试。") from exc
    data.sort(key=lambda item: item["change_pct"], reverse=True)
    result = data[:30]
    _cache_set(cache_key, result, ttl=120)
    return result


def get_stock_detail_a(code: str) -> dict:
    normalized = _validate_a_code(code)
    cache_key = f"a_kline:{normalized}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return {"code": normalized, "history": cached}

    end = datetime.now()
    start = end - timedelta(days=90)
    akshare = _get_akshare()
    try:
        frame = akshare.stock_zh_a_hist(
            symbol=normalized,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
            timeout=10,
        )
        records = frame.to_dict("records")
    except Exception:
        prefix = "sh" if normalized.startswith("6") else "bj" if normalized.startswith(("4", "8", "9")) else "sz"
        try:
            frame = akshare.stock_zh_a_daily(
                symbol=f"{prefix}{normalized}",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="qfq",
            )
            records = frame.to_dict("records")
        except Exception as exc:
            raise MarketDataError("A股历史行情暂时不可用，请稍后重试。") from exc

    history = [
            {
                "date": str(row.get("日期", row.get("date", "")))[:10],
                "open": round(_number(row.get("开盘", row.get("open"))), 2),
                "high": round(_number(row.get("最高", row.get("high"))), 2),
                "low": round(_number(row.get("最低", row.get("low"))), 2),
                "close": round(_number(row.get("收盘", row.get("close"))), 2),
                "volume": _integer(row.get("成交量", row.get("volume"))),
            }
            for row in records
            if row.get("日期", row.get("date")) is not None
            and row.get("收盘", row.get("close")) is not None
        ][-30:]
    if not history:
        raise MarketDataError("未找到该 A 股代码的近期行情。")
    _cache_set(cache_key, history, ttl=300)
    return {"code": normalized, "history": history}


def get_stock_detail_us(symbol: str) -> dict:
    normalized = _validate_us_symbol(symbol)
    cache_key = f"us_kline:{normalized}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return {"symbol": normalized, "history": cached}
    history = _yf_kline(normalized)
    if not history:
        raise MarketDataError("未找到该美股代码的近期行情。")
    _cache_set(cache_key, history, ttl=300)
    return {"symbol": normalized, "history": history}
