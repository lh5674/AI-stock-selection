# test_market.py — 保存在 backend/ 运行
import requests

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
}

tests = {
    "Yahoo v8 chart (trust_env=False)": {
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=5d",
        "trust_env": False,
    },
    "Yahoo v8 chart (trust_env=True)": {
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=5d",
        "trust_env": True,
    },
    "Yahoo v8 chart query2": {
        "url": "https://query2.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=5d",
        "trust_env": True,
    },
    "Yahoo v7 quote": {
        "url": "https://query1.finance.yahoo.com/v7/finance/quote?symbols=NVDA,AAPL",
        "trust_env": True,
    },
    "Yahoo v6 quote": {
        "url": "https://query2.finance.yahoo.com/v6/finance/quote?symbols=NVDA",
        "trust_env": True,
    },
}

for name, cfg in tests.items():
    s = requests.Session()
    s.trust_env = cfg["trust_env"]
    try:
        r = s.get(cfg["url"], headers=HEADERS, timeout=8)
        print(f"{'✅' if r.status_code==200 else '❌'} {name}")
        print(f"   status={r.status_code} len={len(r.text)} preview={r.text[:80]}")
    except Exception as e:
        print(f"❌ {name}: {e}")